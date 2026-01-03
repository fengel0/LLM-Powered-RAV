from contextlib import asynccontextmanager
from core.config_loader import ConfigLoaderImplementation
from fastapi import FastAPI
import uvicorn

from file_converter_api.application_startup import FileConverterAPIApplication
from deployment_base.enviroment.api_env import WORKERS, PORT, SETTINGS


from file_converter_api.api.file_api import FileConverterApi
from file_converter_api.settings import API_VERSION


@asynccontextmanager
async def lifespan(app: FastAPI):
    await FileConverterAPIApplication.Instance().astart()
    await FileConverterAPIApplication.Instance().create_usecase()

    yield
    await FileConverterAPIApplication.Instance().ashutdown()
    FileConverterAPIApplication.Instance().shutdown()


if __name__ == "__main__":
    FileConverterAPIApplication.create(
        config_loader=ConfigLoaderImplementation.create()
    )
    FileConverterAPIApplication.Instance().start()
    config_loader = ConfigLoaderImplementation.Instance()
    config_loader.load_values(SETTINGS)

    app = FileConverterApi(
        title=FileConverterAPIApplication.Instance().get_application_name(),
        version=API_VERSION,
        lifespan=lifespan,
    ).get_app()

    uvicorn.run(
        app=app,
        host="0.0.0.0",
        port=config_loader.get_int(PORT),
        reload=False,
        workers=config_loader.get_int(WORKERS),
    )
