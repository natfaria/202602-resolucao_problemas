"""Inferência da curva de demanda congelada pelo Notebook 2."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

Artifact = Mapping[str, Any]


def load_artifact(path: str | Path) -> dict[str, Any]:
    """Carrega um artefato JSON sem desserializar código executável."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_artifact(artifact: Artifact, path: str | Path) -> None:
    """Salva o artefato em JSON legível e determinístico."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(dict(artifact), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def file_sha256(path: str | Path) -> str:
    """Calcula o SHA-256 de um arquivo."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_core(artifact: Artifact) -> dict[str, Any]:
    """Seleciona os campos que determinam as previsões da curva."""
    version = int(artifact["artifact_version"])
    common = {
        "model_id": artifact["model_id"],
        "family": artifact["family"],
        "calendar": artifact["calendar"],
        "feature_order": artifact["feature_order"],
        "coefficients": artifact["coefficients"],
        "smearing_factor": artifact["smearing_factor"],
        "price_support": artifact["price_support"],
    }
    if version == 1:
        # O Notebook 2.1 congelou a versão 1 antes da criação deste leitor. Seu
        # contrato inclui a fórmula, mas não a própria versão, no núcleo.
        remaining = {
            key: value for key, value in common.items() if key not in {"model_id", "family"}
        }
        return {
            "model_id": common["model_id"],
            "family": common["family"],
            "formula": artifact["formula"],
            **remaining,
        }
    if version == 2:
        return {"artifact_version": version, **common}
    raise ValueError(f"Versão de artefato não suportada: {version!r}")


