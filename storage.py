import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "seen_postings.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen (
            source TEXT NOT NULL,
            posting_id TEXT NOT NULL,
            PRIMARY KEY (source, posting_id)
        )
        """
    )
    return conn


def filter_new(source: str, posting_ids: list[str]) -> list[str]:
    if not posting_ids:
        return []

    conn = _connect()
    try:
        placeholders = ",".join("?" for _ in posting_ids)
        rows = conn.execute(
            f"SELECT posting_id FROM seen WHERE source = ? AND posting_id IN ({placeholders})",
            [source, *posting_ids],
        ).fetchall()
        already_seen = {r[0] for r in rows}
        new_ids = [pid for pid in posting_ids if pid not in already_seen]

        conn.executemany(
            "INSERT OR IGNORE INTO seen (source, posting_id) VALUES (?, ?)",
            [(source, pid) for pid in new_ids],
        )
        conn.commit()
        return new_ids
    finally:
        conn.close()