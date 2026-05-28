from threading import Thread
from typing import Any, Callable


def run_in_thread(target: Callable[..., Any], *args: Any, **kwargs: Any) -> Thread:
    thread = Thread(target=target, args=args, kwargs=kwargs, daemon=True)
    thread.start()
    return thread
