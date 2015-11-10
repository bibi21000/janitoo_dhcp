# -*- coding: utf-8 -*-
"""The models

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
logger = logging.getLogger('janitoo.dhcp')
import os
import sys

import sqlalchemy as sa
from sqlalchemy.orm import relationship, backref, synonym

from janitoo_db.base import Base
from janitoo_db.helpers import CRUDMixin
from janitoo_db.security import generate_password_hash, check_password_hash

def extend( jntmodel ):

    class Lease(Base, CRUDMixin):
        __tablename__ = 'dhcp_leases'
        # Here we define columns for the table person
        # Notice that each column is also a normal Python instance attribute.
        add_ctrl = sa.Column(sa.Integer)
        add_node = sa.Column(sa.Integer)
        name = sa.Column(sa.String(50), nullable=False)
        location = sa.Column(sa.String(250), nullable=False)
        cmd_classes = sa.Column(sa.String(250), nullable=False, default="0x0000")
        state = sa.Column(sa.String(10), nullable=False, default='offline')
        last_seen = sa.Column(sa.DateTime)
        params = relationship( "LeaseParam",
                                primaryjoin="and_(Lease.add_ctrl==LeaseParam.add_ctrl, Lease.add_node==LeaseParam.add_node)",
                            )
        __table_args__ = (
            sa.PrimaryKeyConstraint('add_ctrl', 'add_node', name="dhcp_leases_primary"),
                         )
        def classes(self):
            """
            """
            return self.cmd_classes.split(",")

    class LeaseParam(Base, CRUDMixin):
        __tablename__ = 'dhcp_leases_param'
        # Here we define columns for the table address.
        # Notice that each column is also a normal Python instance attribute.
        add_ctrl = sa.Column(sa.Integer, sa.ForeignKey('dhcp_leases.add_ctrl'))
        add_node = sa.Column(sa.Integer, sa.ForeignKey('dhcp_leases.add_node'))
        key = sa.Column(sa.String(50), nullable=False)
        value = sa.Column(sa.String(250), nullable=False)
        lease = relationship( "Lease",
                                primaryjoin="and_(Lease.add_ctrl==LeaseParam.add_ctrl, Lease.add_node==LeaseParam.add_node)",
                                backref=backref('lease', cascade="save-update, merge, delete, delete-orphan" )
                            )
        __table_args__ = (
            sa.PrimaryKeyConstraint('add_ctrl', 'add_node', 'key', name="dhcp_leases_param_primary"),
            sa.ForeignKeyConstraint( ['add_ctrl', 'add_node'],
                                  ['dhcp_leases.add_ctrl', 'dhcp_leases.add_node'],
                                  name="dhcp_leases_param_foreign_lease"),
                                )
