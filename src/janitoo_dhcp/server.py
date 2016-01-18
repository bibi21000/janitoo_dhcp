# -*- coding: utf-8 -*-
"""The dhcp server

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

# Set default logging handler to avoid "No handler found" warnings.
import logging
logger = logging.getLogger(__name__)
import os, sys
import threading
import uuid as muuid
import time

from janitoo.dhcp import HeartbeatMessage
from janitoo.mqtt import MQTTClient
from janitoo.server import JNTControllerManager
from janitoo.utils import HADD, HADD_SEP, json_dumps, json_loads
from janitoo.utils import TOPIC_NODES, TOPIC_NODES_REPLY, TOPIC_NODES_REQUEST
from janitoo.utils import TOPIC_BROADCAST_REPLY, TOPIC_BROADCAST_REQUEST
from janitoo.utils import TOPIC_VALUES_USER, TOPIC_VALUES_CONFIG, TOPIC_VALUES_BASIC, TOPIC_VALUES_SYSTEM, TOPIC_HEARTBEAT
from janitoo_db.server import JNTDBServer
from janitoo_dhcp.lease import LeaseManager
from janitoo_dhcp.network import DhcpNetwork

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_DHCPD = 0x1000
COMMAND_CONTROLLER = 0x1050
COMMAND_DISCOVERY = 0x5000

assert(COMMAND_DESC[COMMAND_DISCOVERY] == 'COMMAND_DISCOVERY')
assert(COMMAND_DESC[COMMAND_CONTROLLER] == 'COMMAND_CONTROLLER')
assert(COMMAND_DESC[COMMAND_DHCPD] == 'COMMAND_DHCPD')
##############################################################

class DHCPServer(JNTDBServer, JNTControllerManager):
    """The Dynamic Home Configuration Protocol Server

    """
    def __init__(self, options):
        """
        """
        self.network = None
        self.lease_mgr = None
        self.mqtt_resolv = None
        self.mqtt_client = None
        self.resolv_timer = None
        self.heartbeat_timer = None
        self.section = "dhcp"
        JNTDBServer.__init__(self, options)
        JNTControllerManager.__init__(self)
        self.lease_mgr = LeaseManager(self.options)
        #~ self.uuid = self.options.get_option(self.section, 'uuid')
        #~ if self.uuid == None:
            #~ self.uuid = muuid.uuid1()
            #~ self.options.set_option(self.section, 'uuid', '%s'%self.uuid)
        self.loop_sleep = 0.25
        loop_sleep = self.options.get_option('system','loop_sleep')
        if loop_sleep is not None:
            try:
                self.loop_sleep = int(loop_sleep)
            except:
                logger.exception("[%s] - Exception when retrieving value of loop_sleep. Use default value instead", self.__class__.__name__)
        self.network = DhcpNetwork(self._stopevent, self.options, is_primary=True, is_secondary=False, do_heartbeat_dispatch=True)

    def __del__(self):
        """
        """
        try:
            self.stop()
        except:
            logger.debug("[%s] - Catched exception", self.__class__.__name__)

    def start(self):
        """Start the DHCP Server
        """
        logger.info("Start the server")
        JNTDBServer.start(self)
        JNTControllerManager.start_controller(self, self.section, self.options, cmd_classes=[COMMAND_DHCPD], hadd=None, name="DHCP Server",
            product_name="DHCP Server", product_type="DHCP Server")
        self.mqtt_resolv = MQTTClient(options=self.options.data, loop_sleep=self.loop_sleep)
        self.mqtt_resolv.connect()
        self.mqtt_resolv.start()
        #~ print "self.network.resolv_timeout", self.network.resolv_timeout
        self.resolv_timer = threading.Timer(self.network.resolv_timeout, self.resolv_heartbeat)
        self.resolv_timer.start()
        self.network.boot({0:self.get_controller_hadd()}, loop_sleep=self.loop_sleep)
        self.mqtt_client = MQTTClient(options=self.options.data, loop_sleep=self.loop_sleep)
        self.mqtt_client.add_topic(topic='/dhcp/lease/new', callback=self.mqtt_on_lease_new)
        self.mqtt_client.add_topic(topic='/dhcp/lease/repair', callback=self.mqtt_on_lease_repair)
        self.mqtt_client.add_topic(topic='/dhcp/lease/lock', callback=self.mqtt_on_lease_lock)
        self.mqtt_client.add_topic(topic='/dhcp/lease/remove', callback=self.mqtt_on_lease_remove)
        self.mqtt_client.add_topic(topic='/dhcp/lease/release', callback=self.mqtt_on_lease_release)
        self.mqtt_client.add_topic(topic='/dhcp/heartbeat#', callback=self.mqtt_on_heartbeat)
        self.mqtt_client.add_topic(topic='/dhcp/resolv/hadd', callback=self.mqtt_on_resolv_hadd)
        self.mqtt_client.add_topic(topic='/dhcp/resolv/name', callback=self.mqtt_on_resolv_name)
        self.mqtt_client.add_topic(topic='/dhcp/resolv/cmd_classes', callback=self.mqtt_on_resolv_cmd_classes)
        self.mqtt_client.connect()
        self.mqtt_client.subscribe(topic='/dhcp/#', callback=self.mqtt_on_message)
        self.mqtt_client.start()
        self.heartbeat_timer = threading.Timer(self.lease_mgr.heartbeat_timeout, self.check_heartbeat)
        self.heartbeat_timer.start()
        #ProgrammingError: (pysqlite2.dbapi2.ProgrammingError) SQLite objects created in a thread can only be used in that same thread.
        #The object was created in thread id 139632282289984 and this is thread id 139632153548544
        #[SQL: u'SELECT dhcpd_lease.add_ctrl AS dhcpd_lease_add_ctrl, dhcpd_lease.add_node AS dhcpd_lease_add_node, dhcpd_lease.name AS dhcpd_lease_name, dhcpd_lease.location AS dhcpd_lease_location, dhcpd_lease.cmd_classes AS dhcpd_lease_cmd_classes, dhcpd_lease.state AS dhcpd_lease_state, dhcpd_lease.last_seen AS dhcpd_lease_last_seen \nFROM dhcpd_lease'] [parameters: [immutabledict({})]]
        #self.lease_mgr.start(self.dbsession)
        #Use a new session for the lease
        self.lease_mgr.start(self.create_session())
        JNTControllerManager.start_controller_timer(self)

    def resolv_heartbeat(self):
        """
        """
        logger.debug("[%s] - Send heartbeat on resolv", self.__class__.__name__)
        if self.resolv_timer is not None:
            #The manager is started
            self.resolv_timer.cancel()
            self.resolv_timer = None
        self.resolv_timer = threading.Timer(self.network.resolv_timeout, self.resolv_heartbeat)
        self.resolv_timer.start()
        if self.get_controller_hadd() is not None:
            #~ print self.nodes[node].hadd
            add_ctrl, add_node = self.get_controller().split_hadd()
            msg = {'add_ctrl':add_ctrl, 'add_node':add_node, 'state':'ONLINE'}
            self.mqtt_resolv.publish(topic="/dhcp/resolv/heartbeat", payload=json_dumps(msg))

    def reload(self):
        """Reload the server
        """
        logger.info("[%s] - Reload the server", self.__class__.__name__)
        #~ self.stop()
        #~ time.sleep(1.0)
        #~ self.start()

    def start_threads(self):
        """Start the threads associated to this server.
        """
        pass

    def run(self):
        i = 0
        while not self._stopevent.isSet():
            i += 1
            self._stopevent.wait(self.loop_sleep)

    def stop(self):
        """Stop the DHCP Server
        """
        logger.info("Stop the server")
        if self.heartbeat_timer is not None:
            #The manager is started
            self.heartbeat_timer.cancel()
            self.heartbeat_timer = None
        if self.resolv_timer is not None:
            #The manager is started
            self.resolv_timer.cancel()
            self.resolv_timer = None
        JNTControllerManager.stop_controller_timer(self)
        if self.network is not None:
            self.network.stop()
        if self.lease_mgr is not None:
            self.lease_mgr.stop()
        if self.mqtt_resolv is not None:
            self.mqtt_resolv.stop()
            self.mqtt_resolv = None
        JNTControllerManager.stop_controller(self)
        if self.mqtt_client is not None:
            self.mqtt_client.stop()
            self.mqtt_client.unsubscribe(topic='/dhcp/#')
            self.mqtt_client.remove_topic(topic='/dhcp/lease/new')
            self.mqtt_client.remove_topic(topic='/dhcp/lease/repair')
            self.mqtt_client.remove_topic(topic='/dhcp/lease/lock')
            self.mqtt_client.remove_topic(topic='/dhcp/lease/remove')
            self.mqtt_client.remove_topic(topic='/dhcp/lease/release')
            self.mqtt_client.remove_topic(topic='/dhcp/heartbeat#')
            self.mqtt_client.remove_topic(topic='/dhcp/resolv/hadd')
            self.mqtt_client.remove_topic(topic='/dhcp/resolv/name')
            self.mqtt_client.remove_topic(topic='/dhcp/resolv/cmd_classes')
            self.mqtt_client = None
        maxi = 1
        while maxi<10 and not self.network.is_stopped:
            self._stopevent.wait(self.loop_sleep*10)
            maxi += self.loop_sleep*10
        JNTDBServer.stop(self)
        logger.info("Server stopped")

    def start_threads(self):
        """Start the threads associated to this server.
        """
        pass

    def check_heartbeat(self):
        """Check the states of the machines. Must be called in a timer
        Called in a separate thread. Must use a scoped_session.

        """
        if self.heartbeat_timer is not None:
            #The manager is started
            self.heartbeat_timer.cancel()
            self.heartbeat_timer = None
            self.heartbeat_timer = threading.Timer(self.lease_mgr.heartbeat_timeout, self.check_heartbeat)
            self.heartbeat_timer.start()
        self.lease_mgr.check_heartbeat(session=self.create_session())

    def mqtt_on_message(self, client, userdata, message):
        """On generic message

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        #~ print "mqtt_on_message Ok"
        pass

    def mqtt_on_lease_new(self, client, userdata, message):
        """On generic message

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        logger.debug("mqtt_on_lease_new receive %s", message.payload)
        res = {}
        res['msg_status'] = 200
        data = json_loads(message.payload)
        if 'rep_uuid' not in data:
            logger.debug("mqtt_on_lease_new receive a request with no rep_uuid")
            return
        for ffield in ['add_ctrl', 'add_node', 'options']:
            if ffield not in data:
                res['msg_status'] = 400
                res['msg_error'] = "Missing field %s in request" % ffield
        res['rep_uuid'] = data['rep_uuid']
        if res['msg_status'] == 200:
            for ffield in ['name', 'location']:
                if ffield not in data['options']:
                    res['msg_status'] = 400
                    res['msg_error'] = "Missing option %s in request" % ffield
        if res['msg_status'] == 200:
            lease = self.lease_mgr.new_lease(data['add_ctrl'], data['add_node'], data['options'])
            res.update(lease)
        #print res
        self.publish_reply(uuid=data['rep_uuid'], payload=json_dumps(res))

    def mqtt_on_lease_repair(self, client, userdata, message):
        """On lease repair message

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        logger.debug("mqtt_on_lease_repair receive %s", message.payload)
        res = {}
        res['msg_status'] = 200
        data = json_loads(message.payload)
        if 'rep_uuid' not in data:
            logger.debug("mqtt_on_lease_repair receive a request with no rep_uuid")
            return
        for ffield in ['add_ctrl', 'add_node', 'options']:
            if ffield not in data:
                res['msg_status'] = 400
                res['msg_error'] = "Missing field %s in request" % ffield
        res['rep_uuid'] = data['rep_uuid']
        if res['msg_status'] == 200:
            for ffield in ['name', 'location']:
                if ffield not in data['options']:
                    res['msg_status'] = 400
                    res['msg_error'] = "Missing option %s in request" % ffield
        if res['msg_status'] == 200:
            lease = self.lease_mgr.repair_lease(data['add_ctrl'], data['add_node'], data['options'])
            res.update(lease)
        #print res
        self.publish_reply(uuid=data['rep_uuid'], payload=json_dumps(res))

    def mqtt_on_lease_lock(self, client, userdata, message):
        """On lease lock message

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        logger.debug("mqtt_on_lease_lock receive %s", message.payload)
        res = {}
        res['msg_status'] = 200
        data = json_loads(message.payload)
        if 'rep_uuid' not in data:
            logger.debug("mqtt_on_lease_lock receive a request with no rep_uuid")
            return
        for ffield in ['add_ctrl', 'add_node']:
            if ffield not in data:
                res['msg_status'] = 400
                res['msg_error'] = "Missing field %s in request" % ffield
        res['rep_uuid'] = data['rep_uuid']
        if res['msg_status'] == 200:
            lease = self.lease_mgr.lock_lease(data['add_ctrl'], data['add_node'])
            if lease is None:
                res['msg_status'] = 400
                res['msg_error'] = "Can't find a lease for %s:%s" % (data['add_ctrl'], data['add_node'])
                res['add_ctrl'] = data['add_ctrl']
                res['add_node'] = data['add_node']
            else:
                res.update(lease)
        #print res
        self.publish_reply(uuid=data['rep_uuid'], payload=json_dumps(res))

    def mqtt_on_lease_release(self, client, userdata, message):
        """On lease release message

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        logger.debug("mqtt_on_lease_release receive %s", message.payload)
        res = {}
        res['msg_status'] = 200
        data = json_loads(message.payload)
        if 'rep_uuid' not in data:
            logger.debug("mqtt_on_lease_release receive a request with no rep_uuid")
            return
        for ffield in ['add_ctrl', 'add_node']:
            if ffield not in data:
                res['msg_status'] = 400
                res['msg_error'] = "Missing field %s in request" % ffield
        res['rep_uuid'] = data['rep_uuid']
        if res['msg_status'] == 200:
            lease = self.lease_mgr.release_lease(data['add_ctrl'], data['add_node'])
            res.update(lease)
        #print res
        self.publish_reply(uuid=data['rep_uuid'], payload=json_dumps(res))

    def mqtt_on_lease_remove(self, client, userdata, message):
        """On generic message

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        logger.debug("mqtt_on_lease_remove receive %s", message.payload)
        res = {}
        res['msg_status'] = 200
        data = json_loads(message.payload)
        if 'rep_uuid' not in data:
            logger.debug("mqtt_on_lease_remove receive a request with no rep_uuid")
            return
        for ffield in ['add_ctrl', 'add_node']:
            if ffield not in data:
                res['msg_status'] = 400
                res['msg_error'] = "Missing field %s in request" % ffield
        res['rep_uuid'] = data['rep_uuid']
        if res['msg_status'] == 200:
            self.lease_mgr.remove_lease(data['add_ctrl'], data['add_node'])
            res['add_ctrl'] = data['add_ctrl']
            res['add_node'] = data['add_node']
        #print res
        self.publish_reply(uuid=data['rep_uuid'], payload=json_dumps(res))

    def mqtt_on_heartbeat(self, client, userdata, message):
        """On heartbeat message

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        hb = HeartbeatMessage(message)
        add_ctrl, add_node, state = hb.get_heartbeat()
        if add_ctrl is not None:
            self.lease_mgr.heartbeat_hadd(add_ctrl, add_node, state)

    def mqtt_on_resolv_cmd_classes(self, client, userdata, message):
        """On generic message

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        #~ print "mqtt_on_resolv_cmd_classes Ok"
        pass

    def mqtt_on_resolv_name(self, client, userdata, message):
        """On generic message

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        #~ print "mqtt_on_resolv_name Ok"
        pass

    def mqtt_on_resolv_hadd(self, client, userdata, message):
        """On resolv hadd message

        :param client: the Client instance that is calling the callback.
        :type client: paho.mqtt.client.Client
        :param userdata: user data of any type and can be set when creating a new client instance or with user_data_set(userdata).
        :type userdata: all
        :param message: The message variable is a MQTTMessage that describes all of the message parameters.
        :type message: paho.mqtt.client.MQTTMessage
        """
        #~ print "mqtt_on_resolv_hadd receive %s"
        logger.debug("mqtt_on_resolv_hadd receive %s", message.payload)
        res = {}
        res['msg_status'] = 200
        data = json_loads(message.payload)
        if 'rep_uuid' not in data:
            logger.debug("mqtt_on_resolv_hadd receive a request with no rep_uuid")
            return
        for ffield in ['add_ctrl', 'add_node']:
            if ffield not in data:
                res['msg_status'] = 400
                res['msg_error'] = "Missing field %s in request" % ffield
        res['rep_uuid'] = data['rep_uuid']
        if res['msg_status'] == 200:
            lease = self.lease_mgr.resolv_hadd(data['add_ctrl'], data['add_node'])
            #print lease
            res.update(lease)
        #print res
        self.publish_reply(uuid=data['rep_uuid'], payload=json_dumps(res))

    def publish_reply(self, uuid, payload=None, qos=0, retain=False):
        """Publish an uid reply to clients.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param uuid: The uuid sent in the request.
        :type uuid: str
        :param payload: The actual message to send. If not given, or set to None a
                        zero length message will be used. Passing an int or float will result
                        in the payload being converted to a string representing that number. If
                        you wish to send a true int/float, use struct.pack() to create the
                        payload you require.
        :type payload: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        self.mqtt_client.publish_reply(uuid=uuid, payload=payload, qos=qos, retain=retain)

    def publish_stats(self, stat, value=None, qos=0, retain=False):
        """Publish a message on a topic.

        This causes a message to be sent to the broker and subsequently from
        the broker to any clients subscribing to matching topics.

        :param stat: The stat to send.
        :type stat: str
        :param value: the value of the stat
        :type value: message
        :param qos: The quality of service level to use.
        :type qos: int
        :param retain: If set to true, the message will be set as the "last known good"/retained message for the topic.
        :type retain: bool
        """
        self.mqtt_client.publish_stats(stat=stat, value=value, qos=qos, retain=retain)
        self.publish('$SYS/dhcp/')
