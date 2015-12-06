# -*- coding: utf-8 -*-

"""Unittests for Janitoo-dhcp.
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
import logging
import mock
import uuid

from alembic import command as alcommand

from janitoo_nosetests.dbserver import JNTTDBServer, JNTTDBServerCommon
from janitoo_nosetests.thread import JNTTThread, JNTTThreadCommon

from janitoo_dhcp.server import DHCPServer
from janitoo.utils import json_dumps, json_loads, HADD, HADD_SEP

class TestMqtt(JNTTDBServer):
    """Test the common server
    """
    loglevel = logging.DEBUG
    path = '/tmp/janitoo_test'
    broker_user = 'toto'
    broker_password = 'toto'
    server_class = DHCPServer
    server_conf = "tests/data/janitoo_dhcp.conf"

    def on_message(self, client, userdata, message):
        """On generic message
        """
        self.message = message
        self.payload=json_loads(message.payload)

    def test_100_dhcp_heartbeat_bad(self):
        self.start()
        self.topic = "/dhcp/heartbeat"
        self.mqttc.publish(self.topic, 'ONLINE')
        self.mqttc.publish(self.topic+'/', 'ONLINE')
        self.mqttc.publish(self.topic+'/'+'a%s0'%HADD_SEP, 'ONLINE')
        self.mqttc.publish(self.topic+'/'+'0%sa'%HADD_SEP, 'ONLINE')
        self.mqttc.publish(self.topic+'/'+'a%sa'%HADD_SEP, 'ONLINE')
        self.mqttc.publish(self.topic+'/'+'None%sNone'%HADD_SEP, 'ONLINE')
        msg = {'add_ctrl':'a', 'add_node':'a'}
        self.mqttc.publish(self.topic, json_dumps(msg))
        msg = {'add_ctrl':None, 'add_node':None}
        self.mqttc.publish(self.topic, json_dumps(msg))
        time.sleep(1)
        self.stop()

    def test_101_dhcp_lease_lock_bad(self):
        self.start()
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':'a', 'add_node':'a'}
        self.mqttc.publish("/dhcp/lease/lock", json_dumps(msg))
        i = 0
        while self.message is None and i<100000:
            i += 1
            time.sleep(0.0001)
        self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 400)
        self.message = None
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':None, 'add_node':None}
        self.mqttc.publish("/dhcp/lease/lock", json_dumps(msg))
        i = 0
        while self.message is None and i<100000:
            i += 1
            time.sleep(0.0001)
        self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 400)
        time.sleep(1)
        self.stop()

    def test_110_dhcp_lease_new_release_remove(self):
        self.start()
        self.topic = "/dhcp/lease/new"
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':-1, 'add_node':-1,'options' : {'name':'test', 'location':'location_test'}}
        self.mqttc.publish(self.topic, json_dumps(msg))
        i = 0
        while self.message is None and i<100000:
            i += 1
            time.sleep(0.0001)
        self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 200)
        self.assertEqual(self.payload['name'], 'test')
        self.assertEqual(self.payload['location'], 'location_test')
        self.assertEqual(self.payload['add_ctrl'], 10)
        self.assertEqual(self.payload['add_node'], 0)
        add_ctrl = self.payload['add_ctrl']
        add_node = self.payload['add_node']
        self.message = None
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':add_ctrl, 'add_node':add_node}
        self.mqttc.publish("/dhcp/resolv/hadd", json_dumps(msg))
        i = 0
        while self.message is None and i<100000:
            i += 1
            time.sleep(0.0001)
        self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 200)
        self.assertEqual(self.payload['name'], 'test')
        self.assertEqual(self.payload['location'], 'location_test')
        self.assertEqual(self.payload['add_ctrl'], add_ctrl)
        self.assertEqual(self.payload['add_node'], add_node)
        self.assertEqual(self.payload['state'], 'BOOT')
        self.message = None
        self.mqttc.publish_heartbeat(add_ctrl, add_node)
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':add_ctrl, 'add_node':add_node}
        self.mqttc.publish("/dhcp/resolv/hadd", json_dumps(msg))
        i = 0
        while self.message is None and i<100000:
            i += 1
            time.sleep(0.0001)
        self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 200)
        self.assertEqual(self.payload['name'], 'test')
        self.assertEqual(self.payload['location'], 'location_test')
        self.assertEqual(self.payload['add_ctrl'], add_ctrl)
        self.assertEqual(self.payload['add_node'], add_node)
        self.assertEqual(self.payload['state'], 'ONLINE')
        self.message = None
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':add_ctrl, 'add_node':add_node}
        self.mqttc.publish("/dhcp/lease/release", json_dumps(msg))
        i = 0
        while self.message is None and i<100000:
            i += 1
            time.sleep(0.0001)
        self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 200)
        self.assertEqual(self.payload['add_ctrl'], add_ctrl)
        self.assertEqual(self.payload['add_node'], add_node)
        self.assertEqual(self.payload['state'], 'OFFLINE')
        self.message = None
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':add_ctrl, 'add_node':add_node}
        self.mqttc.publish("/dhcp/resolv/hadd", json_dumps(msg))
        i = 0
        while self.message is None and i<100000:
            i += 1
            time.sleep(0.0001)
        self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 200)
        self.assertEqual(self.payload['name'], 'test')
        self.assertEqual(self.payload['location'], 'location_test')
        self.assertEqual(self.payload['add_ctrl'], add_ctrl)
        self.assertEqual(self.payload['add_node'], add_node)
        self.assertEqual(self.payload['state'], 'OFFLINE')
        self.message = None
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':add_ctrl, 'add_node':add_node}
        self.mqttc.publish("/dhcp/lease/remove", json_dumps(msg))
        i = 0
        while self.message is None and i<100000:
            i += 1
            time.sleep(0.0001)
        self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 200)
        self.assertEqual(self.payload['add_ctrl'], add_ctrl)
        self.assertEqual(self.payload['add_node'], add_node)
        time.sleep(1)
        self.stop()

    def test_111_dhcp_lease_new_release_lock_release(self):
        self.start()
        self.topic = "/dhcp/lease/new"
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':-1, 'add_node':-1,'options' : {'name':'test', 'location':'location_test'}}
        self.mqttc.publish(self.topic, json_dumps(msg))
        i = 0
        while self.message is None and i<100000:
            i += 1
            time.sleep(0.0001)
        self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 200)
        self.assertEqual(self.payload['name'], 'test')
        self.assertEqual(self.payload['location'], 'location_test')
        self.assertEqual(self.payload['add_ctrl'], 10)
        self.assertEqual(self.payload['add_node'], 0)
        add_ctrl = self.payload['add_ctrl']
        add_node = self.payload['add_node']
        self.message = None
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':add_ctrl, 'add_node':add_node}
        self.mqttc.publish("/dhcp/lease/release", json_dumps(msg))
        i = 0
        while self.message is None and i<100000:
            i += 1
            time.sleep(0.0001)
        self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 200)
        self.assertEqual(self.payload['add_ctrl'], add_ctrl)
        self.assertEqual(self.payload['add_node'], add_node)
        self.assertEqual(self.payload['state'], 'OFFLINE')
        self.message = None
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':add_ctrl, 'add_node':add_node}
        self.mqttc.publish("/dhcp/lease/lock", json_dumps(msg))
        i = 0
        while self.message is None and i<100000:
            i += 1
            time.sleep(0.0001)
        self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 200)
        self.assertEqual(self.payload['name'], 'test')
        self.assertEqual(self.payload['location'], 'location_test')
        self.assertEqual(self.payload['add_ctrl'], add_ctrl)
        self.assertEqual(self.payload['add_node'], add_node)
        self.assertEqual(self.payload['state'], 'BOOT')
        self.message = None
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':add_ctrl, 'add_node':add_node}
        self.mqttc.publish("/dhcp/lease/release", json_dumps(msg))
        i = 0
        while self.message is None and i<100000:
            i += 1
            time.sleep(0.0001)
        self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 200)
        self.assertEqual(self.payload['add_ctrl'], add_ctrl)
        self.assertEqual(self.payload['add_node'], add_node)
        self.assertEqual(self.payload['state'], 'OFFLINE')
        time.sleep(1)
        self.stop()

    def test_120_dhcp_lease_repair(self):
        self.start()
        self.topic = "/dhcp/lease/repair"
        uuid = self.mqttc.subscribe_reply(callback=self.on_message)
        msg = {'rep_uuid' : uuid, 'add_ctrl':11, 'add_node':1,'options' : {'name':'test', 'location':'location_test'}}
        self.mqttc.publish(self.topic, json_dumps(msg))
        time.sleep(2)
        uuid = self.mqttc.unsubscribe_reply(uuid)
        print self.payload
        self.assertEqual(self.payload['msg_status'], 200)
        self.assertEqual(self.payload['name'], 'test')
        self.assertEqual(self.payload['location'], 'location_test')
        self.assertEqual(self.payload['add_ctrl'], 11)
        self.assertEqual(self.payload['add_node'], 1)
        self.mqttc.publish_heartbeat(self.payload['add_ctrl'], self.payload['add_node'])
        time.sleep(1)
        self.stop()

