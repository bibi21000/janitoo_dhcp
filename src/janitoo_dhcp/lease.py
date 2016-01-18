# -*- coding: utf-8 -*-
"""The dhcp lease manager

About the sleeping nodes: should have the sleeping capability

Add capabilites
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
import datetime

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.sql import and_, exists, or_

from janitoo.dhcp import HeartbeatMessage, CacheManager, leases_states, check_heartbeats
from janitoo.utils import HADD
from janitoo_db.helpers import saobject_to_dict
import janitoo_db.models as jntmodel

class LeaseManager(object):
    """The leases manager

    Can be used in dynammic mode (with start, stop and a db session or in dynamic mode to keep the states of modes in memory (calling check_heartbeat) periodically.

    About the sqlalchemy session object :
     - Use transaction
     - We will receive a gret number of ping_in messages. If we commit on each, we will create some extra db work that can be annoying on raspberry pi.
     - we will store ping message in a cache and commit them to database on check_ping

    """
    def __init__(self, options):
        """

        :param extras: The extra inforamtions to add
        :type extras: []
        :returns: A dict
        :rtype: dict()
        """
        self.dbsession = None
        self.heartbeat_timeout = int(options.data["heartbeat_timeout"]) if "heartbeat_timeout" in options.data else 60
        self.heartbeat_count = int(options.data["heartbeat_count"]) if "heartbeat_count" in options.data else 3
        self.heartbeat_dead = int(options.data["heartbeat_dead"]) if "heartbeat_dead" in options.data else 604800
        self._new_lease_lock = threading.Lock()
        self._cachemgr = CacheManager()

    def start(self, dbsession):
        """Start the lease manager in db mode

        :param extras: The extra inforamtions to add
        :type extras: []
        :returns: A dict
        :rtype: dict()
        """
        #Initialise the cache
        self.dbsession = dbsession
        self._cachemgr.start(self.dbsession.query(jntmodel.Lease).filter(jntmodel.Lease.state!="DEAD", jntmodel.Lease.state!="OFFLINE"))

    def stop(self):
        """Stop the lease manager

        :param extras: The extra inforamtions to add
        :type extras: []
        :returns: A dict
        :rtype: dict()
        """
        #We set the state of online machines to offline.
        for ctrl in self._cachemgr.entries.keys():
            for node in self._cachemgr.entries[ctrl].keys():
                if self._cachemgr.entries[ctrl][node]['state'] in ['ONLINE']:
                    self._cachemgr.entries[ctrl][node]['state'] = 'OFFLINE'
        self._cachemgr.flush(self.dbsession.query(jntmodel.Lease))
        self.dbsession.commit()
        self.dbsession.expunge_all()
        self._cachemgr = CacheManager()

    def new_lease(self, add_ctrl, add_node, options):
        """Get a new lease
        return add_ctrl, add_node, options

        :param add_ctrl: the controller part of the address
        :type add_ctrl: Integer
        :param add_node: the node part of the address. 0 for controller
        :type add_node: Integer
        :returns: A dict with all informations
        :rtype: dict()
        """
        #Check for malformated request
        self._new_lease_lock.acquire()
        try:
            if add_ctrl == -1:
                #A new controller wants an hadd.
                #Find and return max(add_ctrl), 0
                max_ctrl = self.dbsession.query(func.max(jntmodel.Lease.add_ctrl)).scalar()
                if max_ctrl < 10:
                    add_ctrl = 10
                else:
                    add_ctrl = max_ctrl + 1
                add_node = 0
            else:
                #A new node wants an hadd
                #check if add_ctrl,0 exists
                #Find and return add_ctrl, max(add_node)
                max_node = self.dbsession.query(func.max(jntmodel.Lease.add_node)).filter(jntmodel.Lease.add_ctrl==add_ctrl).scalar()
                if max_node is None:
                    return None
                add_node = max_node + 1
            return self.repair_lease(add_ctrl, add_node, options)
        finally:
            self._new_lease_lock.release()

    def lock_lease(self, add_ctrl, add_node):
        """Lock a lease already in database. We should manage the case of a db crash.
        Also update last_seen to now and state to boot

        :param add_ctrl: the controller part of the address
        :type add_ctrl: Integer
        :param add_node: the node part of the address. 0 for controller.
        :type add_node: Integer
        :returns: A dict with all informations
        :rtype: dict()
        """
        query = self.dbsession.query(jntmodel.Lease).filter(jntmodel.Lease.add_ctrl==add_ctrl, jntmodel.Lease.add_node==add_node)
        try:
            node = query.one()
            node.state = "BOOT"
            node.last_seen = datetime.datetime.now()
            self._cachemgr.update(add_ctrl, add_node, state=node.state, last_seen=node.last_seen)
            ddict = saobject_to_dict(node)
            self.dbsession.commit()
            return ddict
        except sa.orm.exc.NoResultFound:
            return None

    def repair_lease(self, add_ctrl, add_node, options):
        """Repair a lease. If the dhcpd database is lost, some client can send their adress and some other informations to rebuid it.
        Also update last_seen to now and state to boot

        :param add_ctrl: the controller part of the address
        :type add_ctrl: Integer
        :param add_node: the node part of the address. 0 for controller
        :type add_node: Integer
        :param options: the options for the lease
        :type options: dict()
        """
        soptions = []
        lname = None
        llocation = None
        lcmd_classes = None
        for k in options.keys():
            if k == 'name':
                lname = options[k]
            elif k == 'location':
                llocation = options[k]
            elif k == 'cmd_classes':
                lcmd_classes = options[k]
            else:
                soptions.append(jntmodel.LeaseParam(key=k, value=options[k]))
        now = datetime.datetime.now()
        l = jntmodel.Lease(add_ctrl=add_ctrl, add_node=add_node, name=lname, location=llocation, state='BOOT', cmd_classes=lcmd_classes, last_seen=now, params=soptions)
        self._cachemgr.update(add_ctrl, add_node, state='BOOT', last_seen=now )
        self.dbsession.merge(l)
        self.dbsession.commit()
        return self.resolv_hadd(add_ctrl, add_node)

    def release_lease(self, add_ctrl, add_node):
        """Release a lease. When a controller / node shutdown, it must release its nodes. Set the state to offline
        return false or true

        :param add_ctrl: the controller part of the address
        :type add_ctrl: Integer
        :param add_node: the node part of the address. 0 for controller, -1 for all nodes managed by controller.
        :type add_node: Integer
        """
        query = self.dbsession.query(jntmodel.Lease).filter(jntmodel.Lease.add_ctrl==add_ctrl)
        if add_node != -1:
            query = query.filter(jntmodel.Lease.add_node==add_node)
        self._cachemgr.remove(add_ctrl, add_node)
        nodes = query.all()
        for node in nodes:
            node.state = "OFFLINE"
            node.last_seen = datetime.datetime.now()
        self.dbsession.commit()
        return self.resolv_hadd(add_ctrl, add_node)

    def remove_lease(self, add_ctrl, add_node):
        """Remove a lease from db

        :param add_ctrl: the controller part of the address
        :type add_ctrl: Integer
        :param add_node: the node part of the address. 0 for controller, -1 for all nodes managed by controller.
        :type add_node: Integer
        :param state: the state of the node.
        :type state: String
        :param last_seen: the last time the node have been seen.
        :type last_seen: datetime
        :returns: A dict
        :rtype: dict()
        """
        query = self.dbsession.query(jntmodel.Lease).filter(jntmodel.Lease.add_ctrl==add_ctrl)
        if add_node != -1:
            query = query.filter(jntmodel.Lease.add_node==add_node)
        self._cachemgr.remove(add_ctrl, add_node)
        nodes = query.all()
        for node in nodes:
            self.dbsession.delete(node)
        self.dbsession.commit()

    def resolv_name(self, name=None, location=None, options=['all']):
        """Resolv a name, location to lease(s)

        :param extras: The extra inforamtions to add
        :type extras: []
        :returns: A dict
        :rtype: dict()
        return [add_ctrl, add_node, options]
        """
        query = self.dbsession.query(jntmodel.Lease)
        conditions = []
        if location is None and name is not None:
            #Look for name in all locations
            query = query.filter(jntmodel.Lease.name == name)
        elif location is not None and name is None:
            #Look for location
            query = query.filter(jntmodel.Lease.location.like("%"+location))
        elif location is None and name is None:
            #Return all locations
            pass
        else:
            #Look for name in one location
            query = query.filter(jntmodel.Lease.name == name, jntmodel.Lease.location == location)
        data = query.all()
        res = {}
        for line in data:
            #print line.cmd_classes
            res[HADD%(line.add_ctrl, line.add_node)] = saobject_to_dict(line)
        return res


    def resolv_cmd_classes(self, cmd_classes=[]):
        """Resolv a cmd_classes to lease(s)

        :param extras: The extra inforamtions to add
        :type extras: []
        :returns: A dict
        :rtype: dict()
        return [add_ctrl, add_node, options]
        """
        query = self.dbsession.query(jntmodel.Lease)
        conditions = []
        if type(cmd_classes) == type(""):
            cmd_classes = [cmd_classes]
        for cmdc in cmd_classes:
            #print cmdc
            conditions.append(jntmodel.Lease.cmd_classes.like("%"+cmdc+"%"))
        query = query.filter(or_(*conditions))
        #query = query.filter(jntmodel.Lease.cmd_classes.like(""+cmd_classes[0]+"%"))
        data = query.all()
        res = {}
        for line in data:
            #print line.cmd_classes
            res[HADD%(line.add_ctrl, line.add_node)] = saobject_to_dict(line)
        return res

    def resolv_hadd(self, add_ctrl, add_node):
        """Resolv an address to lease

        :param add_ctrl: the controller part of the address
        :type add_ctrl: Integer
        :param add_node: the node part of the address. 0 for controller
        :type add_node: Integer
        :returns: A dict with all informations
        :rtype: dict()
        """
        query = self.dbsession.query(jntmodel.Lease).filter(jntmodel.Lease.add_ctrl==add_ctrl, jntmodel.Lease.add_node==add_node)
        try:
            ddict = saobject_to_dict(query.one())
            try:
                ddict['state'] = self._cachemgr.entries[add_ctrl][add_node]['state']
            except KeyError:
                pass
            try:
                ddict['last_seen'] = self._cachemgr.entries[add_ctrl][add_node]['last_seen']
            except KeyError:
                pass
            return ddict
        except sa.orm.exc.NoResultFound:
            return None

    def heartbeat_hadd(self, add_ctrl, add_node, state='ONLINE'):
        """A machine heartbeat us

        :param add_ctrl: the controller part of the address
        :type add_ctrl: Integer
        :param add_node: the node part of the address. 0 for controller, -1 for all nodes managed by controller.
        :type add_node: Integer
        """
        #~ print "Update heartbeat here"
        self._cachemgr.update(add_ctrl, add_node, state=state, last_seen=datetime.datetime.now())

    def check_heartbeat(self, session=None):
        """Check the states of the machine. Must be called in a timer
        Called in a separate thread. Must use a scoped_session.

        :param session: the session to use to communicate with db. May be a scoped_session if used in a separate tread. If None, use the common session.
        :type session: sqlalchemy session
        """
        self._cachemgr.check_heartbeats(heartbeat_timeout=self.heartbeat_timeout, heartbeat_count=self.heartbeat_count, heartbeat_dead=self.heartbeat_dead)
        self._cachemgr.flush(self.dbsession.query(jntmodel.Lease))
        self.dbsession.commit()
        self.dbsession.expunge_all()
