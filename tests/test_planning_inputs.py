"""Provas do contrato persistido entre planejamento e estudo de flexibilizações."""

import json
from pathlib import Path
import shutil

import numpy as np
import pytest

from src.optimization.planning_inputs import (
    inputs_digest,
    load_planning_inputs,
    load_relaxation_limits,
    save_planning_inputs,
)

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "models/otimizacao/entradas_planejamento.json"


def test_received_limits_apply_to_internal_changes_only():
    limits = load_relaxation_limits(ROOT / "models/otimizacao/limites_flexibilizacoes.json")
    assert limits["daily_variation_ceiling"] == 15
    assert limits["initial_transition_ceiling"] is None


@pytest.mark.parametrize("value", [0, -1, float("inf"), None])
def test_invalid_relaxation_limit_is_rejected(tmp_path, value):
    path = tmp_path / "limits.json"
    path.write_text(
        json.dumps(
            {
                "artifact_version": 1,
                "daily_variation_ceiling": value,
                "initial_transition_ceiling": None,
            }
        )
    )
    with pytest.raises(ValueError, match="positivo e finito"):
        load_relaxation_limits(path)


def test_saved_inputs_reproduce_the_same_problem(tmp_path):
    problem, bundle = load_planning_inputs(INPUT, root=ROOT)
    saved = save_planning_inputs(
        problem,
        tmp_path / "inputs.json",
        root=ROOT,
        model_path=ROOT / bundle["model_file"],
        restrictions_path=ROOT / bundle["restrictions_file"],
    )
    assert saved["inputs_sha256"] == bundle["inputs_sha256"]
    loaded, _ = load_planning_inputs(tmp_path / "inputs.json", root=ROOT)
    assert loaded.initial_price == problem.initial_price
    assert loaded.targets == problem.targets
    assert loaded.dates == problem.dates
    np.testing.assert_array_equal(loaded.costs, problem.costs)


def test_modified_economic_inputs_are_detected(tmp_path):
    bundle = json.loads(INPUT.read_text())
    bundle["initial_price"] = 1200
    modified = tmp_path / "inputs.json"
    modified.write_text(json.dumps(bundle))
    with pytest.raises(ValueError, match="hash registrado"):
        load_planning_inputs(modified, root=ROOT)


@pytest.mark.parametrize("source", ["model", "training", "restrictions"])
def test_source_updates_require_regenerating_inputs(tmp_path, source):
    bundle = json.loads(INPUT.read_text())
    for name in ["model", "training", "restrictions"]:
        target = tmp_path / bundle[f"{name}_file"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / bundle[f"{name}_file"], target)
    changed = tmp_path / bundle[f"{source}_file"]
    changed.write_bytes(changed.read_bytes() + b"\n")
    with pytest.raises(ValueError, match=f"fonte {source} mudou"):
        load_planning_inputs(INPUT, root=tmp_path)


def test_horizon_must_remain_after_the_decision_cutoff(tmp_path):
    bundle = json.loads(INPUT.read_text())
    bundle["horizon"][0]["date"] = bundle["decision_cutoff"]
    bundle["inputs_sha256"] = inputs_digest(bundle)
    modified = tmp_path / "inputs.json"
    modified.write_text(json.dumps(bundle))
    with pytest.raises(ValueError, match="posterior ao corte"):
        load_planning_inputs(modified, root=ROOT)
