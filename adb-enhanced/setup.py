from setuptools import setup, find_packages
import sys, os

version = '1.0'

setup(name='adb-enhanced',
        version=version,
        description="An ADB wrapper for Android developers",
        long_description="""\
                An ADB wrapper for Android developers for testing.
        See Readme for more details -
        https://github.com/ashishb/adb-enhanced/blob/master/README.md
        """,
        classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
        keywords='Android ADB developer',
        author='Ashish Bhatia',
        author_email='ashishbhatia.ab@gmail.com',
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
