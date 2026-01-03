import logging
import os
import time
import json
import threading
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi_core.base_api import BaseAPI, Lifespan
from starlette.responses import HTMLResponse, StreamingResponse, JSONResponse
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import Request, HTTPException
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
)
from simple_rag_api.settings import LLMS_AVAILABALE

logger = logging.getLogger(__name__)


# --------------------------- In-memory Context Store ----------------------------


class ContextStore:
    """
    A simple bounded, thread-safe in-memory store with optional TTL.
    Stores: context_id -> {"created": int, "data": Any}
    """

    def __init__(self, max_items: int = 1000, ttl_seconds: Optional[int] = 24 * 3600):
        self._data: Dict[str, Dict[str, Any]] = {}
        self._order: List[str] = []
        self._lock = threading.Lock()
        self._max = max_items
        self._ttl = ttl_seconds

    def put(self, context_id: str, data: Any) -> None:
        now = int(time.time())
        with self._lock:
            # Evict expired
            self._evict_expired(now)
            # Evict for capacity
            if len(self._order) >= self._max:
                oldest = self._order.pop(0)
                self._data.pop(oldest, None)
            # Insert / update
            self._data[context_id] = {"created": now, "data": data}
            if context_id not in self._order:
                self._order.append(context_id)

    def get(self, context_id: str) -> Optional[Any]:
        now = int(time.time())
        with self._lock:
            self._evict_expired(now)
            item = self._data.get(context_id)
            return item["data"] if item else None

    def _evict_expired(self, now: int) -> None:
        if self._ttl is None:
            return
        expired: List[str] = []
        for cid, item in self._data.items():
            if now - item["created"] > self._ttl:
                expired.append(cid)
        for cid in expired:
            self._data.pop(cid, None)
            if cid in self._order:
                self._order.remove(cid)
