from typing import Any, Optional
from typing import Generic, TypeVar


def str_to_bool(value: str) -> bool:
    """
    Convert a string to a boolean.
    Returns True if the string is 'true' (case-insensitive),
    False if the string is 'false' (case-insensitive).
    Raises a ValueError for any other value.
    """
    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False
    else:
        raise ValueError(
            f"Cannot convert '{value}' to a boolean. Expected 'true' or 'false'."
        )


# Define a type variable
R = TypeVar("R")
E = TypeVar("E")


class Result(Generic[R]):
    """
    Generic class to represent the result of an operation that can either succeed or fail.
    Works like Rust's Result type.
    """

    @staticmethod
    def Ok(value: E = None) -> "Result[E]":
        return Result(value=value, error=None)

    @staticmethod
    def Err(error: Exception) -> "Result[Any]":
        return Result(value=None, error=error)

    def __init__(self, value: Optional[R] = None, error: Optional[Exception] = None):
        self.__value = value
        self.__error = error

    def is_ok(self) -> bool:
        return self.__value is not None or (
            self.__value is None and self.__error is None
        )

    def get_ok(self) -> R:
        if self.is_ok() is False:
            raise ValueError("value not found")
        return self.__value  # type: ignore

    def is_error(self) -> bool:
        return self.__error is not None

    def get_error(self) -> Exception:
        if self.__error is None:
            raise ValueError("value not found")
        return self.__error

    def propagate_exception(self) -> "Result[Any]":
        if self.__error is None:
            raise ValueError("value not found")
        return self
