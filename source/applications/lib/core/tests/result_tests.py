# tests/test_result_pytest_class.py
import pytest
from core.result import Result  # Replace with your actual module if different


class TestResult:
    def test_ok_result_creation(self):
        result = Result.Ok("success")
        assert result.is_ok()
        assert not result.is_error()
        assert result.get_ok() == "success"

    def test_err_result_creation(self):
        error = ValueError("Something went wrong")
        result = Result.Err(error)
        assert not result.is_ok()
        assert result.is_error()
        assert result.get_error() is error

    def test_get_ok_raises_on_error(self):
        result = Result.Err(ValueError("Oops"))
        with pytest.raises(ValueError) as exc:
            result.get_ok()
        assert str(exc.value) == "value not found"

    def test_get_error_raises_on_ok(self):
        result = Result.Ok("All good")
        with pytest.raises(ValueError) as exc:
            result.get_error()
        assert str(exc.value) == "value not found"

    def test_propagate_exception_returns_error(self):
        error = RuntimeError("Boom")
        result = Result.Err(error)
        assert result.propagate_exception() is result

    def test_propagate_exception_raises_on_ok(self):
        result = Result.Ok("Fine")
        with pytest.raises(ValueError) as exc:
            result.propagate_exception()
        assert str(exc.value) == "value not found"

    def test_ok_with_none_still_ok(self):
        result = Result.Ok(None)
        assert result.is_ok()
        assert not result.is_error()
        assert result.get_ok() is None
