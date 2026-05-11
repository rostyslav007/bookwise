import asyncio
from dataclasses import dataclass, field
from uuid import UUID

_DONE_SENTINEL = "__DONE__"


@dataclass
class ProgressState:
    step: str = ""
    queues: list[asyncio.Queue[str]] = field(default_factory=list)


class ProgressTracker:
    """In-memory per-book progress tracking with fan-out to SSE client queues."""

    def __init__(self) -> None:
        self._books: dict[UUID, ProgressState] = {}

    def subscribe(self, book_id: UUID) -> asyncio.Queue[str]:
        """Create a new queue for an SSE client and return it."""
        state = self._books.setdefault(book_id, ProgressState())
        queue: asyncio.Queue[str] = asyncio.Queue()
        state.queues.append(queue)
        if state.step:
            queue.put_nowait(state.step)
        return queue

    def unsubscribe(self, book_id: UUID, queue: asyncio.Queue[str]) -> None:
        """Remove a client's queue."""
        state = self._books.get(book_id)
        if state and queue in state.queues:
            state.queues.remove(queue)
        if state and not state.queues:
            self._books.pop(book_id, None)

    def emit(self, book_id: UUID, step: str) -> None:
        """Push a progress step to all subscribers."""
        state = self._books.setdefault(book_id, ProgressState())
        state.step = step
        for queue in state.queues:
            queue.put_nowait(step)

    def complete(self, book_id: UUID) -> None:
        """Signal completion to all subscribers and clean up."""
        state = self._books.pop(book_id, None)
        if state:
            for queue in state.queues:
                queue.put_nowait(_DONE_SENTINEL)


# Singleton instance
progress_tracker = ProgressTracker()
