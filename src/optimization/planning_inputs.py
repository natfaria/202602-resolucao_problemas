"""Entradas persistidas de planejamento, com integridade das fontes e da curva."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from src.modeling.demand_curve import (
    file_sha256,
    load_artifact,
    validate_artifact,
    validate_training_data,
)
from src.optimization.price_schedule import PriceProblem


def inputs_digest(payload: dict) -> str:
    data = {key: value for key, value in payload.items() if key != "inputs_sha256"}
    return hashlib.sha256(
        json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def save_planning_inputs(
    problem: PriceProblem,
    path: str | Path,
    *,
    root: Path,
    model_path: Path,
    restrictions_path: Path,
) -> dict:
    """Salva entradas econômicas, regras e calendário antes da busca de preços."""
    validate_artifact(problem.artifact)
    training_path = validate_training_data(problem.artifact, root)
    payload = {
        "artifact_version": 1,
        "model_file": str(model_path.relative_to(root)),
        "model_file_sha256": file_sha256(model_path),
        "model_core_sha256": problem.artifact["model_core_sha256"],
        "training_file": str(training_path.relative_to(root)),
        "training_file_sha256": file_sha256(training_path),
        "restrictions_file": str(restrictions_path.relative_to(root)),
        "restrictions_file_sha256": file_sha256(restrictions_path),
        "decision_cutoff": problem.artifact["training"]["end"],
        "cost_method": "custo_unitario_ultimo_dia_treino",
        "initial_price": float(problem.initial_price),
        "unit_cost": problem.costs.tolist(),
        "tax_rate": float(problem.tax_rate),
        "targets": dict(problem.targets),
        "tolerance": float(problem.tolerance),
        "tolerance_lower": float(problem.tol_lower),
        "tolerance_upper": float(problem.tol_upper),
        "daily_variation": float(problem.daily_variation),
        "initial_variation": float(problem.init_var),
        "day_rule": problem.day_rule,
        "horizon": [
            {"date": str(date.date()), "weekday": day, "week": week}
            for date, day, week in zip(problem.dates, problem.weekdays, problem.weeks, strict=True)
        ],
    }
    payload["inputs_sha256"] = inputs_digest(payload)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return payload


def load_planning_inputs(path: str | Path, *, root: Path) -> tuple[PriceProblem, dict]:
    """Carrega somente artefatos persistidos e recusa fontes que mudaram."""
    payload = load_artifact(path)
    if payload["artifact_version"] != 1 or payload["inputs_sha256"] != inputs_digest(payload):
        raise ValueError("O artefato de entradas não corresponde ao hash registrado.")
    for name in ["model", "training", "restrictions"]:
        source = root / payload[f"{name}_file"]
        if file_sha256(source) != payload[f"{name}_file_sha256"]:
            raise ValueError(f"A fonte {name} mudou; gere novamente as entradas do planejamento.")
    artifact = load_artifact(root / payload["model_file"])
    validate_artifact(artifact)
    validate_training_data(artifact, root)
    if artifact["model_core_sha256"] != payload["model_core_sha256"]:
        raise ValueError("A curva não corresponde ao núcleo registrado nas entradas.")
    horizon = payload["horizon"]
    problem = PriceProblem(
        artifact=artifact,
        dates=tuple(pd.Timestamp(day["date"]) for day in horizon),
        weekdays=tuple(day["weekday"] for day in horizon),
        weeks=tuple(day["week"] for day in horizon),
        targets=payload["targets"],
        tolerance=payload["tolerance"],
        initial_price=payload["initial_price"],
        daily_variation=payload["daily_variation"],
        unit_cost=payload["unit_cost"],
        tax_rate=payload["tax_rate"],
        tolerance_lower=payload["tolerance_lower"],
        tolerance_upper=payload["tolerance_upper"],
        initial_variation=payload["initial_variation"],
        day_rule=payload["day_rule"],
    )
    if any(date <= pd.Timestamp(payload["decision_cutoff"]) for date in problem.dates):
        raise ValueError("O horizonte deve ser posterior ao corte das entradas.")
    if any(day not in artifact["calendar"]["mapping"] for day in problem.weekdays):
        raise ValueError("O horizonte contém dias fora do domínio da curva.")
    return problem, payload
