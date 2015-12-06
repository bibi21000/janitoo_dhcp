# -*- coding: utf-8 -*-
"""The Node

about the pollinh mechanism :
 - simplest way to do it : define a poll_thread_timer for every value that needed to publish its data
 - Add a kind of polling queue that will launch the method to get and publish the value

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
import threading
import datetime
from pkg_resources import iter_entry_points
from janitoo.value import JNTValue
from janitoo.node import JNTNode
from janitoo.utils import HADD, HADD_SEP, json_dumps, json_loads, hadd_split
from janitoo.dhcp import HeartbeatMessage, check_heartbeats, CacheManager, JNTNetwork
from janitoo.mqtt import MQTTClient
from janitoo.options import JNTOptions

class DhcpNetwork(JNTNetwork):
    """The network manager for the flask application
    """

    def __init__(self, stop_event, options, **kwargs):
        """
        """
        JNTNetwork.__init__(self, stop_event, options, **kwargs)
        self.extend_from_entry_points('janitoo_dhcp')

    def emit_network(self):
        """Emit a network state event
        """
        ret = {}
        ret['state'] = self.state,
        ret['state_str'] = self.state_str,
        ret['nodes_count'] = self.nodes_count,
        ret['home_id'] = self.home_id,
        ret['is_failed'] = self.is_failed,
        ret['is_secondary'] = self.is_secondary,
        ret['is_primary'] = self.is_primary,
        #~ if 'kvals' in extras and self.network.dbcon is not None:
            #~ vals = self.kvals
            #~ for key in vals.keys():
                #~ ret[key]=vals[key]

    def extend_from_entry_points(self, group):
        """"Extend the network with methods found in entrypoints
        """
        for entrypoint in iter_entry_points(group = '%s.network'%group):
            logger.info('Extend network with %s', entrypoint.module_name )
            extend = entrypoint.load()
            extend( self )
