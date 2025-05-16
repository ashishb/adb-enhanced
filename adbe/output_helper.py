import dataclasses
import functools
import sys


@dataclasses.dataclass
class _Settings:
    """Settings for the output helper."""
    verbose: bool = False


__settings = _Settings()


def set_verbose(*, enabled: bool) -> None:
    __settings.verbose = enabled


def print_message(message: str) -> None:
    print(message)


def print_error_and_exit(error_string: str) -> None:
    print_error(error_string)
    sys.exit(1)


def print_error(error_string: str) -> None:
    if _is_interactive_terminal():
        print(f"{BashColors.FAIL}{error_string}{BashColors.ENDC}")
    else:
        print(error_string)


def print_verbose(message: str) -> None:
    if __settings.verbose and _is_interactive_terminal():
        print(f"{BashColors.WARNING}{message}{BashColors.ENDC}")
    else:
        print(message)


@functools.lru_cache
def _is_interactive_terminal() -> bool:
    return sys.stdout.isatty()


# Coloring approach inspired from https://stackoverflow.com/a/287944
# pylint: disable=too-few-public-methods
class BashColors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
