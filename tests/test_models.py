# -*- coding: utf-8 -*-

"""Unittests for models.
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

import sys, os
import time, datetime
import unittest
import threading
from sqlalchemy.orm import sessionmaker, scoped_session

from janitoo_nosetests import JNTTBase
from janitoo_nosetests.models import JNTTModels, JNTTModelsCommon

from janitoo.options import JNTOptions
from janitoo_db.base import Base, create_db_engine
import janitoo_db.models as jntmodels

class ModelsCommon(JNTTModelsCommon):
    """Test the models
    """
    models_conf = "tests/data/janitoo_dhcp.conf"

    def test_001_lease(self):
        now = datetime.datetime.now()
        lease = jntmodels.Lease(add_ctrl="0001", add_node='0001', name="name", location="location", state='BOOT', last_seen=now)
        self.dbsession.merge(lease)
        self.dbsession.commit()

class TestModels(JNTTModels, ModelsCommon):
    """Test the models
    """
    pass
