import os
import requests
from datetime import datetime, timezone

RPC_URL  = os.getenv("BITCOIN_RPC_URL", "http://bitcoinrpc:dc7cf5c65c8c964c7ee9d28e1c5059edada3a9f45702024e73e69a292bbca9e1@127.0.0.1:8332")
RPC_HDRS = {"Content-Type": "application/json"}


def _rpc(method, params=None):
    payload = {"jsonrpc": "1.0", "id": method, "method": method, "params": params or []}
    r = requests.post(RPC_URL, json=payload, headers=RPC_HDRS, timeout=10)
    r.raise_for_status()
    result = r.json()
    if result.get("error"):
        raise RuntimeError(result["error"])
    return result["result"]


def get_mempool():
    try:
        info  = _rpc("getmempoolinfo")
        chain = _rpc("getblockchaininfo")

        fee1  = _rpc("estimatesmartfee", [1])
        fee3  = _rpc("estimatesmartfee", [3])
        fee6  = _rpc("estimatesmartfee", [6])

        def sat(btc_per_kb):
            if btc_per_kb is None: return None
            return round(btc_per_kb * 1e8 / 1000, 1)

        size_mb   = round(info["bytes"] / 1e6, 2)
        tx_count  = info["size"]
        total_fees = round(info.get("total_fee", 0), 4)

        difficulty = chain["difficulty"]
        hashrate_eh = round(difficulty * 2**32 / 600 / 1e18, 2)

        return {
            "tx_count":    tx_count,
            "size_mb":     size_mb,
            "total_fees":  total_fees,
            "fee_next":    sat(fee1.get("feerate")),
            "fee_30min":   sat(fee3.get("feerate")),
            "fee_1h":      sat(fee6.get("feerate")),
            "hashrate_eh": hashrate_eh,
            "difficulty":  round(difficulty / 1e12, 2),
            "block_height": chain["blocks"],
            "updated_at":  datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}
