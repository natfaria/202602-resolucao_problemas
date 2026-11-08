"""Referência de previsão por calendário, sem preço e sem acesso ao futuro."""

import numpy as np
import pandas as pd


def weekday_mean_forecast(history: pd.DataFrame, horizon: pd.DataFrame) -> np.ndarray:
    """Prevê cada dia pela média histórica do mesmo dia da semana.

    O horizonte fornece somente datas e calendário. Seus volumes não são usados.
    A separação temporal é exigida mesmo quando o chamador já construiu os folds.
    """
    if history.empty or horizon.empty:
        raise ValueError("Histórico e horizonte precisam conter observações.")
    if pd.to_datetime(history["data"]).max() >= pd.to_datetime(horizon["data"]).min():
        raise ValueError("O histórico deve terminar antes do horizonte.")
    means = history.groupby("dia_semana", observed=True)["volume_kg"].mean()
    prediction = horizon["dia_semana"].map(means).to_numpy(dtype=float)
    if not np.isfinite(prediction).all() or (prediction <= 0).any():
        raise ValueError("Cada dia do horizonte precisa de média histórica positiva.")
    return prediction
