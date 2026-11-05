from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side as BorderSide
from openpyxl.worksheet.filters import FilterColumn
from openpyxl.utils import get_column_letter

from global_services.data.provider import DataProvider
from market_feed.utils import SessionCounter
from global_services.events.bus import EventBus
from global_services.events.utils import EventBusMsgType
from trading.market_entities.trade import Trade
from trading.market_entities.utils import Side


class TradeExcelExporter:
    """Exports closed trades to an Excel workbook, grouped by session pair."""

    HEADERS = [
        "Is Shadow",
        "Side",
        "Avg Entry Price",
        "Avg Close Price",
        "Invested Margin",
        "Leverage",
        "Realized PnL",
        "Fees Paid",
        "Open Time",
        "Close Time",
        "Duration",
    ]
    INVALID_SHEET_CHARS = str.maketrans({char: "-" for char in "\\/*?:[]"})
    FILTER_HEADERS = {"Is Shadow", "Side"}
    CURRENCY_HEADERS = {"Invested Margin", "Realized PnL", "Fees Paid"}
    DURATION_HEADER = "Duration"
    CURRENCY_FORMAT = '$#,##0.00;-$#,##0.00'
    NUMBER_FORMAT = '#,##0.00;-#,##0.00'
    DURATION_FORMAT = "[h]:mm:ss"
    DEFAULT_HEADER_COLOR = "FF1F4E78"
    METADATA_HEADER_COLOR = "FF595959"
    HEADER_TEXT_COLOR = "FFFFFFFF"
    CELL_SEPARATOR_COLOR = "FFD9DDE3"
    TEXT_COLOR = "FF202020"
    SHADOW_TEXT_COLOR = "FF999999"
    LONG_COLOR = "FF008000"
    SHORT_COLOR = "FFC00000"
    SHADOW_LONG_COLOR = "FF70AD47"
    SHADOW_SHORT_COLOR = "FFD07070"
    HEADER_WIDTHS = {
        "Is Shadow": 12,
        "Side": 12,
        "Avg Entry Price": 18,
        "Avg Close Price": 18,
        "Invested Margin": 18,
        "Leverage": 12,
        "Realized PnL": 18,
        "Fees Paid": 16,
        "Open Time": 22,
        "Close Time": 22,
        "Duration": 14,
    }

    def __init__(self, report_directory: Path, session_counter: SessionCounter, export_shadow_trades: bool = False):
        """Initialize the exporter and subscribe to trade lifecycle events."""
        self.report_directory = report_directory
        self.export_shadow_trades = export_shadow_trades
        self.session_counter = session_counter
        self.session_trades: list[Trade] = []

        self.workbook = Workbook()
        self.workbook.remove(self.workbook.active)

        EventBus().subscribe(EventBusMsgType.TRADE_CLOSE, self._on_trade_close)
        EventBus().subscribe(EventBusMsgType.SESSION_PAIR_END, self._on_session_pair_end)
        EventBus().subscribe(EventBusMsgType.PROCESS_END, self._save_workbook)

    def _on_trade_close(self, trade: Trade):
        """Store a closed trade for the current session pair."""
        if self.export_shadow_trades or not trade.is_shadow:
            self.session_trades.append(trade)

    def _on_session_pair_end(self):
        """Export the current session pair's trades to a dedicated worksheet."""
        symbol = DataProvider().get_symbol()
        session_number = self.session_counter.session if self.session_counter else len(self.workbook.sheetnames) + 1
        sheet_name = f"Session {session_number} - {symbol}".translate(self.INVALID_SHEET_CHARS)[:31]
        sheet = self.workbook.create_sheet(title=sheet_name)
        metadata_keys = list(dict.fromkeys(
            key for trade in self.session_trades for key in trade.metadata
        ))
        sheet.append(self.HEADERS + metadata_keys)

        for trade in self.session_trades:
            sheet.append([
                trade.is_shadow,
                "LONG" if trade.side == Side.BUY else "SHORT",
                self._round_to_two_decimals(trade.execution_price),
                self._round_to_two_decimals(trade.avg_close_price),
                self._round_to_two_decimals(trade.invested_margin),
                self._round_to_two_decimals(trade.leverage),
                self._round_to_two_decimals(trade.realized_pnl),
                self._round_to_two_decimals(trade.fees_paid),
                self._format_time(trade.open_time),
                self._format_time(trade.close_time),
                timedelta(seconds=round((trade.close_time - trade.open_time) / 1000)),
                *[
                    self._format_metadata_value(
                        trade.metadata.get(key)
                    )
                    for key in metadata_keys
                ],
            ])

        self._format_worksheet(sheet, len(self.HEADERS) + 1)
        self.session_trades = []
        self._save_workbook()

    def _format_worksheet(self, sheet, metadata_start_column: int):
        sheet.sheet_view.showGridLines = True
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        sheet.auto_filter.filterColumn = [
            FilterColumn(
                colId=column_index,
                showButton=(
                    (
                        column_index + 1 < metadata_start_column
                        and header.value in self.FILTER_HEADERS
                    )
                ),
            )
            for column_index, header in enumerate(sheet[1])
        ]
        sheet.row_dimensions[1].height = 30

        for cell in sheet[1]:
            is_metadata = cell.column >= metadata_start_column
            fill_color = (
                self.METADATA_HEADER_COLOR
                if is_metadata
                else self.DEFAULT_HEADER_COLOR
            )
            cell.fill = PatternFill(fill_type="solid", fgColor=fill_color)
            cell.font = Font(
                name="Calibri",
                size=11,
                bold=True,
                color=self.HEADER_TEXT_COLOR,
            )
            cell.alignment = Alignment(
                horizontal="left" if (
                    cell.value in self.FILTER_HEADERS
                    or is_metadata
                ) else "center",
                vertical="center",
                wrap_text=True,
                indent=1 if (
                    cell.value in self.FILTER_HEADERS
                    or is_metadata
                ) else 0,
            )
            cell.border = Border(
                bottom=BorderSide(style="medium", color="FFBFBFBF"),
                right=BorderSide(style="thin", color=self.CELL_SEPARATOR_COLOR),
            )

        for row_index, row in enumerate(
            sheet.iter_rows(min_row=2),
            start=2,
        ):
            is_shadow = bool(row[self.HEADERS.index("Is Shadow")].value)
            row_fill = (
                "FFF2F2F2"
                if is_shadow
                else "FFF7F9FC" if row_index % 2 == 0 else "FFFFFFFF"
            )
            for cell in row:
                cell.fill = PatternFill(fill_type="solid", fgColor=row_fill)
                cell.font = Font(
                    name="Calibri",
                    size=11,
                    color=self.SHADOW_TEXT_COLOR if is_shadow else self.TEXT_COLOR,
                    italic=False,
                )
                cell.alignment = Alignment(vertical="center")
                cell.border = Border(
                    bottom=BorderSide(
                        style="thin",
                        color=self.CELL_SEPARATOR_COLOR,
                    ),
                    right=BorderSide(
                        style="thin",
                        color=self.CELL_SEPARATOR_COLOR,
                    ),
                )

                header = sheet.cell(row=1, column=cell.column).value
                if header == self.DURATION_HEADER:
                    cell.number_format = self.DURATION_FORMAT
                elif header in self.CURRENCY_HEADERS:
                    cell.value = self._round_to_two_decimals(cell.value)
                    cell.number_format = self.CURRENCY_FORMAT
                elif (
                    isinstance(cell.value, (int, float))
                    and not isinstance(cell.value, bool)
                ):
                    cell.value = self._round_to_two_decimals(cell.value)
                    cell.number_format = self.NUMBER_FORMAT

            side_cell = row[self.HEADERS.index("Side")]
            side_color = (
                self.SHADOW_LONG_COLOR
                if is_shadow and side_cell.value == "LONG"
                else self.SHADOW_SHORT_COLOR
                if is_shadow
                else self.LONG_COLOR
                if side_cell.value == "LONG"
                else self.SHORT_COLOR
            )
            side_cell.font = Font(
                name="Calibri",
                size=11,
                bold=True,
                italic=False,
                color=side_color,
            )

            pnl_cell = row[self.HEADERS.index("Realized PnL")]
            if pnl_cell.value is not None:
                pnl_color = (
                    self.SHADOW_LONG_COLOR
                    if is_shadow and pnl_cell.value >= 0
                    else self.SHADOW_SHORT_COLOR
                    if is_shadow
                    else self.LONG_COLOR
                    if pnl_cell.value >= 0
                    else self.SHORT_COLOR
                )
                pnl_cell.font = Font(
                    name="Calibri",
                    size=11,
                    bold=True,
                    italic=False,
                    color=pnl_color,
                )

        for column_index, header in enumerate(sheet[1], start=1):
            column_values_length = max(
                len(str(cell.value or ""))
                for cell in sheet[get_column_letter(column_index)]
            )
            if header.value in self.HEADER_WIDTHS:
                width = self.HEADER_WIDTHS[header.value]
            else:
                width = min(
                    max(column_values_length + 2, 14),
                    32,
                )
            has_filter_button = (
                column_index < metadata_start_column
                and header.value in self.FILTER_HEADERS
            )
            if has_filter_button:
                width = max(
                    width,
                    min(max(column_values_length + 5, 14), 32),
                )
            sheet.column_dimensions[get_column_letter(column_index)].width = width

    def _save_workbook(self):
        """Save the workbook to the configured report directory."""
        if not self.workbook.sheetnames:
            return
        self.workbook.save(self.report_directory / "trades.xlsx")

    @staticmethod
    def _format_time(timestamp_ms):
        """Convert a millisecond timestamp to a formatted datetime string."""
        return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _format_metadata_value(value):
        """Convert a trade metadata value to an Excel-compatible representation."""
        if isinstance(value, Decimal):
            return TradeExcelExporter._round_to_two_decimals(value)
        if value is None or isinstance(value, (str, int, bool)):
            return value
        if isinstance(value, float):
            return TradeExcelExporter._round_to_two_decimals(value)
        return str(value)

    @staticmethod
    def _round_to_two_decimals(value):
        """Round numeric values consistently to two decimal places."""
        return float(
            Decimal(str(value)).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        )
