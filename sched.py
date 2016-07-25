#!/usr/bin/env python

import requests
import sys
import re
import json
import psycopg2
import argparse
from uuid import UUID
from datetime import datetime
from infopage import Infopage

useragent = 'sched.py/0.0.1'

class ApiCallError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
class ConflictError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Sched(object):
    ERR_MATCH = re.compile(b'ERR: (.*)')
    EXPORT_API = 'https://{event}.sched.org/api/session/export'
    SYNC_API = 'https://{event}.sched.org/api/site/sync'

    def __init__(self, event, api_key, user_agent=None):
        # the first fetch should be unconditional, so start with the epoch
        self.last_update = datetime.fromtimestamp(0)
        self.api_key = api_key
        self.user_agent = user_agent
        self.export_url = self.EXPORT_API.format(event=event)
        self.sync_url = self.SYNC_API.format(event=event)

    def api_session_export(self, limit=-1):
        headers = { }
        if self.user_agent is not None:
            headers['User-Agent'] = self.user_agent
        fields = 'event_key,id,active,start_time_ts,end_time_ts,name,venue_id,venue'
        now = datetime.now()
        params = { 'api_key': self.api_key, 'format': 'json', 'strip_html': 1, 'fields': fields, 'since': int((self.last_update - datetime(1970, 1, 1)).total_seconds()) }
        if limit != -1:
            params['page'] = 1
            params['limit'] = limit
        r = requests.get(self.export_url, headers=headers, params=params)
        if r.status_code != 200:
            raise ApiCallError("Error exporting session: HTTP error: {status}".format(status=r.status_code))
        match = self.ERR_MATCH.match(r.content)
        if match:
            error = match.group(1).decode('utf-8')
            raise ApiCallError("Error exporting session: Call error: {error}".format(error=error))
        else:
            try:
                data = r.json()
                for e in data:
                    # Mangle data into standard types
                    e['start_time'] = datetime.fromtimestamp(e['start_time_ts'])
                    e['end_time'] = datetime.fromtimestamp(e['end_time_ts'])
                    e['active'] = e['active'].upper() == 'Y'
                    # Why is this a UUID?
                    e['id'] = UUID(e['id'])
                self.last_update = now
                return data
            except ValueError as e:
                raise ApiCallError("Error exporting session: Invalid data: {exception}".format(exception=str(e)))

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--config", help="specifies the configuration file name (default is /etc/infopage.conf)")
parser.add_argument("-e", "--event", help="specifies the name of the event on sched.org")
parser.add_argument("-k", "--key", help="specifies the API key (obtain this on your event administration page)")
parser.add_argument("-d", "--database", help="specifies the PostgreSQL database name")
parser.add_argument("-u", "--user", help="specifies the database user name")
parser.add_argument("-r", "--host", help="specifies the database host (local if not set)")
parser.add_argument("-p", "--password", help="specifies the database password (passwordless login if not set)")
parser.add_argument("-o", "--overwrite", help="starts with a fresh event list (rooms and slides will be kept)", action="store_true")
parser.add_argument("-c", "--clear", help="clears all events, rooms and slides (use this before the first import)", action="store_true")
parser.add_argument("-l", "--list", help="lists all rooms", action="store_true")
parser.add_argument("-s", "--slides", help="stores a slide order into the database, separated by a comma, specify -1 for the 'now' slide (use the -l option to list the slide numbers)")
args = parser.parse_args()

db = Infopage()
db.loadconfig(args.config)
if args.database:
	db.setconfig('dbname', args.database)
if args.user:
	db.setconfig('dbuser', args.user)
if args.host:
	db.setconfig('dbhost', args.host)
if args.password:
	db.setconfig('dbpassword', args.password)
if args.key:
	db.setconfig('schedkey', args.key)
if args.event:
	db.setconfig('schedevent', args.event)

with db:
	if args.list:
		rooms = db.rooms()
		print("Rooms:");
		for r in rooms:
			print("{id}, {name}".format(id=r['id'], name=r['name']))

	elif args.slides:
		slides = args.slides.split(',')
		order = [ ]
		for s in slides:
			if int(s) == -1:
				order.append({ 'room': None, 'master': 2 })
			else:
				order.append({ 'room': int(s), 'master': 0 })
		db.slides(order)

	else:
		if args.overwrite:
			db.clear()
		if args.clear:
			db.clear(True)

		sched = Sched(db.getconfig('schedevent'), db.getconfig('schedkey'), useragent)
		session = sched.api_session_export()
		db.update(session)
