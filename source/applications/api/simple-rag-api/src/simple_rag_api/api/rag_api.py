from datetime import date, datetime
import logging
import os
import json
import time
from typing import Any
from uuid import uuid4

from core.hash import compute_mdhash_id
from core.model import NotFoundException
from domain.database.config.model import RAGConfigTypeE
from fastapi_core.base_api import BaseAPI, JSONResponse, Lifespan
from pydantic import BaseModel
from starlette.responses import HTMLResponse, StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException, Request
from fastapi.templating import Jinja2Templates

from core.config_loader import ConfigLoaderImplementation
from domain.rag.model import Conversation, Message, RoleType
from simple_rag_service.usecase.rag import SimpleRAGUsecase

from simple_rag_api.api.model import (
    ChatChoice,
    ChatChoiceChunk,
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    DeltaMessage,
    ModelData,
    ModelList,
    QueryRequest,
    QueryResposne,
)
from simple_rag_api.api.search_engine import search
from simple_rag_api.application_startup import RAGAPIApplication
from simple_rag_api.settings import (
    DEFAULT_CONFIG,
    DEFAULT_PROJECT,
    LLMS_AVAILABALE,
    RUNNING_HOST,
)
from deployment_base.enviroment.api_env import PATH_PREFIX

logger = logging.getLogger(__name__)


class AnswerContextDump(BaseModel):
    messages: list[ChatMessage]
    context: list[str]
    answer: str


