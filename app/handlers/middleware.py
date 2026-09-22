from uuid import UUID, uuid4

from starlette.requests import Request

from app.handlers.errors import problem_response


class TransportMiddleware:
    def __init__(self, app, trusted_hosts: list[str]):
        self.app = app
        self.trusted_hosts = trusted_hosts

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request = Request(scope, receive)
        incoming = request.headers.get("x-request-id", "")
        try:
            request_id = str(UUID(incoming))
            if incoming != request_id:
                raise ValueError
        except ValueError:
            request_id = str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        async def send_with_id(message):
            if message["type"] == "http.response.start":
                message["headers"] = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key != b"x-request-id"
                ]
                message.setdefault("headers", []).append(
                    (b"x-request-id", request_id.encode())
                )
            await send(message)

        if request.url.hostname not in self.trusted_hosts:
            response = problem_response(
                request, 400, "invalid_host", "Invalid host header."
            )
            return await response(scope, receive, send_with_id)
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > 65536:
                response = problem_response(
                    request, 413, "body_too_large", "Request body exceeds 64 KiB."
                )
                return await response(scope, receive, send_with_id)
            chunks.append(message)
            if not message.get("more_body", False):
                break

        async def buffered_receive():
            return chunks.pop(0) if chunks else await receive()

        await self.app(scope, buffered_receive, send_with_id)
