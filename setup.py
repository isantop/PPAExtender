#!/usr/bin/python3

from distutils.core import setup
from distutils.command.install import install
from distutils.core import Command
import sys

setup(
    name = 'repoman',
    version = '1.1.0',
    description = 'Easily manage software sources',
    url = 'https://github.com/isantop/repoman',
    license = 'GNU GPL3',
    packages=['repoman'],
    data_files = [
        ('/usr/share/metainfo', ['data/repoman.appdata.xml']),
        ('/usr/share/dbus-1/system-services', ['data/ro.santopiet.repoman.service']),
        ('/usr/share/polkit-1/actions', ['data/ro.santopiet.repoman.policy']),
        ('/etc/dbus-1/system.d/', ['data/ro.santopiet.repoman.conf']),
        ('/usr/share/applications', ['data/repoman.desktop']),
        ('/usr/share/repoman', ['data/style.css']),
        ('/usr/lib/repoman', ['add-del-ppa.py', 'data/repoman.pkexec'])
    ],
    scripts = ['repoman/repoman'],
)
