from io import BytesIO
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfWriter


class ReportZipExporter:
    """Build an in-memory archive containing the generated reports."""

    def __init__(self, report_directory: Path, strategy_name: str):
        self.report_directory = report_directory
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        self.filename = f"{strategy_name}-{timestamp}.zip"

    def create_zip(self) -> bytes:
        """Return the requested report files as a ZIP archive."""
        full_run_pdf = self.report_directory / "cumulative-full_run.pdf"
        trades_workbook = self.report_directory / "trades.xlsx"
        cumulative_pdfs = (
            [full_run_pdf] if full_run_pdf.is_file() else []
        )
        cumulative_pdfs.extend(
            sorted(
                (
                    path
                    for path in self.report_directory.glob("cumulative-symbol-*.pdf")
                    if path.is_file()
                ),
                key=lambda path: path.name,
            )
        )
        session_pair_pdfs = sorted(
            (
                path
                for path in self.report_directory.glob("session_pair_based-*.pdf")
                if path.is_file()
            ),
            key=lambda path: int(path.stem.rsplit("-", 1)[1]),
        )
        has_trades_workbook = trades_workbook.is_file()
        if not cumulative_pdfs and not session_pair_pdfs and not has_trades_workbook:
            raise FileNotFoundError(
                f"No report files found in {self.report_directory}"
            )

        zip_buffer = BytesIO()
        with ZipFile(zip_buffer, "w", compression=ZIP_DEFLATED) as archive:
            if cumulative_pdfs:
                archive.writestr(
                    "cumulative.pdf",
                    self._merge_pdfs(cumulative_pdfs),
                )
            if session_pair_pdfs:
                archive.writestr(
                    "session-pair-based.pdf",
                    self._merge_pdfs(session_pair_pdfs),
                )
            if has_trades_workbook:
                archive.write(trades_workbook, arcname="trades.xlsx")
        return zip_buffer.getvalue()

    @staticmethod
    def _merge_pdfs(pdf_paths: list[Path]) -> bytes:
        writer = PdfWriter()
        for pdf_path in pdf_paths:
            writer.append(pdf_path)

        merged_pdf = BytesIO()
        writer.write(merged_pdf)
        return merged_pdf.getvalue()
