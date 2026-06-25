from __future__ import annotations

import json
from html import escape
from typing import Final

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.openapi.docs import swagger_ui_default_parameters
from fastapi.responses import HTMLResponse

from src.shared.infrastructure.config.settings import APISettings

SWAGGER_UI_VERSION: Final = "5.32.6"
SWAGGER_UI_BASE_URL: Final = (
    f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}"
)
SWAGGER_UI_JS_URL: Final = f"{SWAGGER_UI_BASE_URL}/swagger-ui-bundle.js"
SWAGGER_UI_CSS_URL: Final = f"{SWAGGER_UI_BASE_URL}/swagger-ui.css"
SWAGGER_UI_JS_INTEGRITY: Final = (
    "sha384-EYdOaiRwn44zNjrw+Tfs06qYz9BGQVo2f4/pLY5i7VorbjnZNhdplAbTBk8FXHUJ"
)
SWAGGER_UI_CSS_INTEGRITY: Final = (
    "sha384-9Q2fpS+xeS4ffJy6CagnwoUl+4ldAYhOs9pgZuEKxypVModhmZFzeMlvVsAjf7uT"
)


def build_swagger_ui_html(
    *,
    openapi_url: str,
    title: str,
    oauth2_redirect_url: str,
) -> HTMLResponse:
    parameter_lines = [
        f"url: {json.dumps(openapi_url)},",
        *(
            f"{json.dumps(key)}: {json.dumps(jsonable_encoder(value))},"
            for key, value in swagger_ui_default_parameters.items()
        ),
        (
            "oauth2RedirectUrl: window.location.origin + "
            f"{json.dumps(oauth2_redirect_url)},"
        ),
    ]
    parameters = "\n".join(parameter_lines)
    content = f"""<!DOCTYPE html>
<html>
<head>
<link type="text/css" rel="stylesheet" href="{SWAGGER_UI_CSS_URL}"
 integrity="{SWAGGER_UI_CSS_INTEGRITY}" crossorigin="anonymous">
<title>{escape(title)}</title>
</head>
<body>
<div id="swagger-ui"></div>
<script src="{SWAGGER_UI_JS_URL}"
 integrity="{SWAGGER_UI_JS_INTEGRITY}" crossorigin="anonymous"></script>
<script>
const ui = SwaggerUIBundle({{
{parameters}
presets: [
  SwaggerUIBundle.presets.apis,
  SwaggerUIBundle.SwaggerUIStandalonePreset
],
}})
</script>
</body>
</html>
"""
    return HTMLResponse(content)


def add_docs_route(
    app: FastAPI,
    settings: APISettings,
) -> None:
    docs_url = settings.docs_url
    openapi_url = settings.openapi_url
    if not docs_url or not openapi_url:
        return

    @app.get(docs_url, include_in_schema=False)
    async def custom_swagger_ui_html() -> HTMLResponse:
        return build_swagger_ui_html(
            openapi_url=openapi_url,
            title=f"{app.title} - Swagger UI",
            oauth2_redirect_url=f"{docs_url}/oauth2-redirect",
        )
