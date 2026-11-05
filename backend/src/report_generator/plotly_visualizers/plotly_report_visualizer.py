import logging
import re
from io import BytesIO
from urllib.request import Request, urlopen

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from report_generator.plotly_visualizers.plotly_equity_curve_visualizer import (
    PlotlyEquityCurveVisualizer,
)
from report_generator.plotly_visualizers.plotly_statistics_visualizer import (
    PlotlyStatisticsVisualizer,
)


logger = logging.getLogger(__name__)


class PlotlyReportVisualizer:
    """Renders the Plotly report visualizations and statistics to PDF."""

    PAGE_BACKGROUND = "#000000"
    PRIMARY_TEXT = "#eeeeee"
    MUTED_TEXT = "#999999"
    DIVIDER = "#333333"
    EQUITY_LINE = "#19c995"
    EQUITY_FILL = "#19c995"
    STARTING_BALANCE = "#f25c6c"
    CURRENT_EQUITY = "#ffffff"
    SYMBOL_QUOTES = (
        "USDT",
        "USDC",
        "FDUSD",
        "BUSD",
        "TUSD",
        "USDP",
        "DAI",
        "USD",
        "BTC",
        "ETH",
        "BNB",
        "EUR",
        "TRY",
        "BRL",
        "JPY",
        "GBP",
    )
    SYMBOL_LOGO_SIZE = 33
    SYMBOL_LOGO_DIVIDER_GAP = 11
    SYMBOL_LOGO_MAX_BYTES = 1_000_000
    SYMBOL_LOGO_TIMEOUT_SECONDS = 3

    def __init__(self):
        self._symbol_logo_cache: dict[str, bytes | None] = {}

    def render_pdf(
        self,
        report_path,
        title,
        time_range,
        plotly_equity_curve_visualizer: PlotlyEquityCurveVisualizer,
        plotly_statistics_visualizer: PlotlyStatisticsVisualizer,
        symbol: str | None = None,
    ):
        """Render the report content and save it as a PDF."""
        report_path.parent.mkdir(parents=True, exist_ok=True)
        page_width, page_height = A4
        pdf = canvas.Canvas(str(report_path), pagesize=A4)

        pdf.setFillColor(colors.HexColor(self.PAGE_BACKGROUND))
        pdf.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        content_width = page_width - 80
        header_x = 40
        header_y = page_height - 54
        pdf.setFillColor(colors.HexColor(self.PRIMARY_TEXT))
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(header_x, header_y, title)
        pdf.setFillColor(colors.HexColor(self.MUTED_TEXT))
        pdf.setFont("Helvetica", 9)
        pdf.drawString(header_x, header_y - 18, time_range)
        if symbol is not None:
            self._draw_header_symbol(
                pdf,
                symbol,
                header_x,
                header_y,
                content_width,
            )
        pdf.setStrokeColor(colors.HexColor(self.DIVIDER))
        pdf.setLineWidth(0.6)
        pdf.line(header_x, header_y - 31, header_x + content_width, header_y - 31)

        self._draw_equity_curve(
            pdf,
            header_x,
            448,
            content_width,
            285,
            plotly_equity_curve_visualizer,
        )
        self._draw_statistics(
            pdf,
            header_x,
            420,
            content_width,
            plotly_statistics_visualizer,
        )
        pdf.save()

    @classmethod
    def _symbol_logo_url(cls, symbol: str) -> str | None:
        normalized_symbol = re.sub(r"[^A-Z0-9]", "", symbol.strip().upper())
        if not normalized_symbol or normalized_symbol in {"NONE", "NULL", "NAN"}:
            return None

        for quote in cls.SYMBOL_QUOTES:
            if normalized_symbol.endswith(quote):
                normalized_symbol = normalized_symbol[: -len(quote)]
                break

        if not re.fullmatch(r"[A-Z0-9]{1,20}", normalized_symbol):
            return None

        return (
            "https://assets.coincap.io/assets/icons/"
            f"{normalized_symbol.lower()}@2x.png"
        )

    def _get_symbol_logo(self, symbol: str) -> bytes | None:
        logo_url = self._symbol_logo_url(symbol)
        if logo_url is None:
            return None
        if logo_url in self._symbol_logo_cache:
            return self._symbol_logo_cache[logo_url]

        try:
            with urlopen(
                Request(logo_url, headers={"User-Agent": "Mozilla/5.0"}),
                timeout=self.SYMBOL_LOGO_TIMEOUT_SECONDS,
            ) as response:
                logo_data = response.read(self.SYMBOL_LOGO_MAX_BYTES + 1)
            if len(logo_data) > self.SYMBOL_LOGO_MAX_BYTES:
                logger.warning("CoinCap logo for %s exceeded the size limit.", symbol)
                logo_data = None
            elif not logo_data:
                logger.warning("CoinCap returned an empty logo for %s.", symbol)
                logo_data = None
        except OSError as error:
            logger.warning("Could not load CoinCap logo for %s: %s", symbol, error)
            logo_data = None

        self._symbol_logo_cache[logo_url] = logo_data
        return logo_data

    def _draw_header_symbol(
        self,
        pdf,
        symbol: str,
        header_x: float,
        header_y: float,
        content_width: float,
    ):
        logo_data = self._get_symbol_logo(symbol)
        if logo_data is None:
            return

        try:
            logo = ImageReader(BytesIO(logo_data))
            logo_size = self.SYMBOL_LOGO_SIZE
            logo_x = header_x + content_width - logo_size
            logo_y = header_y - 31 + self.SYMBOL_LOGO_DIVIDER_GAP
            radius = logo_size / 2
            center_x = logo_x + radius
            center_y = logo_y + radius
            curve_offset = radius * 0.5522847498

            pdf.saveState()
            try:
                circular_clip = pdf.beginPath()
                circular_clip.moveTo(center_x + radius, center_y)
                circular_clip.curveTo(
                    center_x + radius,
                    center_y + curve_offset,
                    center_x + curve_offset,
                    center_y + radius,
                    center_x,
                    center_y + radius,
                )
                circular_clip.curveTo(
                    center_x - curve_offset,
                    center_y + radius,
                    center_x - radius,
                    center_y + curve_offset,
                    center_x - radius,
                    center_y,
                )
                circular_clip.curveTo(
                    center_x - radius,
                    center_y - curve_offset,
                    center_x - curve_offset,
                    center_y - radius,
                    center_x,
                    center_y - radius,
                )
                circular_clip.curveTo(
                    center_x + curve_offset,
                    center_y - radius,
                    center_x + radius,
                    center_y - curve_offset,
                    center_x + radius,
                    center_y,
                )
                circular_clip.close()
                pdf.clipPath(circular_clip, stroke=0, fill=0)
                pdf.drawImage(
                    logo,
                    logo_x,
                    logo_y,
                    width=logo_size,
                    height=logo_size,
                    mask="auto",
                )
            finally:
                pdf.restoreState()
        except (OSError, ValueError) as error:
            logger.warning("Could not render CoinCap logo for %s: %s", symbol, error)

    def _draw_statistics(self, pdf, x, top, width, statistics_visualizer):
        """Draw the statistics panel onto the PDF."""
        columns = statistics_visualizer.get_panel_columns()
        row_height = 23
        header_height = 21
        column_gap = 32
        column_width = (width - column_gap) / 2

        for column_index, (column_title, items) in enumerate(columns):
            column_x = x + column_index * (column_width + column_gap)
            pdf.setFillColor(colors.HexColor(self.PRIMARY_TEXT))
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(column_x, top, column_title)
            pdf.setStrokeColor(colors.HexColor(self.DIVIDER))
            pdf.setLineWidth(0.6)
            pdf.line(column_x, top - 8, column_x + column_width, top - 8)

            for row_index, (category, value) in enumerate(items):
                y = top - header_height - (row_index + 1) * row_height
                pdf.setFont("Helvetica", 9)
                pdf.setFillColor(colors.HexColor(self.MUTED_TEXT))
                pdf.drawString(column_x, y, category)
                pdf.setFillColor(self._value_color(value))
                pdf.drawRightString(
                    column_x + column_width,
                    y,
                    self._value_text(value),
                )

                if row_index < len(items) - 1:
                    pdf.setStrokeColor(colors.HexColor(self.DIVIDER))
                    pdf.setLineWidth(0.35)
                    pdf.line(
                        column_x,
                        y - 6,
                        column_x + column_width,
                        y - 6,
                    )

    def _draw_equity_curve(
        self,
        pdf,
        x,
        y,
        width,
        height,
        plotly_equity_curve_visualizer,
    ):
        """Draw the equity curve and its reference lines onto the PDF."""
        chart_width = width - 24
        plot_x = x + 12
        plot_y = y + height * 32 / 184
        plot_width = chart_width * 455 / 500
        plot_height = height * 136 / 184

        figure = plotly_equity_curve_visualizer.create_figure()
        trace = figure.data[0]
        shapes = [shape.to_plotly_json() for shape in figure.layout.shapes]
        point_indices = [float(index) for index in trace.x]
        values = [float(value) for value in trace.y]
        if not values:
            pdf.setFont("Helvetica", 10)
            pdf.setFillColor(colors.HexColor(self.MUTED_TEXT))
            pdf.drawCentredString(
                plot_x + plot_width / 2,
                plot_y + plot_height / 2,
                "No equity data",
            )
            return

        x_minimum, x_maximum = [float(value) for value in figure.layout.xaxis.range]
        y_minimum, y_maximum = [float(value) for value in figure.layout.yaxis.range]
        x_range = x_maximum - x_minimum or 1
        y_range = y_maximum - y_minimum or 1

        pdf.saveState()
        pdf.setFillColor(colors.HexColor(self.MUTED_TEXT))
        pdf.setFont("Helvetica", 8.25)
        for tick_value, tick_text in zip(
            figure.layout.yaxis.tickvals,
            figure.layout.yaxis.ticktext,
        ):
            tick_y = plot_y + (float(tick_value) - y_minimum) / y_range * plot_height
            pdf.drawString(
                plot_x + plot_width + chart_width * 5 / 500,
                tick_y - 3,
                str(tick_text),
            )

        for tick_value, tick_text in zip(
            figure.layout.xaxis.tickvals,
            figure.layout.xaxis.ticktext,
        ):
            tick_x = plot_x + (float(tick_value) - x_minimum) / x_range * plot_width
            pdf.drawCentredString(
                tick_x,
                plot_y - height * 16 / 184,
                str(tick_text),
            )
        pdf.restoreState()

        points = [
            (
                plot_x + (point_index - x_minimum) / x_range * plot_width,
                plot_y + (value - y_minimum) / y_range * plot_height,
            )
            for point_index, value in zip(point_indices, values)
        ]

        path = pdf.beginPath()
        path.moveTo(*points[0])
        for point in points[1:]:
            path.lineTo(*point)

        fill_path = pdf.beginPath()
        fill_path.moveTo(points[0][0], plot_y)
        for point in points:
            fill_path.lineTo(*point)
        fill_path.lineTo(points[-1][0], plot_y)
        fill_path.close()
        pdf.saveState()
        pdf.setFillColor(colors.HexColor(self.EQUITY_FILL))
        pdf.setFillAlpha(0.12)
        pdf.drawPath(fill_path, stroke=0, fill=1)
        pdf.restoreState()

        pdf.saveState()
        pdf.setStrokeColor(colors.HexColor(self.EQUITY_LINE))
        pdf.setLineWidth(float(trace.line.width) * 0.75)
        pdf.setLineCap(1)
        pdf.setLineJoin(1)
        pdf.drawPath(path, stroke=1, fill=0)
        pdf.restoreState()

        for shape in shapes:
            if shape.get("type") != "line" or shape.get("yref") != "y":
                continue

            line = shape.get("line", {})
            line_color = colors.HexColor(
                self.CURRENT_EQUITY
                if line.get("dash") == "dash"
                else self.STARTING_BALANCE
            )
            line_y = plot_y + (float(shape["y0"]) - y_minimum) / y_range * plot_height
            pdf.setStrokeColor(line_color)
            pdf.setLineWidth(float(line.get("width", 1)) * 0.75)
            if line.get("dash") == "dash":
                pdf.setDash(3.75, 3)
            else:
                pdf.setDash()
            pdf.line(plot_x, line_y, plot_x + plot_width, line_y)
            pdf.setDash()

        for annotation in figure.layout.annotations:
            annotation_data = annotation.to_plotly_json()
            annotation_y = (
                plot_y
                + (float(annotation_data["y"]) - y_minimum) / y_range * plot_height
                + float(annotation_data.get("yshift", 0)) * 0.75
            )
            annotation_font = annotation_data.get("font", {})
            annotation_color = (
                self.STARTING_BALANCE
                if annotation_data["text"].startswith("Starting Balance")
                else self.CURRENT_EQUITY
            )
            pdf.setFillColor(colors.HexColor(annotation_color))
            pdf.setFont("Helvetica", float(annotation_font.get("size", 10)) * 0.75)
            pdf.drawString(
                plot_x + chart_width * 17 / 500,
                annotation_y - 3,
                str(annotation_data["text"]),
            )

    @staticmethod
    def _value_text(value):
        """Extract the display text from a report value."""
        return str(getattr(value, "children", value))

    @staticmethod
    def _value_color(value):
        """Return the display color defined by the value style."""
        style = getattr(value, "style", {})
        return colors.HexColor(style.get("color", "#ffffff"))
