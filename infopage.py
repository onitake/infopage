#!/usr/bin/env python

import sys
import psycopg2
import json
import io

class Infopage (object):
    """
    infopage database and API access abstraction
    
    Example usage:
    
    ip = Infopage()
    ip.loadconfig
    with ip:
        rooms = ip.rooms()
        print(str(rooms))
    
    Or:
    
    ip = Infopage()
    ip.loadconfig()
    ip.connect()
    rooms = ip.rooms()
    ip.close()
    print(str(rooms))
    """
    
    DEFAULT_CFGFILE = "/etc/infopage.conf"
    DEFAULT_DBUSER = "infopage"
    DEFAULT_DBNAME = "infopage"
    DEFAULT_DBPASSWORD = None
    DEFAULT_DBHOST = None
    
    def __init__(self, configfile=None):
        """
        Create a new infopage database access object.
        
        Keyword arguments:
        configfile -- a config file to load (if None or unset, no config is loaded)
        """
        self.withwith = ('2.5' in psycopg2.__version__)
        self.conn = None
        self.setdefaults()
        if configfile is not None:
            self.loadconfig(configfile)
    
    def __enter__(self):
        if self.conn is not None:
            raise AssertionError("A database connection is still open. Don't try to create a context before closing it first.")
        self.connect()
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
    
    def setdefaults(self):
        """
        Revert all settings to their defaults.
        Database settings do not automatically apply to open connections.
        
        Defaults:
        database = infopage
        database user = infopage
        database password = (not used)
        """
        self.config = {
            'dbuser': Infopage.DEFAULT_DBUSER,
            'dbname': Infopage.DEFAULT_DBNAME,
            'dbpassword': Infopage.DEFAULT_DBPASSWORD,
            'dbhost': Infopage.DEFAULT_DBHOST
        }
    
    def loadconfig(self, configfile=None):
        """
        Load settings from a JSON file.
        
        The config file should have the following format:
        {
            "dbuser": "database user",
            "dbname": "database name",
            "dbpassword": "database password",
            "dbhost": "database server"
        }
        Any undefined settings will not be modified.
        Arbitrary settings can be set as well, they will be silently
        ignored by Infopage, but can be picked up by scripts.
        
        If loading the default config file and it doesn't exist, no error
        will be raised. If opening an explicit configuration fails, the
        IOError is propagated.
        
        Keyword arguments:
        configfile -- the name of the file to load (default: /etc/infopage.conf)
        """
        realconfig = configfile
        if configfile is None:
            realconfig = Infopage.DEFAULT_CFGFILE
        try:
            fh = io.open(realconfig, 'r')
            config = json.load(fh)
            self.config.update(config)
        except IOError as e:
            if configfile is None:
                # ignore if the default config does not exist
                pass
            else:
                raise e
    def saveconfig(self, configfile):
        raise NotImplementedError("Saving configuration files is currently not implemented.")
    def getconfig(self, key):
        """Get a value from the configuration dictionary."""
        return self.config[key]
    def setconfig(self, key, value):
        """
        Set a value in the configuration dictionary.
        
        Supported keys are:
        dbuser -- the database user
        dbname -- the database name
        dbpassword -- the database login password (passwordless login is used if set to None)
        dbhost -- the database host (a local connection is used if set to None)
        """
        self.config[key] = value
    
    def connect(self):
        """Connect to the database"""
        self.conn = psycopg2.connect(database=self.config['dbname'], user=self.config['dbuser'], password=self.config['dbpassword'], host=self.config['dbhost'])
    def close(self):
        """Close the open database connection"""
        if self.conn is not None:
            self.conn.close()
            self.conn = None
    
    def execute(self, closure, *args, **kwargs):
        """Execute a statement closure inside a state monitor, if available."""
        if self.withwith:
            with self.conn:
                with self.conn.cursor() as cur:
                    return closure(cur, *args, **kwargs)
        else:
            cur = self.conn.cursor()
            ret = closure(cur, *args, **kwargs)
            self.conn.commit()
            cur.close()
            return ret
    
    def clear(self, clearall=False):
        """
        Clear the events table, and optionally the slides and rooms too.
        
        Keyword arguments:
        clearall -- also remove data from the slides and rooms tables
        """
        def closure(cur):
            cur.execute("""
                DELETE FROM events
            """)
            if clearall:
                cur.execute("""
                    DELETE FROM slides
                """)
                cur.execute("""
                    DELETE FROM rooms
                """)
        self.execute(closure)
        
    def rooms(self):
        """Return the list of rooms and their unique ID."""
        def closure(cur):
            cur.execute("""
                SELECT id, name
                FROM rooms
            """)
            ret = [ ]
            for r in cur.fetchall():
                ret.append({ 'id': r[0], 'name': r[1] })
            return ret

        return self.execute(closure)

    def slides(self, slides):
        """
        Set the slide order.
        
        Keyword arguments:
        slides -- a list of slides in the following format:
        [
          { 'master': master_number, 'room': room_number },
          ...
        ]
        """
        def closure(cur, slides):
            cur.execute("""
                DELETE FROM slides
            """)
            i = 0
            for s in slides:
                cur.execute("""
                    INSERT INTO slides
                    (master, room, sequence_no)
                    VALUES (%(master)s, %(rid)s, %(seqid)s)
                """, {
                    'master': s['master'],
                    'rid': s['room'],
                    'seqid': i
                })
                i = i + 1

        return self.execute(closure, slides)

    def update(self, events):
        """
        Update the events table.
        
        As there is currently no reliable way to determine when events are deleted,
        the events table should always be cleared before updating.
        
        The rooms table will be updated automatically if a venue does not exist yet.
        
        Keyword arguments:
        events -- an event list in the following format:
        [
          {
            'id': unique_event_id,
            'venue': room_name,
            'venue_id': unique_room_id,
            'active': true_or_false,
            'start_time': timestamp_start,
            'end_time': timestamp_end,
            'name': event_name
          },
          ...
        ]
        """
        def closure(cur, events):
            for e in events:
                eid = e['id'].int & 0x7fffffff
                rid = e['venue_id']
                # TODO Upsert requires Postgres 9.5
                cur.execute("""
                    SELECT id, name
                    FROM rooms
                    WHERE id = %(rid)s
                """, {
                    'rid': rid
                })
                if cur.rowcount == 0:
                    cur.execute("""
                        INSERT INTO rooms
                        (id, name)
                        VALUES (%(rid)s, %(rname)s)
                    """, {
                        'rid': rid,
                        'rname': e['venue']
                    })
                else:
                    if cur.fetchone()[1] != e['venue']:
                        # TODO Implement UPDATE if appropriate
                        raise ConflictError("Room exists, but ID and name don't match")
                cur.execute("""
                    SELECT id
                    FROM events
                    WHERE id = %(eid)s
                """, {
                    'eid': eid
                })
                if cur.rowcount == 0:
                    if e['active']:
                        cur.execute("""
                            INSERT INTO events (id, room, begins, ends, name)
                            VALUES (%(eid)s, %(rid)s, %(begins)s, %(ends)s, %(ename)s)
                        """, {
                            'eid': eid,
                            'rid': rid,
                            'begins': e['start_time'],
                            'ends': e['end_time'],
                            'ename': e['name']
                        })
                    else:
                        cur.execute("DELETE FROM events WHERE id = %(eid)s", { 'eid': eid })
                else:
                    cur.execute("""
                        UPDATE events
                        SET room = %(rid)s, begins = %(begins)s, ends = %(ends)s, name = %(name)s
                        WHERE id = %(eid)s
                    """, {
                        'eid': eid,
                        'rid': rid,
                        'begins': e['start_time'],
                        'ends': e['end_time'],
                        'name': e['name']
                    })
        
        self.execute(closure, events)

    def dropall(self):
        """Delete all tables."""
        def closure(cur):
            cur.execute("""
                DROP TABLE IF EXISTS config;
                DROP TABLE IF EXISTS slides;
                DROP TABLE IF EXISTS events;
                DROP TABLE IF EXISTS rooms;
            """)
        
        self.execute(closure)
    
    def insertdefault(self):
        """Insert default settings."""
        def closure(cur):
            cur.execute("""
                INSERT INTO config (key, value) VALUES ('max_rows', '10');
                INSERT INTO config (key, value) VALUES ('time_format', '%H:%M');
                INSERT INTO config (key, value) VALUES ('has_now', '1');
                INSERT INTO config (key, value) VALUES ('now_text', 'Now');
                INSERT INTO config (key, value) VALUES ('now_master_text', 'In session');
            """)
        
        self.execute(closure)
    
    def createschema(self):
        """Create all the database tables if they don't exist yet."""
        def closure(cur):
            cur.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key varchar(1024) PRIMARY KEY,
                    value text
                );
                CREATE TABLE IF NOT EXISTS rooms (
                    id serial PRIMARY KEY,
                    name text NOT NULL
                );
                CREATE TABLE IF NOT EXISTS slides (
                    id serial PRIMARY KEY,
                    -- The ordering index of the slide, set to NULL if slide should be hidden
                    sequence_no integer NULL UNIQUE,
                    -- The room that should be displayed on this slide, set to NULL for master slides aren't associated with a room
                    room integer REFERENCES rooms NULL,
                    -- The masters are numbered sequentially and defined in content.py
                    master integer NOT NULL,
                    -- Overrides the title (normally the room name will be used)
                    title text NULL,
                    -- If max_rows is NULL, use the config default
                    max_rows integer NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id serial PRIMARY KEY,
                    room integer REFERENCES rooms NOT NULL,
                    begins timestamp NOT NULL,
                    ends timestamp NOT NULL,
                    name text NOT NULL
                );
            """)
        
        self.execute(closure)

    def setting(self, key):
        value = [ None ]
        def closure(cur, key):
            cur.execute("SELECT value FROM config WHERE key = %s", (key, ))
            if cur.rowcount > 0:
                value[0] = cur.fetchone()[0]
        self.execute(closure, key)
        return value[0]

    def select(self, slidecounter):
        value = { 'slide': None, 'master': None, 'title': None }
        def closure(cur):
            cur.execute("SELECT COUNT(sequence_no) FROM slides WHERE sequence_no IS NOT NULL")
            activeslides = cur.fetchone()[0]
            if activeslides > 0:
                slideidx = abs(int(slidecounter)) % activeslides
                cur.execute("SELECT master, title FROM slides WHERE slides.sequence_no = %s", (slideidx, ))
                if cur.rowcount > 0:
                    values = cur.fetchone()
                    value['master'] = values[0]
                    value['title'] = values[1]
                    value['slide'] = slideidx
        if slidecounter is not None and slidecounter != '' and slidecounter > 0:
            self.execute(closure)
        return value

    def slide(self, slideno):
        value = { 'name': None, 'room': None, 'maxrows': None }
        def closure(cur, slideno):
            cur.execute("SELECT rooms.name, slides.room, slides.max_rows FROM slides JOIN rooms ON slides.room = rooms.id WHERE slides.sequence_no = %s", (slideno, ))
            if cur.rowcount > 0:
                values = cur.fetchone()
                value['name'] = values[0]
                value['room'] = values[1]
                value['maxrows'] = values[2]
        self.execute(closure, slideno)
        return value

    def events(self, time, limit, room = None, withnow = False):
        value = { 'now': None, 'after': [ ] } # { 'begins': None, 'ends': None, 'name': None, 'room': None }
        def closure(cur, time, limit, room, withnow):
            limitreal = int(limit)
            if room is None:
                cur.execute("SELECT events.begins, events.ends, events.name, rooms.name FROM events JOIN rooms ON events.room = rooms.id WHERE events.begins <= %s AND events.ends >= %s LIMIT %s", (time, time, limitreal))
                if cur.rowcount > 0:
                    for row in cur.fetchall():
                        value['after'].append({ 'begins': row[0], 'ends': row[1], 'name': row[2], 'room': row[3] })
            else:
                if withnow:
                    cur.execute("SELECT begins, ends, name FROM events WHERE room = %s AND begins <= %s AND ends >= %s LIMIT 1", (room, time, time))
                    if cur.rowcount > 0:
                        now = cur.fetchone()
                        if now is not None:
                            limitreal -= 1
                            value['now'] = { 'begins': now[0], 'ends': now[1], 'name': now[2], 'room': None }
                cur.execute("SELECT begins, ends, name FROM events WHERE room = %s AND begins >= %s LIMIT %s", (room, time, limitreal))
                if cur.rowcount > 0:
                    for row in cur.fetchall():
                        value['after'].append({ 'begins': row[0], 'ends': row[1], 'name': row[2], 'room': None })
        self.execute(closure, time, limit, room, withnow)
        return value
