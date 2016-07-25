# coding: utf-8

from datetime import datetime
from string import Template
import psycopg2
from infopage import Infopage

class Master(object):
    pagetemplate = Template('''
            <div id="titlepane">
                <table>
                    <tr>
                        <td class="logo"><img src="logo.png" /></td>
                        <td class="title">$title</td>
                        <td class="clock">$time</td>
                    </tr>
                </table>
            </div>
            <div id="contentpane">
                <table>$content</table>
            </div>
    ''')
    rowtemplate = Template('''
                    <tr>
                        <td class="desc"><div class="cell">$description</div></td>
                        <td class="time">$start</td>
                    </tr>
    ''')
    def __init__(self):
        pass
    def generate(self, db, slideno):
        pass

class EventMaster(Master):
    def __init__(self, hasnow):
        self.hasnow = hasnow
    def generate(self, db, slideno, title):
        timeformat = db.setting('time_format')
        nowtemplate = db.setting('now_text')
        maxrows = db.setting('max_rows')
        now = datetime.now()
        content = ""
        slidedef = db.slide(slideno)
        if slidedef['name'] is not None:
            title = slidedef['name']
        if slidedef['maxrows'] is not None:
            maxrows = int(slidedef['maxrows'])
        if slidedef['room'] is not None:
            events = db.events(now, maxrows, slidedef['room'], self.hasnow)
            if events['now'] is not None:
                content += self.rowtemplate.substitute(description=events['now']['name'], start=nowtemplate)
            for event in events['after']:
                beginformat = event['begins'].strftime(timeformat)
                content += self.rowtemplate.substitute(description=event['name'], start=beginformat)
        nowformat = now.strftime(timeformat)
        return self.pagetemplate.substitute(title=title, time=nowformat, content=content)

class NowMaster(Master):
    rowtemplate = Template('''
                    <tr>
                        <td class="nowdesc"><div class="cell">$description</div></td>
                        <td class="room"><div class="$style">$start</div></td>
                    </tr>
    ''')
    def __init__(self):
        pass
    def generate(self, db, slideno, title):
        timeformat = db.setting('time_format')
        nowtemplate = db.setting('now_master_text')
        maxrows = db.setting('max_rows')
        now = datetime.now()
        content = ""
        if title is None:
            title = nowtemplate
        events = db.events(now, maxrows)
        for event in events['after']:
            if len(event['name']) > 14:
                content += self.rowtemplate.substitute(style="roomlong", description=event['name'], start=event['room'])
            else:
                content += self.rowtemplate.substitute(style="room", description=event['name'], start=event['room'])
        nowformat = now.strftime(timeformat)
        return self.pagetemplate.substitute(title=title, time=nowformat, content=content)

masters = [ EventMaster(True), EventMaster(False), NowMaster(), ]

def slide(req, slide):
    db = Infopage()
    db.loadconfig()
    with db:
		selector = db.select(slide)
		if selector['master'] is None:
			selector['master'] = 0
		if selector['master'] < len(masters):
			master = masters[selector['master']]
			return master.generate(db, selector['slide'], selector['title'])
