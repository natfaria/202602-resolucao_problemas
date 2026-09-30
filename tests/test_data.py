from pathlib import Path

from src.modeling.demand_curve import context_for_weekday, load_artifact


def test_frozen_artifact_uses_the_selected_calendar_partition():
    artifact_path = Path(__file__).parents[1] / "models/demand_curve_champion.json"
    artifact = load_artifact(artifact_path)

    assert context_for_weekday(artifact, "Segunda") == "Segunda_a_Quinta"
    assert context_for_weekday(artifact, "Terça") == "Segunda_a_Quinta"
    assert context_for_weekday(artifact, "Quarta") == "Segunda_a_Quinta"
    assert context_for_weekday(artifact, "Quinta") == "Segunda_a_Quinta"
    assert context_for_weekday(artifact, "Sexta") == "Sexta"
    assert context_for_weekday(artifact, "Sábado") == "Fim_de_semana"
    assert context_for_weekday(artifact, "Domingo") == "Fim_de_semana"
