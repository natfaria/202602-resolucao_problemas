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
    return {
        "artifact_version": artifact["artifact_version"],
        "model_id": artifact["model_id"],
        "family": artifact["family"],
        "calendar": artifact["calendar"],
        "feature_order": artifact["feature_order"],
        "coefficients": artifact["coefficients"],
        "smearing_factor": artifact["smearing_factor"],
        "price_support": artifact["price_support"],
    }


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
    if artifact["family"] not in {"power", "exponential", "linear"}:
        raise ValueError(f"Família não suportada: {artifact['family']!r}")
    if set(artifact["feature_order"]) != set(artifact["coefficients"]):
        raise ValueError("Coeficientes e ordem de variáveis são incompatíveis.")
    expected_hash = artifact.get("model_core_sha256")
    if expected_hash and expected_hash != model_core_sha256(artifact):
        raise ValueError("O núcleo preditivo do artefato não corresponde ao hash registrado.")


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
