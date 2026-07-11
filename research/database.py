from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd


class ResearchDatabase:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bars (
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                time INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                tick_volume INTEGER NOT NULL,
                spread INTEGER NOT NULL,
                real_volume INTEGER NOT NULL,
                PRIMARY KEY(symbol, timeframe, time)
            )
            """
        )
        self.conn.commit()

    def upsert_bars(self, symbol: str, timeframe: str, frame: pd.DataFrame) -> int:
        if frame.empty:
            return 0

        rows = [
            (
                symbol,
                timeframe,
                int(row.time),
                float(row.open),
                float(row.high),
                float(row.low),
                float(row.close),
                int(row.tick_volume),
                int(row.spread),
                int(row.real_volume),
            )
            for row in frame.itertuples(index=False)
        ]

        self.conn.executemany(
            """
            INSERT INTO bars
            (symbol, timeframe, time, open, high, low, close,
             tick_volume, spread, real_volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol, timeframe, time) DO UPDATE SET
                open=excluded.open,
                high=excluded.high,
                low=excluded.low,
                close=excluded.close,
                tick_volume=excluded.tick_volume,
                spread=excluded.spread,
                real_volume=excluded.real_volume
            """,
            rows,
        )
        self.conn.commit()
        return len(rows)

    def summary(self, symbol: str, timeframe: str) -> tuple[int, int | None, int | None]:
        row = self.conn.execute(
            """
            SELECT COUNT(*), MIN(time), MAX(time)
            FROM bars
            WHERE symbol=? AND timeframe=?
            """,
            (symbol, timeframe),
        ).fetchone()
        return int(row[0]), row[1], row[2]

    def close(self) -> None:
        self.conn.close()
