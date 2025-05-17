import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--testpythoninstallation", action="store")


@pytest.fixture(scope="session")
def testpythoninstallation(request: pytest.FixtureRequest) -> bool:
    value = request.config.option.testpythoninstallation
    if value is None:
        pytest.skip()
    return value
