from core.config_loader import ConfigLoaderImplementation
from fastapi import FastAPI
from contextlib import asynccontextmanager
import gradio as gr
import uvicorn
from deployment_base.enviroment.api_env import PORT, SETTINGS as API_SETTINGS

from graph_view.application_startup import GraphViewApplication
from graph_view.web_ui import get_web_ui


@asynccontextmanager
async def lifespan(app: FastAPI):
    GraphViewApplication.Instance().start()
    await GraphViewApplication.Instance().astart()
    await GraphViewApplication.Instance().create_usecase()
    yield
    await GraphViewApplication.Instance().ashutdown()
    GraphViewApplication.Instance().shutdown()


GraphViewApplication.create(ConfigLoaderImplementation.create())
config_loader = ConfigLoaderImplementation.Instance()
config_loader.load_values(API_SETTINGS)

fastapi_app = FastAPI(lifespan=lifespan)
demo = get_web_ui()
gradio_app = demo.queue()
fastapi_app = gr.mount_gradio_app(fastapi_app, gradio_app, path="")

if __name__ == "__main__":
    uvicorn.run(fastapi_app, host="0.0.0.0", port=config_loader.get_int(PORT))
