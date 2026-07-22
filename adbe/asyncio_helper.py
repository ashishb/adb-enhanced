import asyncio
import concurrent.futures
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


# Executes method method_to_call for each argument in params_list and returns the result_list
def execute_in_parallel[T](method_to_call: Callable[[Any], T], params_list: list[Any]) -> list[T]:
    num_workers = 50

    async def _run() -> list[T]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            loop = asyncio.get_running_loop()
            futures = [
                loop.run_in_executor(executor, method_to_call, param)
                for param in params_list
            ]
            return list(await asyncio.gather(*futures))

    return asyncio.run(_run())
