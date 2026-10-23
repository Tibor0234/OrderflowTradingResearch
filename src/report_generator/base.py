from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


class BaseReportGenerator:
    """Provides shared functionality for generating trading reports."""

    def __init__(self, report_directory: Path):
        """Initialize the report generator with its output directory."""
        self.report_directory = report_directory

    @staticmethod
    def create_report_directory(strategy_name: str, run_started_at: datetime) -> Path:
        """Create and return the report directory for a strategy run."""
        report_directory = (
            Path("reports")
            / f"strategy={strategy_name}"
            / f"year={run_started_at.year:04d}"
            / f"month={run_started_at.month:02d}"
            / f"run_{run_started_at:%Y-%m-%dT%H-%M-%S}"
        )
        report_directory.mkdir(parents=True, exist_ok=True)
        return report_directory

    def _format_time_range(self, start_timestamp):
        """Format the report time range from the start timestamp to the current time."""
        if start_timestamp is None:
            return "Session time unavailable"

        start_time = datetime.fromtimestamp(start_timestamp / 1000)
        end_time = datetime.fromtimestamp(self._get_current_time() / 1000)
        return f"{start_time:%Y-%m-%d %H:%M:%S} - {end_time:%Y-%m-%d %H:%M:%S}"

    def _render_pdf(self, report_path, title, time_range, equity_visualizer, statistics_visualizer):
        """Render the report content and save it as a PDF."""
        page_width, page_height = A4
        pdf = canvas.Canvas(str(report_path), pagesize=A4)

        pdf.setFillColor(colors.HexColor("#121212"))
        pdf.rect(0, 0, page_width, page_height, fill=1, stroke=0)
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(40, page_height - 50, title)
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(colors.HexColor("#aaaaaa"))
        pdf.drawString(40, page_height - 68, time_range)

        content_width = page_width - 80
        self._draw_equity_curve(pdf, 40, 400, content_width, 300, equity_visualizer)
        self._draw_statistics(pdf, 40, 370, content_width, statistics_visualizer)
        pdf.save()

    def _draw_statistics(self, pdf, x, top, width, statistics_visualizer):
        """Draw the statistics panel onto the PDF."""
        categories, values = statistics_visualizer.get_panel_content()
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(x, top, "Statistics")

        panel_top = top - 8
        panel_bottom = top - 28 - max(len(categories) - 1, 0) * 24 - 12
        pdf.setStrokeColor(colors.HexColor("#555555"))
        pdf.rect(x, panel_bottom, width, panel_top - panel_bottom, fill=0, stroke=1)

        pdf.setFont("Helvetica", 10)
        for index, (category, value) in enumerate(zip(categories, values)):
            y = top - 28 - index * 24
            pdf.setFillColor(colors.HexColor("#aaaaaa"))
            pdf.drawString(x, y, category)
            pdf.setFillColor(self._value_color(value))
            pdf.drawRightString(x + width - 12, y, self._value_text(value))

    def _draw_equity_curve(self, pdf, x, y, width, height, equity_visualizer):
        """Draw the equity curve and its reference lines onto the PDF."""
        left_margin = 54
        bottom_margin = 28
        plot_x = x + left_margin
        plot_y = y + bottom_margin
        plot_width = width - left_margin
        plot_height = height - bottom_margin

        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(x, y + height + 18, "Equity Curve")
        pdf.setStrokeColor(colors.HexColor("#555555"))
        pdf.rect(plot_x, plot_y, plot_width, plot_height, fill=0, stroke=1)

        trace = equity_visualizer.get_traces()
        shapes = equity_visualizer.get_shapes()
        timestamps = list(trace.x)
        values = [float(value) for value in trace.y]
        if not values:
            pdf.setFont("Helvetica", 10)
            pdf.setFillColor(colors.HexColor("#aaaaaa"))
            pdf.drawCentredString(plot_x + plot_width / 2, plot_y + plot_height / 2, "No equity data")
            return

        minimum, maximum = min(values), max(values)
        shape_values = [
            float(shape["y0"])
            for shape in shapes
            if shape.get("type") == "line" and shape.get("yref") == "y"
        ]
        if shape_values:
            minimum = min(minimum, *shape_values)
            maximum = max(maximum, *shape_values)
        value_range = maximum - minimum or 1
        start_time = timestamps[0]
        end_time = timestamps[-1]
        time_range = (end_time - start_time).total_seconds() or 1

        pdf.setFont("Helvetica", 8)
        pdf.setStrokeColor(colors.HexColor("#333333"))
        pdf.setFillColor(colors.HexColor("#aaaaaa"))
        for tick_index in range(5):
            ratio = tick_index / 4
            tick_value = minimum + value_range * ratio
            tick_y = plot_y + plot_height * ratio
            pdf.line(plot_x, tick_y, plot_x + plot_width, tick_y)
            pdf.drawRightString(plot_x - 6, tick_y - 3, f"{tick_value:,.2f}")

        for tick_index in range(4):
            ratio = tick_index / 3
            tick_time = start_time + (end_time - start_time) * ratio
            tick_x = plot_x + plot_width * ratio
            pdf.line(tick_x, plot_y, tick_x, plot_y + plot_height)
            pdf.drawCentredString(tick_x, plot_y - 16, tick_time.strftime("%H:%M:%S"))

        pdf.setFillColor(colors.HexColor("#aaaaaa"))
        pdf.drawCentredString(plot_x + plot_width / 2, y + 4, "Time")
        pdf.saveState()
        pdf.translate(x + 12, plot_y + plot_height / 2)
        pdf.rotate(90)
        pdf.drawCentredString(0, 0, "Balance")
        pdf.restoreState()

        points = [
            (
                plot_x + (timestamp - start_time).total_seconds() / time_range * plot_width,
                plot_y + (value - minimum) / value_range * plot_height
            )
            for timestamp, value in zip(timestamps, values)
        ]

        path = pdf.beginPath()
        path.moveTo(*points[0])
        for point in points[1:]:
            path.lineTo(*point)
        pdf.setStrokeColor(colors.toColor(trace.line.color))
        pdf.setLineWidth(trace.line.width)
        pdf.drawPath(path, stroke=1, fill=0)

        for shape in shapes:
            if shape.get("type") != "line" or shape.get("yref") != "y":
                continue

            line = shape.get("line", {})
            line_color = line.get("color", "#ffffff")
            if line_color.startswith("rgba"):
                line_color = colors.HexColor("#ffffff" if "255,255,255" in line_color else "#ff4100")
            else:
                line_color = colors.HexColor(line_color)

            line_y = plot_y + (float(shape["y0"]) - minimum) / value_range * plot_height
            pdf.setStrokeColor(line_color)
            pdf.setLineWidth(line.get("width", 1))
            pdf.setDash(1, 2) if line.get("dash") == "dot" else pdf.setDash()
            pdf.line(plot_x, line_y, plot_x + plot_width, line_y)
            pdf.setDash()

    @staticmethod
    def _value_text(value):
        """Extract the display text from a report value."""
        return str(getattr(value, "children", value))

    @staticmethod
    def _value_color(value):
        """Return the display color defined by the value style."""
        style = getattr(value, "style", {})
        return colors.HexColor(style.get("color", "#ffffff"))