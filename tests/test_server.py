# -*- coding: utf-8 -*-

"""Unittests for DHCP Server.
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

import sys, os
import time, datetime
import unittest
import threading
import time
from pkg_resources import iter_entry_points

from janitoo_nosetests.dbserver import JNTTDBServer, JNTTDBServerCommon
from janitoo_nosetests.thread import JNTTThread, JNTTThreadCommon

from janitoo.utils import json_dumps, json_loads
from janitoo.utils import HADD_SEP, HADD
from janitoo.utils import TOPIC_HEARTBEAT
from janitoo.utils import TOPIC_NODES, TOPIC_NODES_REPLY, TOPIC_NODES_REQUEST
from janitoo.utils import TOPIC_BROADCAST_REPLY, TOPIC_BROADCAST_REQUEST
from janitoo.utils import TOPIC_VALUES_USER, TOPIC_VALUES_CONFIG, TOPIC_VALUES_SYSTEM, TOPIC_VALUES_BASIC

from janitoo_dhcp.server import DHCPServer

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_DISCOVERY = 0x5000

assert(COMMAND_DESC[COMMAND_DISCOVERY] == 'COMMAND_DISCOVERY')
##############################################################

class TestDhcpSerser(JNTTDBServer, JNTTDBServerCommon):
    """Test the server
    """
    loglevel = logging.DEBUG
    path = '/tmp/janitoo_test'
    broker_user = 'toto'
    broker_password = 'toto'
    server_class = DHCPServer
    server_conf = "tests/data/janitoo_dhcp.conf"

    def test_100_dhcp_cache_heartbeat_online(self):
        self.start()
        self.assertHeartbeatNode()
        pastdatetime = datetime.datetime.now() - datetime.timedelta(seconds=self.server.lease_mgr.heartbeat_timeout+1)
        self.server.lease_mgr._cachemgr.update(1, 1, state='ONLINE', last_seen=pastdatetime)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'ONLINE')
        for i in range(0, self.server.lease_mgr.heartbeat_count-1):
            self.server.lease_mgr.check_heartbeat()
            print(self.server.lease_mgr._cachemgr.entries[1][1], i+1)
            self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'ONLINE')
            self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['count'], i+1)
        self.server.lease_mgr.check_heartbeat()
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['count'], 0)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'PENDING')
        for i in range(0, self.server.lease_mgr.heartbeat_count-1):
            self.server.lease_mgr.check_heartbeat()
            print(self.server.lease_mgr._cachemgr.entries[1][1], i+1)
            self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'PENDING')
            self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['count'], i+1)
        self.server.lease_mgr.check_heartbeat()
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['count'], 0)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'FAILED')
        for i in range(0, self.server.lease_mgr.heartbeat_count):
            self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'FAILED')
            self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['count'], i)
            self.server.lease_mgr.check_heartbeat()
        self.stop()

    def test_101_dhcp_cache_multi(self):
        self.start()
        self.assertHeartbeatNode()
        pastdatetime = datetime.datetime.now() - datetime.timedelta(seconds=self.server.lease_mgr.heartbeat_timeout+1)
        self.server.lease_mgr._cachemgr.update(1, 0, state='OFFLINE', last_seen=pastdatetime)
        self.server.lease_mgr._cachemgr.update(1, 1, state='OFFLINE', last_seen=pastdatetime)
        self.server.lease_mgr._cachemgr.update(1, 2, state='OFFLINE', last_seen=pastdatetime)
        self.server.lease_mgr._cachemgr.update(1, 3, state='OFFLINE', last_seen=pastdatetime)
        self.server.lease_mgr._cachemgr.update(1, -1, state='ONLINE', last_seen=pastdatetime)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][0]['state'], 'ONLINE')
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'ONLINE')
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][2]['state'], 'ONLINE')
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][3]['state'], 'ONLINE')
        self.server.lease_mgr._cachemgr.remove(1, -1)
        self.assertTrue(1 not in self.server.lease_mgr._cachemgr.entries)
        self.stop()

    def test_105_dhcp_cache_heartbeat_dead(self):
        self.wipTest()
        self.start()
        self.assertHeartbeatNode()
        pastdatetime = datetime.datetime.now() - datetime.timedelta(seconds=self.server.lease_mgr.heartbeat_dead+1)
        self.server.lease_mgr._cachemgr.update(99, 1, state='ONLINE', last_seen=pastdatetime)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[99][1]['state'], 'ONLINE')
        for i in range(0, 3*self.server.lease_mgr.heartbeat_count):
            self.server.lease_mgr.check_heartbeat()
        print self.server.lease_mgr._cachemgr.entries
        self.assertTrue(99 not in self.server.lease_mgr._cachemgr.entries)
        self.stop()

    def test_110_dhcp_cache_heartbeat_recevive_in_online(self):
        self.start()
        self.assertHeartbeatNode()
        pastdatetime = datetime.datetime.now() - datetime.timedelta(seconds=self.server.lease_mgr.heartbeat_timeout+1)
        self.server.lease_mgr._cachemgr.update(1, 1, state='ONLINE', last_seen=pastdatetime)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'ONLINE')
        for i in range(0, self.server.lease_mgr.heartbeat_count-2):
            self.server.lease_mgr.check_heartbeat()
            self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'ONLINE')
            self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['count'], i+1)
        self.server.lease_mgr.heartbeat_hadd(1, 1)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['count'], 0)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'ONLINE')
        self.stop()

    def test_111_dhcp_cache_heartbeat_receive_in_pending(self):
        self.start()
        self.assertHeartbeatNode()
        pastdatetime = datetime.datetime.now() - datetime.timedelta(seconds=self.server.lease_mgr.heartbeat_timeout+1)
        self.server.lease_mgr._cachemgr.update(1, 1, state='ONLINE', last_seen=pastdatetime)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'ONLINE')
        for i in range(0, self.server.lease_mgr.heartbeat_count-1):
            self.server.lease_mgr.check_heartbeat()
            self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'ONLINE')
            self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['count'], i+1)
        self.server.lease_mgr.check_heartbeat()
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['count'], 0)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'PENDING')
        for i in range(0, self.server.lease_mgr.heartbeat_count-1):
            self.server.lease_mgr.check_heartbeat()
            self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'PENDING')
            self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['count'], i+1)
        self.server.lease_mgr.heartbeat_hadd(1, 1)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['count'], 0)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'ONLINE')
        self.stop()

    def test_120_dhcp_cache_remove(self):
        self.start()
        self.assertHeartbeatNode()
        pastdatetime = datetime.datetime.now() - datetime.timedelta(seconds=self.server.lease_mgr.heartbeat_timeout+1)
        self.server.lease_mgr._cachemgr.update(1, 1, state='ONLINE', last_seen=pastdatetime)
        self.assertEqual(self.server.lease_mgr._cachemgr.entries[1][1]['state'], 'ONLINE')
        self.server.lease_mgr._cachemgr.remove(1, 1)
        self.assertEqual(self.server.lease_mgr._cachemgr.len(), 0)
        self.stop()

    def test_130_dhcp_resolv_add(self):
        self.start()
        self.assertHeartbeatNode()
        pastdatetime = datetime.datetime.now() - datetime.timedelta(seconds=self.server.lease_mgr.heartbeat_timeout+1)
        options={'name':'name','location':'location','cmd_classes':'0x0000','otherkey':'other','otherkey2':'other2',}
        self.server.lease_mgr.repair_lease(1, 1, options)
        res = self.server.lease_mgr.resolv_hadd(1,1)
        print res
        self.assertEqual(res['name'], 'name')
        self.assertEqual(res['location'], 'location')
        for p in res['params']:
            print p
            self.assertTrue(p['key'] in ['otherkey', 'otherkey2'])
            self.assertTrue(p['value'] in ['other', 'other2'])
        self.stop()

    def test_140_dhcp_remove_lease(self):
        self.start()
        self.assertHeartbeatNode()
        pastdatetime = datetime.datetime.now() - datetime.timedelta(seconds=self.server.lease_mgr.heartbeat_timeout+1)
        options={'name':'name','location':'location','cmd_classes':'0x0000','otherkey':'other','otherkey2':'other2',}
        self.server.lease_mgr.repair_lease(1, 0, options)
        self.server.lease_mgr.repair_lease(1, 1, options)
        self.server.lease_mgr.repair_lease(1, 2, options)
        self.server.lease_mgr.repair_lease(1, 3, options)
        self.server.lease_mgr.remove_lease(1, 3)
        self.assertEqual(self.server.lease_mgr.resolv_hadd(1, 3), None)
        self.server.lease_mgr.remove_lease(1, -1)
        self.assertEqual(self.server.lease_mgr.resolv_hadd(1, 0), None)
        self.assertEqual(self.server.lease_mgr.resolv_hadd(1, 1), None)
        self.assertEqual(self.server.lease_mgr.resolv_hadd(1, 2), None)
        self.stop()

    def test_141_dhcp_remove_bad_lease(self):
        self.start()
        self.assertHeartbeatNode()
        pastdatetime = datetime.datetime.now() - datetime.timedelta(seconds=self.server.lease_mgr.heartbeat_timeout+1)
        options={'name':'name','location':'location','cmd_classes':'0x0000','otherkey':'other','otherkey2':'other2',}
        self.server.lease_mgr.remove_lease(1, 3)
        self.server.lease_mgr.remove_lease(1, -1)
        self.stop()

    def test_150_dhcp_get_lease_ctrl(self):
        self.start()
        self.assertHeartbeatNode()
        options={'name':'name','location':'location','cmd_classes':'0x0000','otherkey':'other','otherkey2':'other2',}
        res = self.server.lease_mgr.new_lease(-1, 3, options)
        print res
        self.assertEqual(res['add_ctrl'], 10)
        self.assertEqual(res['add_node'], 0)
        self.assertEqual(res['name'], 'name')
        self.assertEqual(res['location'], 'location')
        for p in res['params']:
            print p
            self.assertTrue(p['key'] in ['otherkey', 'otherkey2'])
            self.assertTrue(p['value'] in ['other', 'other2'])
        res = self.server.lease_mgr.new_lease(-1, 3, options)
        print res
        self.assertEqual(res['add_ctrl'], 11)
        self.assertEqual(res['add_node'], 0)
        self.assertEqual(res['name'], 'name')
        self.assertEqual(res['location'], 'location')
        for p in res['params']:
            print p
            self.assertTrue(p['key'] in ['otherkey', 'otherkey2'])
            self.assertTrue(p['value'] in ['other', 'other2'])
        self.stop()

    def test_152_dhcp_get_lease_node(self):
        self.start()
        self.assertHeartbeatNode()
        options={'name':'name','location':'location','cmd_classes':'0x0000','otherkey':'other','otherkey2':'other2',}
        res = self.server.lease_mgr.new_lease(-1, 3, options)
        print res
        self.assertEqual(res['add_ctrl'], 10)
        self.assertEqual(res['add_node'], 0)
        self.assertEqual(res['name'], 'name')
        self.assertEqual(res['location'], 'location')
        for p in res['params']:
            print p
            self.assertTrue(p['key'] in ['otherkey', 'otherkey2'])
            self.assertTrue(p['value'] in ['other', 'other2'])
        res = self.server.lease_mgr.new_lease(10, 3, options)
        print res
        self.assertEqual(res['add_ctrl'], 10)
        self.assertEqual(res['add_node'], 1)
        self.assertEqual(res['name'], 'name')
        self.assertEqual(res['location'], 'location')
        for p in res['params']:
            print p
            self.assertTrue(p['key'] in ['otherkey', 'otherkey2'])
            self.assertTrue(p['value'] in ['other', 'other2'])
        res = self.server.lease_mgr.new_lease(10, -1, options)
        print res
        self.assertEqual(res['add_ctrl'], 10)
        self.assertEqual(res['add_node'], 2)
        self.assertEqual(res['name'], 'name')
        self.assertEqual(res['location'], 'location')
        for p in res['params']:
            print p
            self.assertTrue(p['key'] in ['otherkey', 'otherkey2'])
            self.assertTrue(p['value'] in ['other', 'other2'])
        self.stop()

    def test_153_dhcp_get_bad_lease(self):
        self.start()
        self.assertHeartbeatNode()
        options={'name':'name','location':'location','cmd_classes':'0x0000','otherkey':'other','otherkey2':'other2',}
        res = self.server.lease_mgr.new_lease(2, 3, options)
        self.assertEqual(res, None)
        self.stop()

    def test_160_dhcp_resolv_cmd_classes(self):
        self.start()
        self.assertHeartbeatNode()
        options={'name':'name','location':'location','cmd_classes':'0x1050','otherkey':'other','otherkey2':'other2',}
        res = self.server.lease_mgr.new_lease(-1, 3, options)
        options={'name':'name','location':'location','cmd_classes':'0x0027','otherkey':'other','otherkey2':'other2',}
        res = self.server.lease_mgr.new_lease(10, -1, options)
        options={'name':'name','location':'location','cmd_classes':'0x0027','otherkey':'other','otherkey2':'other2',}
        res = self.server.lease_mgr.new_lease(10, -1, options)
        options={'name':'name','location':'location','cmd_classes':'0x0028,0x0027','otherkey':'other','otherkey2':'other2',}
        res = self.server.lease_mgr.new_lease(10, -1, options)
        res = self.server.lease_mgr.resolv_cmd_classes(cmd_classes="0x0027")
        print res
        self.assertEqual(len(res), 3)
        self.assertNotEqual(json_dumps(res), None)
        res = self.server.lease_mgr.resolv_cmd_classes(cmd_classes=["0x1050","0x0028"])
        print res
        self.assertEqual(len(res), 2)
        res = self.server.lease_mgr.resolv_cmd_classes()
        print res
        self.assertEqual(len(res), 4)
        self.stop()

    def test_170_dhcp_resolv_name(self):
        self.start()
        self.assertHeartbeatNode()
        options={'name':'name1','location':'location','cmd_classes':'0x1050','otherkey':'other','otherkey2':'other2',}
        res = self.server.lease_mgr.new_lease(-1, 3, options)
        options={'name':'name2','location':'kitchen.location','cmd_classes':'0x0027','otherkey':'other','otherkey2':'other2',}
        res = self.server.lease_mgr.new_lease(10, -1, options)
        options={'name':'name3','location':'lights.kitchen.location','cmd_classes':'0x0027','otherkey':'other','otherkey2':'other2',}
        res = self.server.lease_mgr.new_lease(10, -1, options)
        options={'name':'name4','location':'garden.location','cmd_classes':'0x0028,0x0027','otherkey':'other','otherkey2':'other2',}
        res = self.server.lease_mgr.new_lease(10, -1, options)
        res = self.server.lease_mgr.resolv_name(name="name1")
        print res
        self.assertEqual(len(res), 1)
        self.assertNotEqual(json_dumps(res), None)
        res = self.server.lease_mgr.resolv_name(location="location")
        print res
        self.assertEqual(len(res), 4)
        res = self.server.lease_mgr.resolv_name(location="kitchen.location")
        print res
        self.assertEqual(len(res), 2)
        self.stop()
