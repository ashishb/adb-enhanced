_verbose = False

def set_verbose(enabled):
    global _verbose
    _verbose = enabled

def print_message(message):
    print(message)


def print_error_and_exit(error_string):
    print('%s%s%s' % (bcolors.FAIL, error_string, bcolors.ENDC))
    quit(1)


def print_error(error_string):
    print('%s%s%s' % (bcolors.FAIL, error_string, bcolors.ENDC))


def print_verbose(message):
    if _verbose:
        print('%s%s%s' % (bcolors.WARNING, message, bcolors.ENDC))


# Coloring approach inspired from https://stackoverflow.com/a/287944
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
