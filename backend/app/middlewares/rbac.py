import uuid

from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求注入 request_id，便于日志链路追踪。JWT 校验放在依赖中完成。"""

    async def dispatch(self, request, call_next):
        request.state.request_id = uuid.uuid4().hex[:16]
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response
