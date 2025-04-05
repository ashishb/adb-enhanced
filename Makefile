lint: lint_python3 lint_markdown

test: test_python3

documentation:
	pandoc --from=markdown --to=rst --output=docs/README.rst README.md && cd docs && make html

clean:
	rm -rf build/ dist/  # Cleanup build dir

setup:
	brew install pandoc sphinx-doc uv
	brew link --force sphinx-doc
	uv sync

build: clean
	uv build

release_debug: documentation
	./release.py test release

release_production: documentation
	./release.py production release

lint_markdown:
	mdl -r ~MD013,~MD029,~MD033 README.md

lint_python3:
# E0602 is due to undefined variable unicode which is defined only for Python 2
# W0511 is fixme due to TODOs in the code.
# adbe/adbe.py:756:8: W0601: Global variable 'screen_record_file_path_on_device' undefined at the module level (global-variable-undefined)
# adbe/adbe.py:764:8: W0601: Global variable 'screen_record_file_path_on_device' undefined at the module level (global-variable-undefined)
# adbe/adbe.py:752:4: W0621: Redefining name 'screen_record_file_path_on_device' from outer scope (line 759) (redefined-outer-name)
# C0111: Missing function docstring (missing-docstring)
	uv run -- pylint --disable=C0103,C0111,C0209,W1514 release.py
	uv run -- pylint adbe/*.py tests/*.py --disable=R0123,R0911,R0912,R0914,R0915,R1705,R1710,C0103,C0111,C0209,C0301,C0302,C1801,W0511,W0621,W0601,W0602,W0603
	uv run -- flake8 adbe --count --ignore=F401,E126,E501,W504 --show-source --statistics
	# Default complexity limit is 10
	# Default line length limit is 127
	uv run -- flake8 adbe --count --exit-zero --ignore=F401,E126,E501,W504 --max-complexity=13 --max-line-length=127 --statistics

# To run a single test, for example, test_file_move3, try this
# python3 -m pytest -v tests/adbe_tests.py -k test_file_move3
test_python3:
	echo "Wait for device"
	adb wait-for-device
	echo "Run the tests"
	uv run -- pytest -v tests/adbe_tests.py  # Python3 tests

test_python3_installation:
	echo "Wait for device"
	adb wait-for-device
	echo "Run the tests"
	uv run -- pytest -v tests/adbe_tests.py  --durations=0 --testpythoninstallation true
