import pytest


def pytest_addoption(parser) -> None:
    parser.addoption("--testpythoninstallation", action="store")


@pytest.fixture(scope="session")
def testpythoninstallation(request):
    value = request.config.option.testpythoninstallation
    if value is None:
        pytest.skip()
    return value
