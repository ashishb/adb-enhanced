from setuptools import setup, find_packages
import sys, os

version = '1.3'

setup(name='adb-enhanced',
        version=version,
        description="An ADB wrapper for Android developers",
        long_description="""\
        An ADB wrapper for Android developers for testing.

        # Examples
            * Turn doze mode on
            `adbe doze on`
            
            * Turn mobile-data off
            `adbe mobile-data off`
            
            * Turn on battery saver
            `adbe battery saver on`
            
            * Don't keep activities in the background
            `adbe dont-keep-activities on`
            
            * Grant storage-related runtime permissions
            `adbe permissions grant com.example.android storage`
            
            * Revoke storage-related runtime permissions
            `adbe permissions revoke com.example.android storage`
        
        # Usage:
            adbe.py [options] rotate (landscape | portrait | left | right)
            adbe.py [options] gfx (on | off | lines)
            adbe.py [options] overdraw (on | off | deut)
            adbe.py [options] layout (on | off)
            adbe.py [options] airplane ( on | off ) - This does not work on all the devices as of now.
            adbe.py [options] battery level <percentage>
            adbe.py [options] battery saver (on | off)
            adbe.py [options] battery reset
            adbe.py [options] doze (on | off)
            adbe.py [options] jank <app_name>
            adbe.py [options] devices
            adbe.py [options] top-activity
            adbe.py [options] force-stop <app_name>
            adbe.py [options] clear-data <app_name>
            adbe.py [options] mobile-data (on | off)
            adbe.py [options] mobile-data saver (on | off)
            adbe.py [options] rtl (on | off) - This is not working properly as of now.
            adbe.py [options] screenshot <filename.png>
            adbe.py [options] dont-keep-activities (on | off)
            adbe.py [options] input-text <text>
            adbe.py [options] press back
            adbe.py [options] permission-groups list all
            adbe.py [options] permissions list (all | dangerous)
            adbe.py [options] permissions (grant | revoke) <package_name> (calendar | camera | contacts | location | microphone | phone | sensors | sms | storage) - grant and revoke runtime permissions
        
        # Options:
            -e, --emulator          directs command to the only running emulator
            -d, --device            directs command to the only connected "USB" device
            -s, --serial SERIAL     directs command to the device or emulator with the given serial number or qualifier.

        See Readme for more details -
        https://github.com/ashishb/adb-enhanced/blob/master/README.md
        """,
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
