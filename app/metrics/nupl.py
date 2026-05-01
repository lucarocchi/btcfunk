import sqlite3
from datetime import datetime, timezone

DB_PATH = "btcfunk.sqlite"


def get_nupl():
    from app.metrics.mvrv import get_mvrv
    d = get_mvrv()

    mvrv = d["mvrv"]
    nupl = round(1 - 1 / mvrv, 4) if mvrv else None

    # realized_price = current_price / mvrv  (derived from MVRV definition)
    realized_price = round(d["current_price"] / mvrv, 2) if mvrv else None

    # Historical NUPL from historical MVRV series
    nupl_values = [
        round(1 - 1 / v, 4) if v and v > 0 else None
        for v in d["values"]
    ]

    return {
        "nupl":           nupl,
        "realized_price": realized_price,
        "current_price":  d["current_price"],
        "labels":         d["labels"],
        "values":         nupl_values,
        "updated_at":     d["updated_at"],
    }
