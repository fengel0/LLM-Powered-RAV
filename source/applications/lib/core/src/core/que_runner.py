import asyncio
from opentelemetry import trace
import logging
from typing import Any, Callable, Coroutine, Sequence, TypeVar, Optional
from core.result import Result
import time

logger = logging.getLogger(__name__)
T = TypeVar("T")


async def index_with_queue(
    objects: Sequence[T],
    workers: int,
    index_one: Callable[[T], Coroutine[Any, Any, Result[None]]],
) -> Result[None]:
    """
    Process objects concurrently using a worker queue pattern.

    Args:
        objects: Sequence of objects to process
        workers: Number of concurrent workers
        index_one: Async function to process each object
        max_queue_size: Maximum queue size (None for unlimited)
        timeout: Overall timeout in seconds (None for no timeout)
    """
    total = len(objects)
    if total == 0:
        return Result.Ok()
    if workers < 1:
        raise ValueError("workers must be >= 1")

    logger.info("Processing %d objects with %d worker(s)", total, workers)

    # Use bounded queue if specified
    queue_size = len(objects)
    q: asyncio.Queue[T | None] = asyncio.Queue(maxsize=queue_size)

    # Shared state
    completed = 0
    completed_lock = asyncio.Lock()
    first_error: Optional[Exception] = None
    error_lock = asyncio.Lock()
    stop_event = asyncio.Event()

    start_time = time.time()

    async def set_first_error(error: Exception) -> None:
        """Thread-safe way to set the first error"""
        nonlocal first_error
        async with error_lock:
            if first_error is None:
                first_error = error
                stop_event.set()
                logger.info("set error")

    async def worker_fn(worker_id: int) -> None:
        """Worker function that processes items from the queue"""
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span(f"worker-{worker_id}"):
            nonlocal completed
            logger.debug("Worker %d started", worker_id)

            try:
                while True:
                    try:
                        # Use timeout to allow periodic stop_event checks
                        item = await asyncio.wait_for(q.get(), timeout=1.0)

                        if item is None:
                            logger.debug(
                                "Worker %d received shutdown signal", worker_id
                            )
                            break

                        if stop_event.is_set():
                            continue

                        # Process the item
                        result = await index_one(item)

                        if result.is_error():
                            await set_first_error(result.get_error())
                            continue

                        # Update progress
                        async with completed_lock:
                            completed += 1
                            progress = (completed / total) * 100
                            if completed % max(1, total // 20) == 0:  # Log every 5%
                                elapsed = time.time() - start_time
                                rate = completed / elapsed if elapsed > 0 else 0
                                logger.info(
                                    "Progress: %.1f%% (%d/%d) - %.1f items/sec",
                                    progress,
                                    completed,
                                    total,
                                    rate,
                                )

                    except asyncio.TimeoutError:
                        logger.info("timeout error")
                    except Exception as e:
                        logger.error(
                            "Worker %d encountered error: %s",
                            worker_id,
                            e,
                            exc_info=True,
                        )
                        await set_first_error(e)
                    finally:
                        q.task_done()

            except Exception as e:
                logger.error("Worker %d fatal error: %s", worker_id, e, exc_info=True)
                await set_first_error(e)
            finally:
                logger.info("Worker %d finished", worker_id)

    async def producer_fn() -> None:
        """Producer function that feeds items to the queue"""
        try:
            for obj in objects:
                if stop_event.is_set():
                    break
                await q.put(obj)

            # Send shutdown signals to all workers
            for _ in range(workers):
                await q.put(None)

        except Exception as e:
            logger.error("Producer error: %s", e, exc_info=True)
            await set_first_error(e)

    # Start all tasks
    worker_tasks = [asyncio.create_task(worker_fn(i)) for i in range(workers)]
    producer_task = asyncio.create_task(producer_fn())

    try:
        # Wait for completion with optional timeout
        await producer_task
        await q.join()
        logger.info("finished que")

        # Signal workers to stop
        stop_event.set()

        # Wait for all workers to complete
        await asyncio.gather(*worker_tasks, return_exceptions=True)

        elapsed = time.time() - start_time
        logger.info(
            "Completed processing %d objects in %.2f seconds (%.1f items/sec)",
            completed,
            elapsed,
            completed / elapsed if elapsed > 0 else 0,
        )

        if first_error:
            logger.error("Processing failed: %s", first_error)
            return Result.Err(first_error)

        return Result.Ok()

    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        return Result.Err(e)

    finally:
        # Cleanup: cancel any remaining tasks
        stop_event.set()

        tasks_to_cancel = [producer_task] + worker_tasks
        for task in tasks_to_cancel:
            if not task.done():
                task.cancel()

        # Wait for cancellation to complete
        await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
