from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from global_services.data.provider import DataProvider
from trading.market_entities.trade import Trade
from trading.market_entities.utils import Side


class MLTradeParquetExporter:
    """Export one completed run of real and shadow trades to Parquet."""

    def __init__(
        self,
        output_directory: str | Path,
        schema_version: int | str,
        strategy_name: str,
        run_started_at: datetime,
    ):
        self.output_directory = Path(output_directory)
        self.schema_version = str(schema_version)
        self.strategy_name = self._safe_path_part(strategy_name)
        self.run_started_at = run_started_at
        self.run_id = run_started_at.strftime("%Y-%m-%dT%H-%M-%S")
        self.session_counter = None
        self.records: list[dict[str, Any]] = []
        self._exported = False

        EventBus().subscribe(EventBusMsgType.TRADE_CLOSE, self._on_trade_close)
        EventBus().subscribe(EventBusMsgType.SESSION_PAIR_END, self._on_session_pair_end)
        EventBus().subscribe(EventBusMsgType.PROCESS_END, self._save_parquet)

    def set_session_counter(self, session_counter):
        """Set the session counter used to identify session pairs."""
        self.session_counter = session_counter
        return self

    def _on_trade_close(self, trade: Trade):
        """Store a flattened record for a closed trade."""
        session_pair_id = None
        session_number = None
        if self.session_counter is not None:
            session_number = self.session_counter.session
            session_pair_id = self.session_counter.session_pair

        record = {
            "run_id": self.run_id,
            "run_started_at": self.run_started_at.isoformat(timespec="seconds"),
            "session_number": session_number,
            "session_pair_id": session_pair_id,
            "trade_id": str(trade.id),
            "symbol": DataProvider().get_symbol(),
            "is_shadow": trade.is_shadow,
            "side": "BUY" if trade.side == Side.BUY else "SELL",
            "entry_price": self._to_float(trade.execution_price),
            "close_price": self._to_float(trade.avg_close_price),
            "invested_value": self._to_float(trade.invested_value),
            "leverage": self._to_float(trade.leverage),
            "realized_pnl": self._to_float(trade.realized_pnl),
            "open_time_ms": trade.open_time,
            "close_time_ms": trade.close_time,
            "duration_seconds": (trade.close_time - trade.open_time) / 1000,
        }
        record.update({f"metadata_{key}": self._to_parquet_value(value) for key, value in trade.metadata.items()})
        self.records.append(record)

    def _on_session_pair_end(self):
        """Keep session-pair boundaries in the records without writing partial files."""

    def _save_parquet(self):
        """Write all records from this run to one Parquet file."""
        if self._exported or not self.records:
            return

        output_path = (
            self.output_directory
            / f"schema_v{self.schema_version}"
            / f"strategy={self.strategy_name}"
            / f"year={self.run_started_at.year:04d}"
            / f"month={self.run_started_at.month:02d}"
            / f"run_{self.run_id}.parquet"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        table = pa.Table.from_pylist(self.records)
        pq.write_table(table, output_path)
        self._exported = True

    @staticmethod
    def _safe_path_part(value: str) -> str:
        return "".join(char if char.isalnum() or char in "._-" else "_" for char in value)

    @staticmethod
    def _to_float(value) -> float | None:
        return float(value) if value is not None else None

    @classmethod
    def _to_parquet_value(cls, value):
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (list, tuple, dict)):
            return json.dumps(value, default=str, sort_keys=True)
        return str(value)
