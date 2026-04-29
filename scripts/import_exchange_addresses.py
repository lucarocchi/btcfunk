"""
Fetches labeled Bitcoin exchange addresses from Dune Analytics spellbook
and stores them in our SQLite cache db.

Source: duneanalytics/spellbook (MIT license)
Run: python scripts/import_exchange_addresses.py
"""

import re
import sqlite3
import subprocess
import sys

DB_PATH = "mvrv_cache.sqlite"
SPELLBOOK_PATH = (
    "dbt_subprojects/hourly_spellbook/models/_sector/cex/addresses/chains/bitcoin"
    "/cex_bitcoin_addresses.sql"
)
REPO = "duneanalytics/spellbook"

# Pattern: ('bitcoin', '<address>', '<exchange>', '<label>', ...)
ROW_RE = re.compile(
    r"\(\s*'bitcoin'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'"
)


def fetch_sql():
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/contents/{SPELLBOOK_PATH}", "--jq", ".content"],
        capture_output=True, text=True, check=True,
    )
    import base64
    return base64.b64decode(result.stdout.strip()).decode()


def parse_addresses(sql):
    rows = []
    for m in ROW_RE.finditer(sql):
        address, exchange, label = m.group(1), m.group(2), m.group(3)
        rows.append((address, exchange, label))
    return rows


def init_db(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS known_addresses (
            address  TEXT PRIMARY KEY,
            exchange TEXT NOT NULL,
            label    TEXT,
            source   TEXT DEFAULT 'dune-spellbook'
        )
    """)
    con.commit()


def import_addresses(rows):
    con = sqlite3.connect(DB_PATH)
    init_db(con)
    con.executemany(
        "INSERT OR REPLACE INTO known_addresses (address, exchange, label, source) VALUES (?,?,?,?)",
        [(addr, exc, lbl, "dune-spellbook") for addr, exc, lbl in rows],
    )
    con.commit()
    return con.execute("SELECT COUNT(*) FROM known_addresses").fetchone()[0]


def main():
    print("Fetching Dune spellbook…")
    sql = fetch_sql()

    rows = parse_addresses(sql)
    print(f"Parsed {len(rows)} addresses")

    exchanges = {}
    for _, exc, _ in rows:
        exchanges[exc] = exchanges.get(exc, 0) + 1
    for exc, n in sorted(exchanges.items(), key=lambda x: -x[1]):
        print(f"  {exc:<20} {n}")

    total = import_addresses(rows)
    print(f"\nSQLite: {total} addresses in known_addresses")


if __name__ == "__main__":
    main()
