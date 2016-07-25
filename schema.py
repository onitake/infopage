#!/usr/bin/env python

import sys
from infopage import Infopage

if len(sys.argv) > 1 and '-h' in sys.argv[1:]:
    print "Usage: schema.py [-d]"
    print "-d     Drops all tables before recreating them"
    sys.exit(1)

dropping = len(sys.argv) > 1 and '-d' in sys.argv[1:]

ip = Infopage()
ip.loadconfig()
with ip:
	if dropping:
		ip.dropall()
	ip.createschema()
	if dropping:
		ip.insertdefault()
