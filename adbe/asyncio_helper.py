import asyncio
import concurrent.futures
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")


# Executes method method_to_call for each argument in params_list and returns the result_list
def execute_in_parallel(method_to_call: Callable[[Any], T], params_list: list[Any]) -> list[T]:
    result_list: list[T] = []
    num_workers = 50
    loop = asyncio.get_event_loop()

    async def _list_debug_apps_async(params_list2: list[Any]) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(
                    executor,
                    method_to_call,
                    param) for param in params_list2
            ]

            result_list.extend(await asyncio.gather(*futures))

    loop.run_until_complete(_list_debug_apps_async(params_list))
    return result_list
