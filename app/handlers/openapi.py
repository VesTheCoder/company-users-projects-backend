from fastapi.openapi.utils import get_openapi

from app.handlers.errors import ProblemDetail


def install_openapi(app, settings):
    def schema():
        if app.openapi_schema is not None:
            return app.openapi_schema
        document = get_openapi(title=app.title, version=app.version, routes=app.routes)
        document.setdefault("components", {}).setdefault("schemas", {})[
            "ProblemDetail"
        ] = ProblemDetail.model_json_schema()
        document["components"]["securitySchemes"] = {
            "SessionCookie": {
                "type": "apiKey",
                "in": "cookie",
                "name": settings.cookie_name,
            }
        }
        for path, methods in document["paths"].items():
            if not path.startswith("/api/"):
                continue
            for method, operation in methods.items():
                login = path.endswith("/auth/login")
                if not login:
                    operation["security"] = [{"SessionCookie": []}]
                if method in {"post", "put", "patch", "delete"}:
                    header = "X-CSRF-Protection" if login else "X-CSRF-Token"
                    operation.setdefault("parameters", []).extend(
                        [
                            {
                                "name": header,
                                "in": "header",
                                "required": True,
                                "schema": {"type": "string"},
                                "description": "1 for login; CSRF token otherwise.",
                            },
                            {
                                "name": "Origin",
                                "in": "header",
                                "required": False,
                                "schema": {"type": "string"},
                                "description": "Trusted Origin or Referer is required.",
                            },
                        ]
                    )
                for status in [400, 401, 403, 404, 409, 412, 413, 422, 428, 429, 503]:
                    operation["responses"][str(status)] = {
                        "description": "Problem Details error",
                        "content": {
                            "application/problem+json": {
                                "schema": {"$ref": "#/components/schemas/ProblemDetail"}
                            }
                        },
                    }
        app.openapi_schema = document
        return document

    app.openapi = schema
