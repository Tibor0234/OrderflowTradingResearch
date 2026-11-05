from urllib.parse import urlsplit

from aiohttp import web


def cors_headers(request: web.Request) -> dict[str, str]:
    origin = request.headers.get("Origin")
    if origin is None:
        return {}

    parsed_origin = urlsplit(origin)
    if (
        parsed_origin.scheme not in {"http", "https"}
        or parsed_origin.hostname not in {"localhost", "127.0.0.1", "::1"}
    ):
        return {}

    return {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}


def cors_preflight_response(
    request: web.Request,
    allowed_methods: str,
) -> web.Response:
    headers = cors_headers(request)
    if "Access-Control-Allow-Origin" not in headers:
        return web.Response(status=403)

    headers.update({
        "Access-Control-Allow-Methods": allowed_methods,
        "Access-Control-Allow-Headers": "Content-Type",
    })
    return web.Response(status=204, headers=headers)
