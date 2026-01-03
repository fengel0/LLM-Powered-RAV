from starlette.responses import JSONResponse
import uvicorn
from core.logger import init_logging, logging, OTELConfig


from fastapi_core.base_api import BaseAPI


class TestApi(BaseAPI):
    summary = """
        This API is in charge to convert abetrie files that have been uploaded to an S3 Bucket
    """

    def __init__(self, title: str, version: str):
        super().__init__(title, version)

    def _register_api_paths(self):
        @self.app.get("/test_endpoint", summary="Test endpoint")
        async def test_function() -> JSONResponse:
            return JSONResponse(content={"greeding": "hi my friend"})


if __name__ == "__main__":
    otel_config: OTELConfig | None = None
    otel_config = OTELConfig(
        title="MyNewWildApi",
        version="0.0.1",
        otel_host="127.0.0.1:4317",
        otel_metric_host="127.0.0.1:4317",
        otel_log_host="127.0.0.1:4317",
        insecure=True,
    )

    init_logging("DEBUG", otel_config)

    app = TestApi(title=otel_config.title, version=otel_config.version).get_app()

    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=1234,
        reload=False,
        workers=1,
    )
