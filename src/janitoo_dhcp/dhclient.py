# -*- coding: utf-8 -*-
"""The dhcp controller client

At start, the controller must get new or lock leases for himself and its nodes.
It must also send heartbeat to the dhpc server.
At the end, it must release all leases

How we should use it :

- openzwave : nodes appears on notification, can be added to network by external commands.
 - when node has its essential informations, we check

- roomba : need an ip address, a user and a password.
 - at first start, the roomba server has no hadd for its controller. So it request a new one.
 - After, the server will lock all leases for himself and its nodes usinf (add_ctrl,-1). He will receive lease for itsel and all its nodes at a time.

 To add a new node :
  - the controller has subscribed to /machines/config/add_ctrl:#
  - the core check that command_class add_node is implemented by the controller and retrieve all types of nodes that can be added.
  - the core get config parameters for this type of node from the crontoller (use values config of zwave)
  - the core get parameters from user
  - the core create the lease with user values on the dhcpd server.
  - the dhcp server create the lease for hadd and publish message to /machines/config/hadd
  - the controller receive the config on /machines/config/add_ctrl:add_node and start the node

 To update a node :
  - the controller has subscribed to /machines/config/add_ctrl:#
  - the core resolv_hadd from the dhcp server
  - the core get config parameters for this node from the crontoller (use values config of zwave)
  - the core get new parameters from user
  - the core repair_lease with user values on the dhcpd server.
  - the dhcp server update the lease for hadd and publish message to /machines/config/hadd
  - the controller receive the config on /machines/config/add_ctrl:add_node and update the node/controller

Boot sequence:
  if the controller has no previous hadd, get a new one and release it

  if one :
   - subscribe to /machines/config/add_ctrl:#
   - on message : update name, locaton, if needed we can restart the node ...
   - lock the hadd : add_ctrl:-1 : this
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

from janitoo.mqtt import MQTTClient
import threading

class DHCPClient(object):
    """The Dynamic Home Configuration Protocol client
    """

    def __init__(self, options):
        """
        """
        self.___options = options
        self.dhcpc_options = None
        self._dhcpc_client = MQTTClient(options=self.__options)
        self._dhcpc_hadd_timer = None
        self._dhcpc_heartbeat_timer = None
        self._dhcpc_heartbeat_timeout = None
        self._dhcpc_callback = None
        self._dhcpc_add_ctrl = -1
        self._dhcpc_add_nodes = {}
        """The nodes managed by the controller including itself
        '0' : {'callback_heartbeat' : a_callback_called_to_check_the_state_of_machine}.

        """
        self.hadd = None
        self._dhcp_tries = 3
        self._dhcp_try_current = 0
        self._dhcp_timeout = 10
        self._dhcp_heartbeat = 60

    def _dhcpc_hadd(self):
        """Check that we receive an HADD before a timeout
        """
        self._dhcpc_hadd_timer = None
        self._dhcpc_hadd_timer = threading.Timer(self._dhcpc_heartbeat_timeout, self._dhcpc_heartbeat)
        self._dhcpc_hadd_timer.start()

    def _dhcpc_heartbeat(self):
        """Manage the heartbeat
        """
        self._dhcpc_heartbeat_timer = None
        self._dhcpc_heartbeat_timer = threading.Timer(self._dhcpc_heartbeat_timeout, self._dhcpc_heartbeat)
        self._dhcpc_heartbeat_timer.start()
        for node in list(self._dhcpc_add_nodes.keys()):
            if self._dhcpc_add_nodes[node]['callback_heartbeat'] == None or self._dhcpc_add_nodes[node]['callback_heartbeat'](node) == True:
                self.mqttc.publish_heartbeat(add_ctrl, add_node)

    def _dhcpc_on_message(self, client, userdata, message):
        """On DHCP message
        """
        pass

    def lock_dhcpc(self, add_node, callback):
        """Get an HADD fron the DHCP server and launch callback at the end of the process
        """
        self._dhcpc_callback = None
        if 'dhcp_tries' in self.__options:
            try:
                self._dhcp_tries = int(self.__options['dhcp_tries'])
            except ValueError:
                pass
        if 'dhcp_timeout' in self.__options:
            try:
                self._dhcp_timeout = int(self.__options['dhcp_timeout'])
            except ValueError:
                pass
        if 'dhcp_heartbeat' in self.__options:
            try:
                self._dhcp_heartbeat = int(self.__options['dhcp_heartbeat'])
            except ValueError:
                pass
        self.dhcpc_options = self.get_options('dhcp')
        add_ctrl = -1
        add_node = -1
        try:
            if "add_ctrl" in options and "add_node" in self.dhcpc_options:
                add_ctrl = int(self.dhcpc_options['add_ctrl'])
                add_node = int(self.dhcpc_options['add_node'])
        except ValueError:
            pass

    def new_dhcpc(self, add_node, callback):
        """Get a new HADD fron the DHCP server and launch callback at the end of the process
        """
        self._dhcpc_callback = None
        if 'dhcp_tries' in self.__options:
            try:
                self._dhcp_tries = int(self.__options['dhcp_tries'])
            except ValueError:
                pass
        if 'dhcp_timeout' in self.__options:
            try:
                self._dhcp_timeout = int(self.__options['dhcp_timeout'])
            except ValueError:
                pass
        if 'dhcp_heartbeat' in self.__options:
            try:
                self._dhcp_heartbeat = int(self.__options['dhcp_heartbeat'])
            except ValueError:
                pass
        self.dhcpc_options = self.get_options('dhcp')
        add_ctrl = -1
        add_node = -1
        try:
            if "add_ctrl" in options and "add_node" in self.dhcpc_options:
                add_ctrl = int(self.dhcpc_options['add_ctrl'])
                add_node = int(self.dhcpc_options['add_node'])
        except ValueError:
            pass

    def release_dhcpc(self, add_node):
        """Release the HADD
        """
        pass
