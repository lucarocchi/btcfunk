import requests
from datetime import datetime, timezone


def get_fear_greed():
    r = requests.get(
        "https://api.alternative.me/fng/",
        params={"limit": 365},
        headers={"User-Agent": "btcfunk/1.0"},
        timeout=10,
    )
    r.raise_for_status()
    data = r.json()["data"]

    labels, values = [], []
    for entry in reversed(data):
        dt = datetime.fromtimestamp(int(entry["timestamp"]), tz=timezone.utc)
        labels.append(dt.strftime("%Y-%m-%d"))
        values.append(int(entry["value"]))

    current = values[-1] if values else None
    classification = data[0]["value_classification"] if data else None

    return {
        "current":        current,
        "classification": classification,
        "labels":         labels,
        "values":         values,
        "updated_at":     datetime.now(timezone.utc).isoformat(),
    }
