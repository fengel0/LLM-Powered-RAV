from contextlib import asynccontextmanager
from deployment_base.enviroment.api_env import PATH_PREFIX, SETTINGS, WORKERS, PORT
from core.config_loader import ConfigLoaderImplementation
from fastapi import FastAPI
import uvicorn

from simple_rag_api.api.rag_api import RAGApi
from simple_rag_api.application_startup import RAGAPIApplication


from simple_rag_api.settings import API_VERSION


@asynccontextmanager
async def lifespan(app: FastAPI):
    await RAGAPIApplication.Instance().astart()
    await RAGAPIApplication.Instance().create_usecase()
    yield
    await RAGAPIApplication.Instance().ashutdown()
    RAGAPIApplication.Instance().shutdown()


if __name__ == "__main__":
    config_loader = ConfigLoaderImplementation.create()
    result = config_loader.load_values(SETTINGS)
    if result.is_error():
        raise result.get_error()
    RAGAPIApplication.create(ConfigLoaderImplementation.Instance())
    RAGAPIApplication.Instance().start()

    app = RAGApi(
        title=RAGAPIApplication.Instance().get_application_name(),
        version=API_VERSION,
        lifespan=lifespan,
        root_path=config_loader.get_str(PATH_PREFIX),
    ).get_app()

    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=config_loader.get_int(PORT),
        reload=False,
        workers=config_loader.get_int(WORKERS),
    )
