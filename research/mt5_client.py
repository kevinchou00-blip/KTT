from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import MetaTrader5 as mt5


@dataclass(slots=True)
class ConnectionResult:
    ok: bool
    message: str
    symbol: str | None = None


class MT5ReadOnlyClient:
    TIMEFRAMES = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1,
        "D1": mt5.TIMEFRAME_D1,
    }

    def __init__(self, candidates: list[str]) -> None:
        self.candidates = candidates
        self.symbol: str | None = None
        self.connected = False

    def connect(self) -> ConnectionResult:
        if not mt5.initialize():
            return ConnectionResult(False, f"MT5连接失败：{mt5.last_error()}")

        symbols = mt5.symbols_get() or []
        available = {s.name.upper(): s.name for s in symbols}

        for candidate in self.candidates:
            actual = available.get(candidate.upper())
            if actual and mt5.symbol_select(actual, True):
                self.symbol = actual
                break

        if self.symbol is None:
            for upper, actual in available.items():
                if "XAUUSD" in upper and mt5.symbol_select(actual, True):
                    self.symbol = actual
                    break

        if self.symbol is None:
            mt5.shutdown()
            return ConnectionResult(False, "已连接MT5，但未找到黄金品种")

        account = mt5.account_info()
        self.connected = True
        server = getattr(account, "server", "未知服务器") if account else "未知服务器"
        login = getattr(account, "login", "-") if account else "-"
        return ConnectionResult(
            True,
            f"已连接：{server}｜账户 {login}｜品种 {self.symbol}",
            self.symbol,
        )

    def fetch(self, timeframe: str, count: int) -> pd.DataFrame:
        if not self.connected or not self.symbol:
            raise RuntimeError("MT5尚未连接")

        rates = mt5.copy_rates_from_pos(
            self.symbol, self.TIMEFRAMES[timeframe], 0, count
        )
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"{timeframe}读取失败：{mt5.last_error()}")

        return pd.DataFrame(rates)

    def shutdown(self) -> None:
        if self.connected:
            mt5.shutdown()
        self.connected = False
