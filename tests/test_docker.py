# -*- coding: utf-8 -*-

"""Unittests for Janitoo-common.
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
__copyright__ = "Copyright © 2013-2014-2015-2016 Sébastien GALLET aka bibi21000"

import warnings
warnings.filterwarnings("ignore")

import sys, os
import time
import unittest
import logging
import threading
import mock
import logging

from janitoo_nosetests import JNTTBase
from janitoo_nosetests.dbserver import JNTTDBDockerServerCommon, JNTTDBDockerServer, jntt_docker_dbserver
from janitoo_nosetests.models import jntt_docker_models, jntt_docker_fullmodels

from janitoo.runner import Runner, jnt_parse_args
from janitoo.server import JNTServer
from janitoo.utils import HADD_SEP, HADD

sys.path.insert(0, os.path.abspath('.'))

from test_models import ModelsCommon
#Launch ModelsCommon tests for every supported database
jntt_docker_models(__name__, ModelsCommon, prefix='Dhcp')

from test_full_models import CommonFullModels
#Launch ModelsCommon tests for every supported database
jntt_docker_fullmodels(__name__, CommonFullModels)

from test_server import DhcpServerCommon
#Launch DhcpServerCommon tests for every supported database
jntt_docker_dbserver(__name__, DhcpServerCommon)
