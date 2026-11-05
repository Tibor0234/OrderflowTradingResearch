from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from openpyxl import load_workbook

from global_services.data.provider import DataProvider
from global_services.events.bus import EventBus
from market_feed.utils import SessionCounter
from report_generator.trade.excel_export import TradeExcelExporter
from trading.market_entities.trade import Trade
from trading.market_entities.utils import Side


def test_trade_export_formats_trade_margins_and_shadow_rows(tmp_path, monkeypatch):
    provider = DataProvider()
    monkeypatch.setattr(provider, "symbol", "BTCUSDT")
    monkeypatch.setattr(provider, "time", 1_000)
    monkeypatch.setattr(EventBus(), "subscribe", lambda *args: None)
    trade = Trade(
        id=uuid4(),
        execution_price=Decimal("100"),
        side=Side.BUY,
        margin=Decimal("100"),
        leverage=Decimal("2"),
        metadata={"strategy": "test", "signal": "entry", "tag": "example"},
    )
    trade.charge_fee(Decimal("0.001"))
    trade.charge_fee_from_margin(Decimal("50"), Decimal("0.001"))
    trade.avg_close_price = Decimal("110")
    trade.close_time = 3_000
    shadow_trade = Trade(
        id=uuid4(),
        execution_price=Decimal("105.678"),
        side=Side.SELL,
        margin=Decimal("50"),
        leverage=Decimal("2.345"),
        metadata={
            "strategy": Decimal("2.50"),
            "signal": Decimal("3.40"),
            "confidence": Decimal("1.236"),
        },
        is_shadow=True,
    )
    shadow_trade.avg_close_price = Decimal("98")
    shadow_trade.realized_pnl = Decimal("1.256")
    shadow_trade.close_time = 3_601_000

    exporter = TradeExcelExporter(
        tmp_path,
        SessionCounter(
            session=30,
            symbol="BTCUSDT",
            session_pair_count=7,
            selected_session_pairs=10,
        ),
        export_shadow_trades=True,
    )
    exporter._on_trade_close(trade)
    exporter._on_trade_close(shadow_trade)
    exporter._on_session_pair_end()

    workbook = load_workbook(tmp_path / "trades.xlsx", data_only=True)
    try:
        sheet = workbook.active
        rows = list(sheet.values)
        assert rows[0][0] == "Is Shadow"
        assert "Symbol" not in rows[0]
        assert rows[0] == tuple(
            exporter.HEADERS + ["strategy", "signal", "tag", "confidence"]
        )
        long_row = dict(zip(rows[0], rows[1]))
        short_shadow_row = dict(zip(rows[0], rows[2]))
        assert long_row["Side"] == "LONG"
        assert long_row["Fees Paid"] == 0.3
        assert long_row["Realized PnL"] == -0.3
        assert long_row["Duration"] == timedelta(seconds=2)
        assert short_shadow_row["Side"] == "SHORT"
        assert short_shadow_row["Realized PnL"] == 1.26
        assert short_shadow_row["Duration"] == timedelta(hours=1)
        assert short_shadow_row["strategy"] == 2.5
        assert short_shadow_row["signal"] == 3.4
        assert short_shadow_row["tag"] is None
        assert short_shadow_row["confidence"] == 1.24

        assert sheet.freeze_panes == "A2"
        assert sheet.sheet_view.showGridLines
        assert sheet.auto_filter.ref == "A1:O3"
        assert {
            column.colId: column.showButton
            for column in sheet.auto_filter.filterColumn
        } == {
            column_index: column_index in {0, 1}
            for column_index in range(sheet.max_column)
        }
        assert sheet["A1"].fill.fgColor.rgb[-6:] == "1F4E78"
        assert sheet["L1"].fill.fgColor.rgb[-6:] == "595959"
        assert sheet["L1"].alignment.horizontal == "left"
        assert sheet["L1"].alignment.indent == 1
        assert sheet["L1"].border.right.style == "thin"
        assert sheet["L2"].border.left is None
        assert sheet["L2"].border.right.style == "thin"
        assert sheet["L2"].border.bottom.style == "thin"
        assert sheet["B2"].font.color.rgb[-6:] == "008000"
        assert sheet["G2"].font.color.rgb[-6:] == "C00000"
        assert sheet["G2"].data_type == "n"
        assert sheet["G2"].number_format == exporter.CURRENCY_FORMAT
        assert sheet["B3"].font.color.rgb[-6:] == "D07070"
        assert sheet["G3"].font.color.rgb[-6:] == "70AD47"
        assert sheet["A3"].font.color.rgb[-6:] == "999999"
        assert sheet["A3"].fill.fgColor.rgb[-6:] == "F2F2F2"
        assert sheet["L2"].data_type == "s"
        assert sheet["L2"].number_format == "General"
        assert sheet["L3"].data_type == "n"
        assert sheet["M3"].data_type == "n"
        assert sheet["N2"].data_type == "s"
        assert sheet["N2"].number_format == "General"
        assert sheet["O3"].data_type == "n"
        assert not sheet["A3"].font.italic
        assert not sheet["B3"].font.italic
        assert not sheet["G3"].font.italic
        assert sheet["E2"].number_format == exporter.CURRENCY_FORMAT
        assert sheet["G2"].number_format == exporter.CURRENCY_FORMAT
        assert sheet["C2"].number_format == exporter.NUMBER_FORMAT
        assert sheet["K2"].number_format == exporter.DURATION_FORMAT
    finally:
        workbook.close()


def test_trade_export_creates_worksheets_for_empty_sessions(tmp_path, monkeypatch):
    provider = DataProvider()
    monkeypatch.setattr(provider, "symbol", "BTCUSDT")
    monkeypatch.setattr(EventBus(), "subscribe", lambda *args: None)
    session_counter = SessionCounter(
        session=1,
        symbol="BTCUSDT",
        session_pair_count=1,
        selected_session_pairs=2,
    )
    exporter = TradeExcelExporter(tmp_path, session_counter)

    exporter._on_session_pair_end()

    workbook_path = tmp_path / "trades.xlsx"
    assert workbook_path.exists()
    workbook = load_workbook(workbook_path, data_only=True)
    try:
        assert workbook.sheetnames == ["Session 1 - BTCUSDT"]
        sheet = workbook.active
        assert list(sheet.values) == [tuple(exporter.HEADERS)]
        assert sheet.auto_filter.ref == "A1:K1"
    finally:
        workbook.close()

    session_counter.session = 2
    monkeypatch.setattr(provider, "symbol", "ETHUSDT")
    exporter._on_session_pair_end()

    workbook = load_workbook(workbook_path, data_only=True)
    try:
        assert workbook.sheetnames == [
            "Session 1 - BTCUSDT",
            "Session 2 - ETHUSDT",
        ]
        assert all(
            list(sheet.values) == [tuple(exporter.HEADERS)]
            for sheet in workbook.worksheets
        )
    finally:
        workbook.close()
