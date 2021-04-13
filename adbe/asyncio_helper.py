import asyncio
import concurrent.futures
import typing


# This code has to be in a separate file since it is conditionally loaded for Python 3.5 and later.

# Executes method method_to_call for each argument in params_list and returns the result_list
def execute_in_parallel(method_to_call: typing.Callable, params_list: typing.List):

    result_list = []
    num_workers = 50
    loop = asyncio.get_event_loop()

    async def _func_async(params_list2: typing.List):
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
            loop = asyncio.get_event_loop()
            futures = [
                loop.run_in_executor(
                    executor,
                    method_to_call,
                    param) for param in params_list2
            ]

            for result in await asyncio.gather(*futures):
                result_list.append(result)

    loop.run_until_complete(_func_async(params_list))
    return result_list
