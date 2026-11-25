"""Inferência da curva de demanda publicada pelo notebook 2.0."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

Artifact = Mapping[str, Any]
ARTIFACT_VERSION = 2


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
    if version != ARTIFACT_VERSION:
        raise ValueError(f"Versão de artefato não suportada: {version!r}")
    return {
        "artifact_version": version,
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
    version = int(artifact["artifact_version"])
    if version != ARTIFACT_VERSION:
        raise ValueError(f"Versão de artefato não suportada: {version!r}")
    if artifact["family"] not in {"power", "exponential", "linear"}:
        raise ValueError(f"Família não suportada: {artifact['family']!r}")
    if set(artifact["feature_order"]) != set(artifact["coefficients"]):
        raise ValueError("Coeficientes e ordem de variáveis são incompatíveis.")
    expected_hash = artifact.get("model_core_sha256")
    if expected_hash and expected_hash != model_core_sha256(artifact):
        raise ValueError("O núcleo preditivo do artefato não corresponde ao hash registrado.")


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


def predict_volume_from_artifact(
    artifact: Artifact | str | Path,
    price: float,
    weekday: str,
    *,
    allow_extrapolation: bool = False,
) -> float:
    """Prevê volume em kg e bloqueia extrapolações por padrão."""
    artifact_data = (
        load_artifact(artifact) if isinstance(artifact, (str, Path)) else dict(artifact)
    )
    validate_artifact(artifact_data)
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
    if prediction <= 0:
        raise ValueError("A curva produziu volume não positivo no ponto solicitado.")
    return float(prediction)
