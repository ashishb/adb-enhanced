lint: lint_python lint_markdown

test: test_python

documentation:
	pandoc --from=markdown --to=rst --output=docs/README.rst README.md && cd docs && make html

clean:
	rm -rf dist/  # Cleanup build dir

setup:
	brew install pandoc sphinx-doc uv
	brew link --force sphinx-doc
	uv sync

build: clean
	uv build

release_debug:
	uv publish --publish-url=https://test.pypi.org/legacy/

release_production:
	uv publish

lint_markdown:
	mdl -r ~MD013,~MD029,~MD033 README.md

format:
	uv run ruff check --config pyproject.toml --fix --unsafe-fixes --preview adbe tests

lint_python:
	uv run ruff check --preview --config pyproject.toml adbe tests

# To run a single test, for example, test_file_move3, try this
# python3 -m pytest -v tests/adbe_tests.py -k test_file_move3
test_python:
	echo "Wait for device"
	adb wait-for-device
	echo "Run the tests"
	uv run -- pytest -v tests/adbe_tests.py  # Python3 tests

test_python_installation:
	echo "Wait for device"
	adb wait-for-device
	echo "Run the tests"
	uv run -- pytest -v tests/adbe_tests.py  --durations=0 --testpythoninstallation true
