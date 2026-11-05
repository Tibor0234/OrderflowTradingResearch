from io import BytesIO
import re
from zipfile import ZipFile

import pytest
from pypdf import PdfReader
from reportlab.pdfgen import canvas

from report_generator.report_zip_exporter import ReportZipExporter


def _write_pdf(path, *page_texts):
    pdf = canvas.Canvas(str(path))
    for text in page_texts:
        pdf.drawString(40, 800, text)
        pdf.showPage()
    pdf.save()


def _pdf_page_texts(pdf_bytes):
    return [
        page.extract_text().strip()
        for page in PdfReader(BytesIO(pdf_bytes)).pages
    ]


def test_report_zip_exporter_merges_reports_in_required_order(tmp_path):
    _write_pdf(tmp_path / "cumulative-full_run.pdf", "Full run")
    _write_pdf(tmp_path / "cumulative-symbol-ZZZ.pdf", "Symbol Z")
    _write_pdf(tmp_path / "cumulative-symbol-AAA.pdf", "Symbol A")
    _write_pdf(tmp_path / "session_pair_based-10.pdf", "Session pair 10")
    _write_pdf(tmp_path / "session_pair_based-2.pdf", "Session pair 2")
    (tmp_path / "trades.xlsx").write_bytes(b"workbook bytes")

    exporter = ReportZipExporter(tmp_path, "TestStrategy")
    archive_bytes = exporter.create_zip()

    assert re.fullmatch(
        r"TestStrategy-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.zip",
        exporter.filename,
    )
    with ZipFile(BytesIO(archive_bytes)) as archive:
        assert set(archive.namelist()) == {
            "cumulative.pdf",
            "session-pair-based.pdf",
            "trades.xlsx",
        }
        assert _pdf_page_texts(archive.read("cumulative.pdf")) == [
            "Full run",
            "Symbol A",
            "Symbol Z",
        ]
        assert _pdf_page_texts(archive.read("session-pair-based.pdf")) == [
            "Session pair 2",
            "Session pair 10",
        ]
        assert archive.read("trades.xlsx") == b"workbook bytes"


def test_report_zip_exporter_fails_when_required_reports_are_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="No report files found"):
        ReportZipExporter(tmp_path, "TestStrategy").create_zip()


def test_report_zip_exporter_includes_only_available_report_types(tmp_path):
    _write_pdf(tmp_path / "cumulative-symbol-BTCUSDT.pdf", "Symbol BTC")
    _write_pdf(tmp_path / "session_pair_based-2.pdf", "Session pair 2")

    archive_bytes = ReportZipExporter(tmp_path, "TestStrategy").create_zip()

    with ZipFile(BytesIO(archive_bytes)) as archive:
        assert set(archive.namelist()) == {
            "cumulative.pdf",
            "session-pair-based.pdf",
        }
        assert _pdf_page_texts(archive.read("cumulative.pdf")) == ["Symbol BTC"]
        assert _pdf_page_texts(archive.read("session-pair-based.pdf")) == [
            "Session pair 2",
        ]