def model_core_sha256(artifact: Artifact) -> str:
    """Calcula um hash estável dos campos que controlam a previsão."""
    serialized = json.dumps(
        model_core(artifact),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def validate_artifact(artifact: Artifact) -> None:
    """Valida a estrutura mínima e a integridade do núcleo preditivo."""
    required = {
        "artifact_version",
        "model_id",
        "family",
        "calendar",
        "feature_order",
        "coefficients",
        "smearing_factor",
        "price_support",
    }
    missing = required - set(artifact)
    if missing:
        raise ValueError(f"Artefato sem campos obrigatórios: {sorted(missing)}")
    version = int(artifact["artifact_version"])
    if version not in {1, 2}:
        raise ValueError(f"Versão de artefato não suportada: {version!r}")
    if version == 1 and "formula" not in artifact:
        raise ValueError("Artefato v1 sem o campo obrigatório 'formula'.")
    if artifact["family"] not in {"power", "exponential", "linear"}:
        raise ValueError(f"Família não suportada: {artifact['family']!r}")
    if set(artifact["feature_order"]) != set(artifact["coefficients"]):
        raise ValueError("Coeficientes e ordem de variáveis são incompatíveis.")
    expected_hash = artifact.get("model_core_sha256")
    if expected_hash and expected_hash != model_core_sha256(artifact):
        raise ValueError("O núcleo preditivo do artefato não corresponde ao hash registrado.")


def validate_uncertainty_artifact(artifact: Artifact, uncertainty: Artifact) -> None:
    """Valida que a incerteza pertence exatamente ao núcleo da curva informada."""
    validate_artifact(artifact)
    required = {"artifact_version", "model_core_sha256", "scenario_multipliers"}
    missing = required - set(uncertainty)
    if missing:
        raise ValueError(f"Artefato de incerteza sem campos obrigatórios: {sorted(missing)}")
    frozen_hash = str(artifact.get("model_core_sha256", model_core_sha256(artifact)))
    if uncertainty["model_core_sha256"] != frozen_hash:
        raise ValueError("A incerteza não pertence ao núcleo preditivo da curva informada.")
    multipliers = uncertainty["scenario_multipliers"]
    if float(multipliers.get("central", np.nan)) != 1.0:
        raise ValueError("O multiplicador do cenário central precisa ser igual a 1.")
    values = np.asarray(list(multipliers.values()), dtype=float)
    if not values.size or not np.all(np.isfinite(values)) or np.any(values <= 0):
        raise ValueError("Multiplicadores de cenário precisam ser finitos e positivos.")


def load_artifact_bundle(
    artifact_path: str | Path,
    uncertainty_path: str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Carrega e valida conjuntamente curva e incerteza congeladas."""
    artifact = load_artifact(artifact_path)
    uncertainty = load_artifact(uncertainty_path)
    validate_uncertainty_artifact(artifact, uncertainty)
    return artifact, uncertainty


def validate_training_data(artifact: Artifact, project_root: str | Path) -> Path:
    """Confere a base de treino registrada no artefato e devolve seu caminho."""
    training = artifact.get("training")
    if not isinstance(training, Mapping):
        raise TypeError("Artefato sem metadados estruturados da base de treino.")
    required = {"data_file", "data_sha256"}
    missing = required - set(training)
    if missing:
        raise ValueError(f"Metadados de treino sem campos: {sorted(missing)}")
    path = Path(project_root) / str(training["data_file"])
    if not path.is_file():
        raise FileNotFoundError(f"Base de treino registrada não encontrada: {path}")
    if file_sha256(path) != training["data_sha256"]:
        raise ValueError("A base de treino não corresponde ao SHA-256 registrado no artefato.")
    return path


def context_for_weekday(artifact: Artifact, weekday: str) -> str:
    """Transforma o dia da semana no contexto congelado no artefato."""
    mapping = artifact["calendar"]["mapping"]
    if weekday not in mapping:
        raise ValueError(f"Dia da semana não reconhecido: {weekday!r}")
    return str(mapping[weekday])


def _scenario_multiplier(scenario: str, uncertainty: Artifact | None) -> float:
    if scenario == "central":
        return 1.0
    if uncertainty is None:
        raise ValueError("Cenários não centrais exigem o artefato de incerteza.")
    multipliers = uncertainty["scenario_multipliers"]
    if scenario not in multipliers:
        raise ValueError(f"Cenário não reconhecido: {scenario!r}")
    return float(multipliers[scenario])


def predict_volume_from_artifact(
    artifact: Artifact | str | Path,
    price: float,
    weekday: str,
    *,
    scenario: str = "central",
    uncertainty: Artifact | str | Path | None = None,
    allow_extrapolation: bool = False,
) -> float:
    """Prevê volume em kg e bloqueia extrapolações por padrão."""
    artifact_data = load_artifact(artifact) if isinstance(artifact, (str, Path)) else dict(artifact)
    validate_artifact(artifact_data)
    uncertainty_data = (
        load_artifact(uncertainty) if isinstance(uncertainty, (str, Path)) else uncertainty
    )
    if uncertainty_data is not None:
        validate_uncertainty_artifact(artifact_data, uncertainty_data)
    if price <= 0:
        raise ValueError("Preço precisa ser estritamente positivo.")

    context = context_for_weekday(artifact_data, weekday)
    if context not in artifact_data["price_support"]:
        raise ValueError(f"Contexto ausente no suporte do artefato: {context!r}")
    support = artifact_data["price_support"][context]
    lower = float(support["min"])
    upper = float(support["max"])
    if not allow_extrapolation and not lower <= price <= upper:
        raise ValueError(
            f"Preço {price:.2f} fora do suporte de {context}: [{lower:.2f}, {upper:.2f}]."
        )

    family = artifact_data["family"]
    price_feature = np.log(price) if family == "power" else price / 100.0
    features = {name: 0.0 for name in artifact_data["feature_order"]}
    features["const"] = 1.0
    features["ln_preco" if family == "power" else "preco_100"] = float(price_feature)
    baseline = artifact_data["calendar"]["baseline"]
    if context != baseline:
        features[f"contexto_{context}"] = 1.0

    linear_prediction = sum(
        float(artifact_data["coefficients"][name]) * features[name]
        for name in artifact_data["feature_order"]
    )
    if family in {"power", "exponential"}:
        prediction = np.exp(linear_prediction) * float(artifact_data["smearing_factor"])
    else:
        prediction = linear_prediction
    prediction *= _scenario_multiplier(scenario, uncertainty_data)
    if prediction <= 0:
        raise ValueError("A curva produziu volume não positivo no ponto solicitado.")
    return float(prediction)
