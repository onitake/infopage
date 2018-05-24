#!/usr/bin/env python

import sys
import csv
import psycopg2
import argparse
import uuid
from datetime import datetime
from zlib import adler32
from infopage import Infopage

CSV_NS = uuid.UUID('6ba7b810-9dad-11d1-80b4-cccccccccccc')
CSV_FIELDS = [ 'location', 'event', 'start', 'end' ]
CSV_DATEFMT = '%Y-%m-%d %H:%M'
def read_csv(csvfile):
    events = []
    with open(csvfile, 'rb') as input:
        records = csv.DictReader(input, dialect='excel', fieldnames=CSV_FIELDS)
        for record in records:
            if record['event'] is not '' and record['location'] is not '':
                event = {
                    'id': uuid.uuid5(CSV_NS, record['event']),
                    'name': record['event'],
                    'venue_id': adler32(record['location']),
                    'venue': record['location'],
                    'active': True,
                    'start_time': datetime.strptime(record['start'], CSV_DATEFMT),
                    'end_time': datetime.strptime(record['end'], CSV_DATEFMT),
                }
                print("{event}".format(event=event))
                events.append(event)
    return events

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", help="the CSV file to read")
parser.add_argument("-f", "--config", help="specifies the configuration file name (default is /etc/infopage.conf)")
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

		if args.input is not None:
            events = read_csv(args.input)
            db.update(events)
