# tests/test_index_with_queue_pytest_class.py
import asyncio
import logging
import time
from typing import Any, Optional

import pytest

from core.result import Result
from core.que_runner import index_with_queue  # <-- adjust if needed
from core.logger import init_logging

init_logging("debug")
logger = logging.getLogger(__name__)


# ---------- Helpers ----------


async def ok(x: Any) -> Result[None]:
    await asyncio.sleep(0.005)
    return Result.Ok()


def err_on(target: Any, error: Optional[Exception] = None):
    async def _f(x: Any) -> Result[None]:
        await asyncio.sleep(0.002)
        if x == target:
            return Result.Err(error or RuntimeError("boom"))
        return Result.Ok()

    return _f


def raise_on(target: Any, error: Optional[Exception] = None):
    async def _f(x: Any) -> Result[None]:
        await asyncio.sleep(0.002)
        if x == target:
            raise (error or ValueError("raised"))
        return Result.Ok()

    return _f


class FaultyIterable(list):
    """
    Raises part-way through iteration to simulate a producer-side failure while enqueuing.
    """

    def __iter__(self):
        for i, v in enumerate(super().__iter__()):
            if i == 2:
                raise RuntimeError("iteration failed in producer")
            yield v


# ---------- Tests ----------


@pytest.mark.asyncio
class TestIndexWithQueue:
    async def test_empty_ok(self):
        res = await index_with_queue(objects=[], workers=2, index_one=ok)
        assert not res.is_error()

    async def test_invalid_workers(self):
        with pytest.raises(ValueError):
            await index_with_queue(objects=[1], workers=0, index_one=ok)

    async def test_all_success(self):
        seen = []

        async def track(x):
            seen.append(x)
            await asyncio.sleep(0.003)
            return Result.Ok()

        objs = list(range(30))
        res = await index_with_queue(objs, workers=4, index_one=track)
        assert not res.is_error(), (
            f"Unexpected Err: {res.get_error() if res.is_error() else None}"
        )
        # same elements, ignoring order (and preserving multiplicity)
        assert sorted(seen) == sorted(objs)
        assert len(seen) == len(objs)

    async def test_returns_err_when_index_one_returns_err(self):
        objs = list(range(20))
        res = await index_with_queue(objs, workers=4, index_one=err_on(5))
        assert res.is_error(), "Expected Err() after an item returns error"
        assert "boom" in str(res.get_error())

    async def test_returns_err_when_index_one_raises(self):
        objs = list(range(10))
        res = await index_with_queue(objs, workers=3, index_one=raise_on(3))
        assert res.is_error(), "Expected Err() after an item raises"
        assert "raised" in str(res.get_error())

    async def test_producer_iteration_error_bubbles_as_err(self):
        objs = FaultyIterable([1, 2, 3, 4, 5])
        res = await index_with_queue(objs, workers=2, index_one=ok)
        assert res.is_error(), "Expected Err() when producer fails during iteration"
        assert "producer" in str(res.get_error()).lower()

    async def test_progress_smoke(self):
        """
        Smoke test across a 5% boundary; ensures no rate/progress crash.
        """
        res = await index_with_queue(list(range(50)), workers=3, index_one=ok)
        assert not res.is_error()

    # ----------------- Guard-rails for queue discipline -----------------

    async def test_no_double_task_done_after_error__should_pass_once_fixed(self):
        """
        After the first error, workers will still consume items already in the queue.
        Your current code does q.task_done() inside the `if stop_event.is_set():` branch
        AND again in the `finally:` block -> double task_done per item -> ValueError:
        'task_done() called too many times'.

        This test asserts that DOES NOT happen. It will FAIL against the current
        implementation and PASS once you move q.task_done() to only execute when a
        task was actually fetched and only once per fetched item.
        """
        objs = list(range(100))
        res = await index_with_queue(objs, workers=5, index_one=err_on(3))
        # Desired behavior (after fix): still Err, but NOT caused by task_done mismatch.
        assert res.is_error(), "We expect an Err due to the failing item"
        assert "task_done() called too many times" not in str(res.get_error()), (
            "Double q.task_done detected — fix worker loop to call task_done exactly once per successful q.get()"
        )

    async def test_q_join_completes__should_pass_once_fixed(self):
        """
        Regression test for 'q.join() never finishes' scenarios due to incorrect
        task_done accounting. If task_done counts get corrupted, join can hang or
        return Err. We assert completion and Ok() in an all-success run.
        """
        objs = list(range(25))
        start = time.time()
        res = await index_with_queue(objs, workers=4, index_one=ok)
        duration = time.time() - start

        # Expect success and that it didn't hang forever.
        assert res.is_ok()
        assert duration < 10, "join likely hung — check task_done accounting"
