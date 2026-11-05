import asyncio
import logging

from aiohttp import web

from communication.api.cors import cors_headers, cors_preflight_response
from report_generator.report_zip_exporter import ReportZipExporter

logger = logging.getLogger(__name__)


class ReportExportApi:
    """Serve the generated report archive to browser clients."""

    def __init__(self, report_zip_exporter: ReportZipExporter):
        self.report_zip_exporter = report_zip_exporter

    def register_routes(self, app: web.Application) -> None:
        app.router.add_get("/api/export", self.handle_export)
        app.router.add_options("/api/export", self.handle_export_preflight)

    async def handle_export_preflight(self, request: web.Request) -> web.Response:
        return cors_preflight_response(request, "GET, OPTIONS")

    async def handle_export(self, request: web.Request) -> web.Response:
        headers = cors_headers(request)
        try:
            archive = await asyncio.to_thread(
                self.report_zip_exporter.create_zip
            )
        except FileNotFoundError as error:
            logger.warning("Report archive is not ready: %s", error)
            return web.json_response(
                {"error": "Report files are not ready for export"},
                status=409,
                headers=headers,
            )
        except Exception:
            logger.exception("Failed to create report archive")
            return web.json_response(
                {"error": "Failed to create report archive"},
                status=500,
                headers=headers,
            )

        headers.update({
            "Content-Type": "application/zip",
            "Content-Disposition": (
                f'attachment; filename="{self.report_zip_exporter.filename}"'
            ),
        })
        if "Access-Control-Allow-Origin" in headers:
            headers["Access-Control-Expose-Headers"] = "Content-Disposition"
        return web.Response(body=archive, headers=headers)
