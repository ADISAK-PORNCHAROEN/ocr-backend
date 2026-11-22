from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class UploadBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or scope["path"] != "/api/v1/ocr/jobs"
        ):
            await self.app(scope, receive, send)
            return

        content_length = self._content_length(scope)
        if content_length is not None and content_length > self.max_body_bytes:
            response = JSONResponse(
                status_code=413,
                content={
                    "error": {
                        "code": "FILE_TOO_LARGE",
                        "message": "ขนาด request เกินขีดจำกัด",
                        "retryable": False,
                    }
                },
            )
            await response(scope, receive, send)
            return

        received_bytes = 0

        async def limited_receive() -> Message:
            nonlocal received_bytes
            message = await receive()
            if message["type"] == "http.request":
                received_bytes += len(message.get("body", b""))
                if received_bytes > self.max_body_bytes:
                    raise StarletteHTTPException(status_code=413, detail="Request body too large")
            return message

        await self.app(scope, limited_receive, send)

    @staticmethod
    def _content_length(scope: Scope) -> int | None:
        for name, value in scope.get("headers", []):
            if name.lower() == b"content-length":
                try:
                    return int(value)
                except ValueError:
                    return None
        return None