class RAGApi(BaseAPI):
    def __init__(
        self, title: str, version: str, lifespan: Lifespan, root_path: str = ""
    ):
        super().__init__(title, version, lifespan=lifespan, root_path=root_path)

        # --- STATIC & TEMPLATES -------------------------------------------------
        static_dir = os.path.join(os.getcwd(), "static")
        self.app.mount("/static", StaticFiles(directory=static_dir), name="static")
        self.templates = Jinja2Templates(directory=static_dir)  # index.html lives here

        # --- CORS (optional but recommended if UI may be served from elsewhere) --
        raw_origins = os.getenv("CORS_ORIGINS", "*")
        origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins if origins != ["*"] else ["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _register_api_paths(self):
        @self.app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            base_url = str(request.base_url).rstrip("/")
            if ConfigLoaderImplementation.Instance().get_str(RUNNING_HOST):
                api_hosts = [
                    f"{ConfigLoaderImplementation.Instance().get_str(RUNNING_HOST)}{ConfigLoaderImplementation.Instance().get_str(PATH_PREFIX)}/v1",
                    f"{base_url}/v1",
                ]
            else:
                api_hosts = [f"{base_url}/v1"]

            configs_result = await RAGAPIApplication.Instance().get_all_config()
            if configs_result.is_error():
                raise configs_result.get_error()
            projects_result = await RAGAPIApplication.Instance().get_all_project_names()
            if projects_result.is_error():
                raise projects_result.get_error()

            configs = configs_result.get_ok()
            projects = projects_result.get_ok()

            return self.templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "APIHosts": api_hosts,
                    "configs": configs,
                    "projects": projects,
                    "root_path": self.root_path,
                },
            )

        @self.app.get("/search", response_class=HTMLResponse)
        async def search_side(request: Request):
            base_url = str(request.base_url).rstrip("/")
            if ConfigLoaderImplementation.Instance().get_str(RUNNING_HOST):
                api_hosts = [
                    f"{ConfigLoaderImplementation.Instance().get_str(RUNNING_HOST)}{ConfigLoaderImplementation.Instance().get_str(PATH_PREFIX)}/v1",
                    f"{base_url}/v1",
                ]
            else:
                api_hosts = [f"{base_url}/v1"]

            configs_result = await RAGAPIApplication.Instance().get_all_config(
                RAGConfigTypeE.HYBRID
            )
            if configs_result.is_error():
                raise configs_result.get_error()
            projects_result = await RAGAPIApplication.Instance().get_all_project_names()
            if projects_result.is_error():
                raise projects_result.get_error()

            configs = configs_result.get_ok()
            projects = projects_result.get_ok()

            return self.templates.TemplateResponse(
                "search.html",
                {
                    "request": request,
                    "APIHosts": api_hosts,
                    "configs": [c for c in configs if c],
                    "projects": projects,
                    "root_path": self.root_path,
                },
            )

        # ------------------ OpenAI-compatible endpoints -------------------------
        @self.app.post(
            "/v1/chat/completions",
            tags=["OpenAI-compatible"],
            summary="OpenAI-compatible chat completion endpoint using custom RAG backend",
        )
        async def chat_completions(request: ChatCompletionRequest):  # type: ignore
            config_loader = ConfigLoaderImplementation.Instance()

            chat_id = f"chatcmpl-{uuid4()}"
            context_id = f"ctx-{uuid4()}"
            created = int(time.time())

            config_id = request.config_id or config_loader.get_str(DEFAULT_CONFIG)
            project_id = request.project_id or config_loader.get_str(DEFAULT_PROJECT)

            config_result = await RAGAPIApplication.Instance().get_config_by_id(
                config_id
            )

            project_result = await RAGAPIApplication.Instance().get_project(project_id)

            if config_result.is_error():
                raise config_result.get_error()
            if project_result.is_error():
                raise project_result.get_error()

            project = project_result.get_ok()
            config = config_result.get_ok()

            if project is None:
                raise NotFoundException(f"Project {project_id} not found")
            if config is None:
                raise NotFoundException(f"Config {config_id} not found")

            query_dump = AnswerContextDump(
                messages=request.messages, context=[], answer=""
            )

            async def stream_generator():
                """
                Streams tokens as SSE. Before token stream, sends a named event 'context'
                with the generated context_id. Once nodes are available, stores them
                in CONTEXT_STORE under context_id.
                """
                # Let the frontend know the context_id immediately
                yield f"event: context\ndata: {json.dumps({'context_id': context_id})}\n\n"

                # Run the RAG request and stream tokens
                rag_llm = RAGAPIApplication.Instance().get_llm_based_on_config_type(
                    config
                )

                response_result = await SimpleRAGUsecase(rag_llm=rag_llm).request(
                    conversation=Conversation(
                        messages=[
                            Message(
                                message=chat_message.content,
                                role=RoleType(chat_message.role),
                            )
                            for chat_message in request.messages
                        ],
                        model=request.model,
                    ),
                    metadata_filters=None,
                    collection=f"{project_id}-{config.embedding.id}",
                )

                if response_result.is_error():
                    # Send an error event to the client before raising
                    err = str(response_result.get_error())
                    yield f"event: error\ndata: {json.dumps({'message': err})}\n\n"
                    raise response_result.get_error()

                index = 0

                response = response_result.get_ok()
                nodes = getattr(response, "nodes", None)

                query_dump.context = [
                    n.model_dump_json(indent=2) for n in response.nodes
                ]
                # Store a light projection of nodes for retrieval via /v1/contexts/{id}
                try:
                    projected = _project_nodes(nodes)
                    RAGAPIApplication.Instance().store_context(
                        context_id=context_id, context=projected
                    )
                except Exception as e:
                    logger.exception("Failed to project/store nodes: %s", e)
                    # Still continue streaming tokens

                assert response.generator
                async for token in response.generator:
                    query_dump.answer = f"{query_dump.answer}{token}"
                    first_chunk = ChatCompletionChunk(
                        id=chat_id,
                        created=created,
                        model=request.model,
                        choices=[
                            ChatChoiceChunk(
                                index=index,
                                delta=DeltaMessage(
                                    role=RoleType.Assistent.value,
                                    content=token,
                                ),
                                finish_reason=None,
                                nodes=None,
                            )
                        ],
                    )
                    index += 1
                    yield f"data: {first_chunk.model_dump_json()}\n\n"
                yield "data: [DONE]\n\n"
                model_dump_str = query_dump.model_dump_json(indent=2)
                hash = compute_mdhash_id(model_dump_str)
                timestemp = datetime.now().strftime("%Y%m%d-%H%M%S")
                with open(f"./chat_dump/{timestemp}-{config_id}-{hash}", "w") as f:
                    f.write(model_dump_str)

            # --- Streaming response
            if request.stream:
                return StreamingResponse(
                    stream_generator(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no",
                        # Expose the context id via header as well:
                        "X-Context-Id": context_id,
                        # Helpful when the UI is on a different origin:
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization",
                        # Expose the custom header to browsers
                        "Access-Control-Expose-Headers": "X-Context-Id",
                    },
                )

            full_response = (
                "Das ist eine RAG-basierte Antwort auf Ihre Anfrage. "
                "Die Informationen wurden aus der Wissensbasis abgerufen."
            )
            payload = ChatCompletionResponse(
                id=chat_id,
                object="chat.completion",
                created=created,
                model=request.model,
                choices=[
                    ChatChoice(
                        index=0,
                        message=ChatMessage(role="assistant", content=full_response),
                        finish_reason="stop",
                    )
                ],
            )
            # Return as JSONResponse so we can attach headers
            return JSONResponse(
                status_code=200,
                content=payload.model_dump(),
                headers={
                    "X-Context-Id": context_id,
                    "Access-Control-Expose-Headers": "X-Context-Id",
                },
            )

        # ---------------------- Context retrieval endpoint -----------------------
        @self.app.get(
            "/v1/contexts/{context_id}",
            tags=["OpenAI-compatible"],
            summary="Get the retrieved context for a prior chat completion",
        )
        async def get_context(context_id: str):
            data = RAGAPIApplication.Instance().get_context(context_id)
            if data is None:
                raise HTTPException(
                    status_code=404, detail="Context not found or expired"
                )
            return {"context_id": context_id, "data": data}

        @self.app.get(
            "/v1/models", response_model=ModelList, tags=["OpenAI-compatible"]
        )
        async def list_models():  # type: ignore
            llms = ConfigLoaderImplementation.Instance().get_str(LLMS_AVAILABALE)
            llms_list = [llm.strip() for llm in llms.split(",") if llm.strip()]
            return ModelList(
                data=[
                    ModelData(
                        id=llm,
                        name=llm,
                        created=int(time.time()),
                        owned_by="custom-rag",
                    )
                    for llm in llms_list
                ]
            )

        @self.app.post(
            "/v1/query",
            tags=["OpenAI-compatible"],
            summary="Query api",
        )
        async def query(request: QueryRequest):  # type: ignore
            config_loader = ConfigLoaderImplementation.Instance()

            config_id = request.config_id or config_loader.get_str(DEFAULT_CONFIG)
            project_id = request.project_id or config_loader.get_str(DEFAULT_PROJECT)

            config_result = await RAGAPIApplication.Instance().get_config_by_id(
                config_id
            )

            project_result = await RAGAPIApplication.Instance().get_project(project_id)

            if config_result.is_error():
                raise config_result.get_error()
            if project_result.is_error():
                raise project_result.get_error()

            project = project_result.get_ok()
            config = config_result.get_ok()

            if project is None:
                raise NotFoundException(f"Project {project_id} not found")
            if config is None:
                raise NotFoundException(f"Config {config_id} not found")
            result = await search(
                query=request.query,
                collection=f"{project_id}-{config.embedding.id}",
                rag_config=config,
                config_loader=ConfigLoaderImplementation.Instance(),
                enable_reranker=request.enable_reranker,
            )
            if result.is_error():
                raise result.get_error()

            nodes = result.get_ok()
            output = QueryResposne(nodes=nodes).model_dump()

            return JSONResponse(
                status_code=200,
                content=output,
            )


# ------------------------------ Helper: node projection ------------------------


def _project_nodes(nodes: Any) -> list[dict[str, Any]]:
    """
    Convert domain-specific nodes into a JSON-friendly list.
    Adjust this to match your actual node objects. The goal is to avoid
    storing large or unserializable objects and keep only what the UI needs.
    """
    out: list[dict[str, Any]] = []
    if not nodes:
        return out

    for n in nodes:
        # Best-effort extraction; change attribute names as needed
        node_id = getattr(n, "id", None) or getattr(n, "node_id", None)
        score = getattr(n, "score", None)
        metadata = getattr(n, "metadata", None) or {}
        text = getattr(n, "text", None) or getattr(n, "content", None)

        # If metadata is not dict-like, coerce to string
        if metadata is not None and not isinstance(metadata, dict):
            try:
                # some frameworks return pydantic models; try dict()
                metadata = dict(metadata)  # type: ignore
            except Exception:
                metadata = {"_repr": str(metadata)}

        out.append(
            {
                "id": node_id,
                "score": score,
                "metadata": metadata,
                "text": text,
            }
        )
    return out
