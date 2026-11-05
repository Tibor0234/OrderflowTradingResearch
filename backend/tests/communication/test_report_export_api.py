import asyncio

import aiohttp

from communication.api import ReportExportApi
from communication.server import CommunicationServer


class StubReportZipExporter:
    filename = "TestStrategy-2026-11-03T22-45-46.zip"

    def create_zip(self):
        return b"zip archive bytes"


class MissingReportsZipExporter(StubReportZipExporter):
    def create_zip(self):
        raise FileNotFoundError("missing report")


def test_report_export_api_returns_zip_download():
    server = CommunicationServer(port=0)
    server.register(ReportExportApi(StubReportZipExporter()))
    server.start()

    async def download():
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{server.host}:{server.port}/api/export",
                headers={"Origin": "http://localhost:3000"},
            ) as response:
                assert response.status == 200
                assert response.headers["Content-Type"] == "application/zip"
                assert response.headers["Content-Disposition"] == (
                    'attachment; filename="TestStrategy-2026-11-03T22-45-46.zip"'
                )
                assert response.headers["Access-Control-Allow-Origin"] == (
                    "http://localhost:3000"
                )
                assert response.headers["Access-Control-Expose-Headers"] == (
                    "Content-Disposition"
                )
                assert await response.read() == b"zip archive bytes"

    try:
        asyncio.run(download())
    finally:
        server.stop()


def test_report_export_api_returns_conflict_when_reports_are_not_ready():
    server = CommunicationServer(port=0)
    server.register(ReportExportApi(MissingReportsZipExporter()))
    server.start()

    async def request_export():
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"http://{server.host}:{server.port}/api/export"
            ) as response:
                assert response.status == 409
                assert await response.json() == {
                    "error": "Report files are not ready for export",
                }

    try:
        asyncio.run(request_export())
    finally:
        server.stop()


def test_report_export_api_allows_localhost_preflight():
    server = CommunicationServer(port=0)
    server.register(ReportExportApi(StubReportZipExporter()))
    server.start()

    async def preflight():
        async with aiohttp.ClientSession() as session:
            async with session.options(
                f"http://{server.host}:{server.port}/api/export",
                headers={"Origin": "http://localhost:3000"},
            ) as response:
                assert response.status == 204
                assert response.headers["Access-Control-Allow-Methods"] == (
                    "GET, OPTIONS"
                )

    try:
        asyncio.run(preflight())
    finally:
        server.stop()
