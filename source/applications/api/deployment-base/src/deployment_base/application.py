from abc import ABC, abstractmethod
from core.logger import disable_local_logging
from opentelemetry import trace
from typing import Protocol, TypeVar, runtime_checkable
from core.singelton import SingletonMeta
import threading

from core.config_loader import ConfigLoader

import logging

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="Application")


@runtime_checkable
class SyncLifetimeReg(Protocol):
    def start(self, config_loader: ConfigLoader): ...
    def shutdown(self): ...


@runtime_checkable
class AsyncLifetimeReg(Protocol):
    async def start(self, config_loader: ConfigLoader): ...
    async def shutdown(self): ...


class Application(ABC):


    """
    Application base class
    allows to start in application in multiple steps
    """

    _instances: dict[type, "Application"] = {}
    _lock = threading.Lock()
    tracer = trace.get_tracer("ApplicationStartup")

    def __new__(cls, config_loader: ConfigLoader):
        # per-subclass singleton
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__new__(cls)
        return cls._instances[cls]

    def __init__(self, config_loader: ConfigLoader) -> None:
        # safe to run multiple times; same singleton instance
        self._sync_componentes: list[SyncLifetimeReg] = []
        self._async_componentes: list[AsyncLifetimeReg] = []
        self._config_loader = config_loader

    def _with_component(self, component: SyncLifetimeReg) -> "Application":
        self._sync_componentes.append(component)
        return self

    def _with_acomponent(self, component: AsyncLifetimeReg) -> "Application":
        self._async_componentes.append(component)
        return self

    async def create_usecase(self):
        logger.info("create Usecase")
        await self._create_usecase()
        self._config_loader.log_loaded_values(False)

    @abstractmethod
    def _add_components(self): ...
    @abstractmethod
    async def _create_usecase(self): ...

    @classmethod
    def create(cls: type[T], config_loader: ConfigLoader) -> T:
        # returns the subclass instance when called on a subclass
        return cls(config_loader=config_loader)

    @classmethod
    def Instance(cls: type[T]) -> T:
        # returns the subclass instance when called on a subclass
        assert cls in cls._instances, (
            f"{cls.__name__} not initialized — call create() first"
        )
        return cls._instances[cls]

    def start(self):
        self._add_components()  # will call subclass implementation now
        logger.debug(f"start {len(self._sync_componentes)} sync components")
        with self.tracer.start_as_current_span("sync startup"):
            for component in self._sync_componentes:
                logger.debug(f"start {component.__class__}")
                component.start(self._config_loader)

    def shutdown(self):
        with self.tracer.start_as_current_span("sync shutdown"):
            for component in self._sync_componentes:
                logger.debug(f"start {component.__class__}")
                component.shutdown()
            SingletonMeta.clear_all()
            disable_local_logging()

    async def astart(self):
        with self.tracer.start_as_current_span("async startup"):
            for component in self._async_componentes:
                await component.start(self._config_loader)

    async def ashutdown(self):
        logger.debug(f"start {len(self._async_componentes)} sync components")
        with self.tracer.start_as_current_span("async shutdown"):
            for component in self._async_componentes:
                await component.shutdown()
