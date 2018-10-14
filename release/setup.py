from setuptools import setup, find_packages
import sys, os

_DIR_OF_THIS_SCRIPT = os.path.split(__file__)[0]
_VERSION_FILE_NAME = 'version.txt'
_VERSION_FILE_PATH = os.path.join(_DIR_OF_THIS_SCRIPT, 'adbe', _VERSION_FILE_NAME)
_README_FILE_NAME = 'README.md'
_README_FILE_PATH =  os.path.join(_DIR_OF_THIS_SCRIPT, _README_FILE_NAME)

with open(_VERSION_FILE_PATH, 'r') as fh:
    version = fh.read().strip()

with open(_README_FILE_PATH, 'r') as fh:
    long_description = fh.read()

setup(name='adb-enhanced',
        version=version,
        description='Swiss-army knife for Android testing and development',
        long_description=long_description,
        long_description_content_type='text/markdown',
        classifiers=['Intended Audience :: Developers'], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
        keywords='Android ADB developer',
        author='Ashish Bhatia',
        author_email='ashishb@ashishb.net',
        url='https://github.com/ashishb/adb-enhanced',
        license='Apache',
        packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
        include_package_data=True,
        zip_safe=True,
        install_requires=[
                # -*- Extra requirements: -*-
                'docopt',
                'future',
                'psutil',
                ],
        entry_points={
                # -*- Entry points: -*-
                'console_scripts': [
                        'adbe=adbe:main',
                        ],
                }
        )
