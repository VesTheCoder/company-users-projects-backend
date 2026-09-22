from time import perf_counter

import structlog


class ObservabilityMiddleware:
    def __init__(self, app, settings, metrics):
        self.app = app
        self.settings = settings
        self.metrics = metrics

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        structlog.contextvars.clear_contextvars()
        request_id = scope.get("state", {}).get("request_id", "")
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=request_id,
            service="company-api",
            environment=self.settings.app_env,
        )
        started, status = perf_counter(), 500

        async def observed_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, observed_send)
        finally:
            route = getattr(scope.get("route"), "path", "unmatched")
            method = (
                scope["method"]
                if scope["method"]
                in {"GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS", "HEAD"}
                else "OTHER"
            )
            duration = perf_counter() - started
            labels = (route, method, f"{status // 100}xx")
            self.metrics.requests.labels(*labels).inc()
            self.metrics.latency.labels(*labels).observe(duration)
            structlog.get_logger().info(
                "http.request",
                route=route,
                method=method,
                status_code=status,
                duration_ms=round(duration * 1000, 2),
            )
            structlog.contextvars.clear_contextvars()
