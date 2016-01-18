#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Setup file of Janitoo
"""
__license__ = """
    This file is part of Janitoo.

    Janitoo is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Janitoo is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Janitoo. If not, see <http://www.gnu.org/licenses/>.

"""
__author__ = 'Sébastien GALLET aka bibi21000'
__email__ = 'bibi21000@gmail.com'
__copyright__ = "Copyright © 2013-2014-2015 Sébastien GALLET aka bibi21000"

from os import name as os_name
from setuptools import setup, find_packages
from platform import system as platform_system
import glob
import os
import sys
from _version import janitoo_version

DEBIAN_PACKAGE = False
filtered_args = []

for arg in sys.argv:
    if arg == "--debian-package":
        DEBIAN_PACKAGE = True
    else:
        filtered_args.append(arg)
sys.argv = filtered_args

def get_data_files(res, rsrc, src, pattern):
    for root, dirs, fils in os.walk(src):
        if src == root:
            sub = []
            for fil in fils:
                sub.append(os.path.join(root,fil))
            res.append((rsrc, sub))
            for dire in dirs:
                get_data_files(res, os.path.join(rsrc, dire), os.path.join(root, dire), pattern)
    return res

data_files = []
get_data_files(data_files, 'docs','src/docs/','*')
get_data_files(data_files, 'config','src/config','*.py')
get_data_files(data_files, 'config','src/config','*.conf')
get_data_files(data_files, 'config','src/config','*.cfg')
get_data_files(data_files, 'config','src/config','*.mako')
get_data_files(data_files, 'config','src/config','README')

setup(
    name = 'janitoo_dhcp',
    description = "The DHCP server for janitoo",
    long_description = "The DHCP server for janitoo",
    author='Sébastien GALLET aka bibi2100 <bibi21000@gmail.com>',
    author_email='bibi21000@gmail.com',
    license = """
        This file is part of Janitoo.

        Janitoo is free software: you can redistribute it and/or modify
        it under the terms of the GNU General Public License as published by
        the Free Software Foundation, either version 3 of the License, or
        (at your option) any later version.

        Janitoo is distributed in the hope that it will be useful,
        but WITHOUT ANY WARRANTY; without even the implied warranty of
        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
        GNU General Public License for more details.

        You should have received a copy of the GNU General Public License
        along with Janitoo. If not, see <http://www.gnu.org/licenses/>.
    """,
    url='http://bibi21000.gallet.info/',
    version = janitoo_version,
    zip_safe = False,
    scripts=['src/scripts/jnt_dhcp'],
    packages = find_packages('src', exclude=["scripts", "docs", "config"]),
    package_dir = { '': 'src' },
    keywords = "dhcp",
    include_package_data=True,
    data_files = data_files,
    install_requires=[
                     'janitoo_db',
                    ],
    dependency_links = [
      'https://github.com/bibi21000/janitoo_db/archive/master.zip#egg=janitoo_db',
    ],
    entry_points = {
        "janitoo.models": [
            "janitoo_dhcp = janitoo_dhcp.models:extend",
        ],
    }
)
