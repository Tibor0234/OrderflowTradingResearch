from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from openpyxl import load_workbook

from global_services.data.provider import DataProvider
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
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
        assert workbook.sheetnames == ["Trades"]
        rows = list(sheet.values)
        assert rows[0] == tuple(
            exporter.HEADERS + ["strategy", "signal", "tag", "confidence"]
        )
        long_row = dict(zip(rows[0], rows[1]))
        short_shadow_row = dict(zip(rows[0], rows[2]))
        assert long_row["Session"] == 30
        assert long_row["Symbol"] == "BTCUSDT"
        assert short_shadow_row["Session"] == 30
        assert short_shadow_row["Symbol"] == "BTCUSDT"
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
        assert sheet.auto_filter.ref == "A1:Q3"
        assert {
            column.colId: column.showButton
            for column in sheet.auto_filter.filterColumn
        } == {
            column_index: column_index in {0, 1, 2}
            for column_index in range(sheet.max_column)
        }
        assert sheet["A1"].fill.fgColor.rgb[-6:] == "1F4E78"
        assert sheet["N1"].fill.fgColor.rgb[-6:] == "595959"
        assert sheet["N1"].alignment.horizontal == "left"
        assert sheet["N1"].alignment.indent == 1
        assert sheet["N1"].border.right.style == "thin"
        assert sheet["N2"].border.left is None
        assert sheet["N2"].border.right.style == "thin"
        assert sheet["N2"].border.bottom.style == "thin"
        assert sheet["D2"].font.color.rgb[-6:] == "008000"
        assert sheet["I2"].font.color.rgb[-6:] == "C00000"
        assert sheet["I2"].data_type == "n"
        assert sheet["I2"].number_format == exporter.CURRENCY_FORMAT
        assert sheet["D3"].font.color.rgb[-6:] == "D07070"
        assert sheet["I3"].font.color.rgb[-6:] == "70AD47"
        assert sheet["C3"].font.color.rgb[-6:] == "999999"
        assert sheet["C3"].fill.fgColor.rgb[-6:] == "F2F2F2"
        assert sheet["N2"].data_type == "s"
        assert sheet["N2"].number_format == "General"
        assert sheet["N3"].data_type == "n"
        assert sheet["O3"].data_type == "n"
        assert sheet["P2"].data_type == "s"
        assert sheet["P2"].number_format == "General"
        assert sheet["Q3"].data_type == "n"
        assert not sheet["C3"].font.italic
        assert not sheet["D3"].font.italic
        assert not sheet["I3"].font.italic
        assert sheet["G2"].number_format == exporter.CURRENCY_FORMAT
        assert sheet["I2"].number_format == exporter.CURRENCY_FORMAT
        assert sheet["E2"].number_format == exporter.NUMBER_FORMAT
        assert sheet["M2"].number_format == exporter.DURATION_FORMAT
        assert sheet["A2"].number_format == "General"
    finally:
        workbook.close()


def test_trade_export_uses_one_worksheet_for_empty_sessions(tmp_path, monkeypatch):
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
        assert workbook.sheetnames == ["Trades"]
        sheet = workbook.active
        assert list(sheet.values) == [tuple(exporter.HEADERS)]
        assert sheet.auto_filter.ref == "A1:M1"
    finally:
        workbook.close()

    session_counter.session = 2
    monkeypatch.setattr(provider, "symbol", "ETHUSDT")
    exporter._on_session_pair_end()

    workbook = load_workbook(workbook_path, data_only=True)
    try:
        assert workbook.sheetnames == ["Trades"]
        assert list(workbook["Trades"].values) == [tuple(exporter.HEADERS)]
        assert workbook["Trades"].auto_filter.ref == "A1:M1"
    finally:
        workbook.close()


def test_trade_export_appends_session_pairs_and_expands_metadata(tmp_path, monkeypatch):
    provider = DataProvider()
    monkeypatch.setattr(provider, "symbol", "BTCUSDT")
    monkeypatch.setattr(provider, "time", 1_000)
    bus = EventBus()
    monkeypatch.setattr(bus, "listeners", {})
    counter = SessionCounter(
        session=10,
        symbol="BTCUSDT",
        session_pair_count=1,
        selected_session_pairs=3,
    )
    exporter = TradeExcelExporter(tmp_path, counter)

    def make_trade(metadata, is_shadow=False):
        trade = Trade(
            id=uuid4(),
            execution_price=Decimal("100"),
            side=Side.BUY,
            margin=Decimal("50"),
            leverage=Decimal("2"),
            metadata=metadata,
            is_shadow=is_shadow,
        )
        trade.avg_close_price = Decimal("101")
        trade.close_time = 3_000
        return trade

    bus.emit(EventBusMsgType.TRADE_CLOSE, make_trade({"first": "a", "shared": 1}))
    bus.emit(EventBusMsgType.TRADE_CLOSE, make_trade({"ignored": "shadow"}, is_shadow=True))
    bus.emit(EventBusMsgType.SESSION_PAIR_END)

    workbook_path = tmp_path / "trades.xlsx"
    workbook = load_workbook(workbook_path, data_only=True)
    try:
        assert workbook.sheetnames == ["Trades"]
        assert workbook["Trades"].max_row == 2
        assert workbook["Trades"].auto_filter.ref == "A1:O2"
    finally:
        workbook.close()

    counter.session = 11
    monkeypatch.setattr(provider, "symbol", "ETHUSDT")
    bus.emit(EventBusMsgType.SESSION_PAIR_END)
    bus.emit(EventBusMsgType.TRADE_CLOSE, make_trade({"shared": 2, "second": "b"}))
    bus.emit(EventBusMsgType.SESSION_PAIR_END)
    bus.emit(EventBusMsgType.PROCESS_END)

    workbook = load_workbook(workbook_path, data_only=True)
    try:
        assert workbook.sheetnames == ["Trades"]
        sheet = workbook["Trades"]
        rows = list(sheet.values)
        assert rows[0] == tuple(exporter.HEADERS + ["first", "shared", "second"])
        assert len(rows) == 3
        first = dict(zip(rows[0], rows[1]))
        second = dict(zip(rows[0], rows[2]))
        assert (first["Session"], first["Symbol"]) == (10, "BTCUSDT")
        assert (second["Session"], second["Symbol"]) == (11, "ETHUSDT")
        assert (first["first"], first["shared"], first["second"]) == ("a", 1, None)
        assert (second["first"], second["shared"], second["second"]) == (None, 2, "b")
        assert sheet.auto_filter.ref == "A1:P3"
        assert {
            column.colId for column in sheet.auto_filter.filterColumn if column.showButton
        } == {0, 1, 2}
        assert sheet["P2"].border.right.style == "thin"
    finally:
        workbook.close()
