from src.modeling.demand_curve import assign_cluster


def test_assign_cluster_uses_the_selected_calendar_partition():
    assert assign_cluster("Segunda") == "Segunda"
    assert assign_cluster("Terça") == "TerQuaQui"
    assert assign_cluster("Quarta") == "TerQuaQui"
    assert assign_cluster("Quinta") == "TerQuaQui"
    assert assign_cluster("Sexta") == "Sexta"
    assert assign_cluster("Sábado") == "FimDeSemana"
    assert assign_cluster("Domingo") == "FimDeSemana"
