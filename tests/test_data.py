from pathlib import Path

import pytest

from src.modeling.demand_curve import context_for_weekday, load_artifact

ARTIFACT = Path(__file__).parents[1] / "models/preditivo_diario/curva_demanda.json"


def test_published_artifact_uses_the_selected_calendar_partition():
    artifact = load_artifact(ARTIFACT)

    for weekday in ["Segunda", "Terça", "Quarta", "Quinta"]:
        assert context_for_weekday(artifact, weekday) == "Segunda_a_Quinta"
    assert context_for_weekday(artifact, "Sexta") == "Sexta"


def test_weekend_is_outside_the_published_domain():
    with pytest.raises(ValueError, match="não reconhecido"):
        context_for_weekday(load_artifact(ARTIFACT), "Sábado")
