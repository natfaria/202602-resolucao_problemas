import pandas as pd
import pytest

from src.modeling.benchmarks import weekday_mean_forecast


def test_weekday_benchmark_uses_only_history_and_preserves_horizon_order():
    history = pd.DataFrame(
        {
            "data": ["2025-09-01", "2025-09-08", "2025-09-05"],
            "dia_semana": ["Segunda", "Segunda", "Sexta"],
            "volume_kg": [10.0, 30.0, 5.0],
        }
    )
    horizon = pd.DataFrame(
        {
            "data": ["2025-09-19", "2025-09-15"],
            "dia_semana": ["Sexta", "Segunda"],
            "volume_kg": [9999.0, 9999.0],
        }
    )
    assert weekday_mean_forecast(history, horizon) == pytest.approx([5.0, 20.0])
    with pytest.raises(ValueError, match="antes"):
        weekday_mean_forecast(pd.concat([history, horizon]), horizon)
