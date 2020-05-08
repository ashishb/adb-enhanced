import sys

__VERBOSE_MODE = False


def set_verbose(enabled):
    global __VERBOSE_MODE
    __VERBOSE_MODE = enabled


def print_message(message):
    print(message)


def print_error_and_exit(error_string):
    print_error(error_string)
    sys.exit(1)


def print_error(error_string):
    if _is_interactive_terminal():
        error_string = '%s%s%s' % (BashColors.FAIL, error_string, BashColors.ENDC)
    print(error_string)


def print_verbose(message):
    if __VERBOSE_MODE:
        if _is_interactive_terminal():
            message = '%s%s%s' % (BashColors.WARNING, message, BashColors.ENDC)
        print(message)


def _is_interactive_terminal():
    return sys.stdout.isatty()


# Coloring approach inspired from https://stackoverflow.com/a/287944
# pylint: disable=too-few-public-methods
class BashColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
