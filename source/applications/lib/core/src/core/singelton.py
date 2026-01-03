from typing import Any, TypeVar, Type
import logging

T = TypeVar("T", bound="BaseSingleton")

logger = logging.getLogger(__name__)


class SingletonMeta(type):
    """
    Metaclass that guarantees a *single* instance per concrete class.

    How it works
    -------------
    * When a class that uses ``SingletonMeta`` is called, the metaclass checks an
      internal ``_instances`` dictionary.
    * If an instance for that class already exists it is returned; otherwise a
      new object is created, stored in ``_instances`` and then returned.
    * The dictionary lives on the metaclass itself, so every subclass automatically
      shares the same global registry.

    Public helpers
    ---------------
    * ``clear_all()`` – removes *all* stored instances.  If a stored instance
      implements a ``_reset`` method it is called first (allowing the object to
      clean up its own state) before the entry is deleted.

    Notes
    -----
    * ``SingletonMeta`` is **not** meant to be subclassed; it is used as the
      ``metaclass=`` argument of ``BaseSingleton`` (or any other class that
      wants singleton behaviour).
    * Thread‑safety is provided by the GIL for CPython; if you need true
      multi‑process safety you must add your own locking.
    """

    _instances: dict[type, Any] = {}

    def __call__(cls, *args, **kwargs) -> Any:  # type: ignore
        if cls not in cls._instances:  # type: ignore
            instance = super().__call__(*args, **kwargs)
            logger.debug(f"created {cls}")
            cls._instances[cls] = instance
        return cls._instances[cls]

    @classmethod
    def clear_all(cls):
        for instance in cls._instances.keys():
            if hasattr(instance, "_reset"):
                try:
                    logger.debug(f"deleted {cls}")
                except Exception:
                    pass  # don’t let one bad cleanup ruin the purge
        cls._instances.clear()


class BaseSingleton(metaclass=SingletonMeta):
    """
    Simple base class that supplies a clean, opinionated API on top of
    ``SingletonMeta``.

    Core responsibilities
    ---------------------
    * **One‑time initialization** – ``__init__`` forwards arguments to an
      ``_init_once`` hook **only on the first construction**.  Subsequent
      calls become no‑ops, guaranteeing that expensive setup code runs once.
    * **Reset/Restart** – subclasses can implement ``_reset`` to clear their own
      internal state; the ``restart`` class‑method uses this hook to destroy the
      existing instance and allow a fresh one to be created.
    * **Factory helpers** – ``create`` builds the singleton the first time it is
      called and raises if an instance already exists; ``Instance`` returns the
      already‑created object (or raises if it has not been created yet).

    Extending the class
    -------------------
    Subclasses **should not** override ``__init__``.  Instead they implement
    ``_init_once(self, *args, **kwargs)`` for all one‑time setup logic and,
    optionally, ``_reset(self, *args, **kwargs)`` to undo that logic when a
    restart is requested.

    Example
    -------
    >>> class Config(BaseSingleton):
    ...     def _init_once(self, path: str):
    ...         self.settings = json.load(open(path))
    ...
    >>> cfg = Config.create("config.json")   # creates the singleton
    >>> same_cfg = Config.Instance()        # retrieves the same object
    >>> Config.restart()                    # resets and removes the instance
    """

    _initialized = False

    def __init__(self, *args, **kwargs):  # type: ignore
        if self._initialized:
            return
        self._init_once(*args, **kwargs)  # type: ignore
        self._initialized = True

    def _init_once(self, *args, **kwargs):  # type: ignore
        """Subclasses override this instead of __init__."""
        pass

    def _reset(self, *args, **kwargs):  # type: ignore
        """Subclasses can override this to reset their state."""
        self._initialized = False

    @classmethod
    def create(cls: Type[T], *args, **kwargs) -> T:  # type: ignore
        if cls in SingletonMeta._instances:  # type: ignore
            raise RuntimeError(f"{cls.__name__} instance already created.")
        return cls(*args, **kwargs)  # type: ignore

    @classmethod
    def Instance(cls: Type[T]) -> T:
        if cls not in SingletonMeta._instances:  # type: ignore
            raise RuntimeError(
                f"{cls.__name__} has not been created yet. Call `create` first."
            )
        return SingletonMeta._instances[cls]  # type: ignore

    @classmethod
    def restart(cls: Type[T], *args, **kwargs) -> T:  # type: ignore
        if cls not in SingletonMeta._instances:  # type: ignore
            raise RuntimeError(
                f"{cls.__name__} has not been created yet. Call `create` first."
            )
        SingletonMeta._instances[cls]._reset()  # type: ignore
        SingletonMeta._instances.pop(cls)  # type: ignore
