from setuptools import setup, find_packages
import sys, os

version = '1.5.2'

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='adb-enhanced',
        version=version,
        description="An ADB wrapper for Android developers",
        long_description=long_description,
        classifiers=["Intended Audience :: Developers"], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
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
                ],
        entry_points={
                # -*- Entry points: -*-
                'console_scripts': [
                        'adbe=adbe:main',
                        ],
                }
        )
