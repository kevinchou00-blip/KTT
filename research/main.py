from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from research.database import ResearchDatabase
from research.mt5_client import MT5ReadOnlyClient


ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


class SyncWorker(QThread):
    progress = Signal(str, int, str)
    completed = Signal()
    failed = Signal(str)

    def __init__(self, client, database, symbol, timeframes):
        super().__init__()
        self.client = client
        self.database = database
        self.symbol = symbol
        self.timeframes = timeframes

    def run(self):
        try:
            total = len(self.timeframes)
            for index, (timeframe, count) in enumerate(self.timeframes.items(), start=1):
                self.progress.emit(timeframe, int((index - 1) / total * 100), "正在读取…")
                frame = self.client.fetch(timeframe, int(count))
                saved = self.database.upsert_bars(self.symbol, timeframe, frame)
                self.progress.emit(
                    timeframe,
                    int(index / total * 100),
                    f"完成，写入 {saved:,} 根",
                )
            self.completed.emit()
        except Exception as exc:
            self.failed.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.client = MT5ReadOnlyClient(self.config["symbol_candidates"])
        self.database = ResearchDatabase(ROOT / self.config["database"])
        self.symbol = None
        self.worker = None

        self.setWindowTitle("KTTP Research v0.1 Alpha")
        self.resize(980, 650)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)

        title = QLabel("KTTP Research")
        title.setStyleSheet("font-size: 27px; font-weight: 800; color: #ffd15c;")
        subtitle = QLabel("历史数据中心｜永久只读｜无交易执行功能")
        subtitle.setStyleSheet("color: #67d995; font-size: 14px;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        status_frame = QFrame()
        status_frame.setStyleSheet(
            "QFrame {background:#202733; border:1px solid #465369; border-radius:9px;}"
        )
        status_layout = QVBoxLayout(status_frame)
        self.connection_label = QLabel("状态：尚未连接MT5")
        self.connection_label.setWordWrap(True)
        status_layout.addWidget(self.connection_label)

        buttons = QHBoxLayout()
        self.connect_button = QPushButton("连接 MT5")
        self.sync_button = QPushButton("同步历史数据")
        self.sync_button.setEnabled(False)
        buttons.addWidget(self.connect_button)
        buttons.addWidget(self.sync_button)
        buttons.addStretch()
        status_layout.addLayout(buttons)
        layout.addWidget(status_frame)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.table = QTableWidget(5, 5)
        self.table.setHorizontalHeaderLabels(
            ["周期", "数据库K线数", "最早时间", "最新时间", "状态"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        for row, timeframe in enumerate(self.config["timeframes"].keys()):
            self.table.setItem(row, 0, QTableWidgetItem(timeframe))
            for col in range(1, 5):
                self.table.setItem(row, col, QTableWidgetItem("-"))
        layout.addWidget(self.table)

        note = QLabel(
            "v0.1只负责历史数据同步。下一版才会加入M15/M5/M1信号扫描。"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#aeb8c7;")
        layout.addWidget(note)

        self.setCentralWidget(root)
        self.setStyleSheet(
            """
            QWidget {background:#151922; color:#eef1f5; font-family:'Microsoft YaHei UI'; font-size:13px;}
            QPushButton {background:#315b8d; border:1px solid #5d83b1; border-radius:6px; padding:9px 18px;}
            QPushButton:disabled {background:#353b45; color:#7d8796;}
            QProgressBar {border:1px solid #4a5668; border-radius:5px; text-align:center; background:#2c3441;}
            QProgressBar::chunk {background:#4caf78;}
            QTableWidget {background:#1d2430; gridline-color:#3e4a5d; border:1px solid #465369;}
            QHeaderView::section {background:#293242; padding:8px; border:0;}
            """
        )

        self.connect_button.clicked.connect(self.connect_mt5)
        self.sync_button.clicked.connect(self.sync_history)

    def connect_mt5(self):
        result = self.client.connect()
        self.connection_label.setText(result.message)
        if result.ok:
            self.symbol = result.symbol
            self.sync_button.setEnabled(True)
            self.refresh_table()
        else:
            QMessageBox.warning(self, "连接失败", result.message)

    def sync_history(self):
        if not self.symbol:
            return

        self.connect_button.setEnabled(False)
        self.sync_button.setEnabled(False)
        self.progress.setValue(0)

        self.worker = SyncWorker(
            self.client,
            self.database,
            self.symbol,
            self.config["timeframes"],
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_progress(self, timeframe, percent, status):
        self.progress.setValue(percent)
        row = list(self.config["timeframes"].keys()).index(timeframe)
        self.table.setItem(row, 4, QTableWidgetItem(status))

    def on_completed(self):
        self.progress.setValue(100)
        self.connection_label.setText(
            f"历史同步完成｜品种 {self.symbol}｜数据库已更新"
        )
        self.connect_button.setEnabled(True)
        self.sync_button.setEnabled(True)
        self.refresh_table()
        QMessageBox.information(self, "完成", "历史数据同步完成。")

    def on_failed(self, message):
        self.connect_button.setEnabled(True)
        self.sync_button.setEnabled(True)
        QMessageBox.critical(self, "同步失败", message)

    def refresh_table(self):
        if not self.symbol:
            return

        for row, timeframe in enumerate(self.config["timeframes"].keys()):
            count, first_time, last_time = self.database.summary(self.symbol, timeframe)

            def fmt(value):
                return (
                    "-"
                    if value is None
                    else datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M")
                )

            self.table.setItem(row, 1, QTableWidgetItem(f"{count:,}"))
            self.table.setItem(row, 2, QTableWidgetItem(fmt(first_time)))
            self.table.setItem(row, 3, QTableWidgetItem(fmt(last_time)))
            if count > 0:
                self.table.setItem(row, 4, QTableWidgetItem("数据库已有数据"))

        self.table.resizeColumnsToContents()

    def closeEvent(self, event):
        self.client.shutdown()
        self.database.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
