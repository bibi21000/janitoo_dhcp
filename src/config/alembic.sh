#!/bin/bash
alembic -c janitoo_dhcpd.conf -n database $* --version-path=models/janitoo
