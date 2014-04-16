#!/usr/bin/env python

import urllib, urllib2
import cookielib
import os
from data_parser import WSDCDataParser, DataParseError
import json
import sys
import time
import sqlite3 as lite
import re
import httplib

DEBUG=True

class Counter:
		def __init__(self, initval=0):
				self.counter=initval

		def inc(self):
				self.counter +=1
				return self.counter

		def dec(self):
				self.counter -=1
				return self.counter

		def val(self):
				return self.counter

def getpage(url, data=None, headers={}):
		if data: data = urllib.urlencode(data)
		#auth(config.login)
		#req = urllib2.urlopen(url)
		response = False
		req = urllib2.Request(url, data, headers)
		while not response:
				try:
						response = urllib2.urlopen(req)
				except:
						print "sleep"
						time.sleep(1)
		return json.loads(response.read())

def act(action, param):
		headers = { "User-Agent" :"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36" }
		base_URL="http://swingdancecouncil.herokuapp.com/pages/"
		actions = {
						"get_id": "dancer_search_by_fragment.json?term=%s",
						"get_history":"dancer_point_history.json?wscid=%s",
						}
		return getpage(urllib.basejoin(base_URL, actions[action] % urllib.quote(str(param))), headers=headers)

def p_sort(a,b):
		if a.start_date > b.start_date: return -1
		elif a.start_date < b.start_date: return 1
		else: return 0


def prepare_table(cursor, table, temporary=False):
		istemporary = "temporary"
		if not temporary: istemporary = ""
		create_table = """
		create %s table %s (
				uid integer,
				first_name varchar,
				last_name varchar,
				role varchar,
				ename varchar,
				placement varchar,
				points integer,
				start_date datetime,
				end_date datetime,
				location varchar,
				division varchar,
				tier varchar
		);
		""" % (istemporary, table)
		drop_table = "drop table if exists %s;" % table

		cursor.execute(drop_table)
		cursor.execute(create_table)

def add_entries(cursor, table, uid):
		try:
				data = WSDCDataParser(act("get_history", uid))
		except DataParseError:
				return None
		p_list = []
		for d in data.divisions:
				for p in d.placements:
						p_list.append(p)
		p_list.sort(cmp=p_sort)
		for p in p_list:
				query = "INSERT INTO %s VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);" % table
				cursor.execute(query,
						(
								data.wscid,
								data.first_name,
								data.last_name,
								p.role,
								p.name,
								p.placement,
								p.points,
								p.start_date,
								p.end_date,
								p.location,
								p.division,
								p.tier,
						))

def sync_db():
		con = lite.connect('wsdc.tmp.sqlite')
		cur = con.cursor()
		prepare_table(cur, "dancers")
		all_ids = act("get_id","")
		total = len(all_ids)
		if DEBUG:
				print total
		c = Counter()
		for e in all_ids:
				uid = e['value']
				if DEBUG:
						if c.inc()%10 == 0:
								print "% 7d/%d" % (c.counter,total)
				if not add_entries(cur, 'dancers', uid): continue
		con.commit()
		con.close()
		os.rename("wsdc.tmp.sqlite", "wsdc.sqlite");

def main():
		os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))
		dcore_lim = 100;
		con = lite.connect("wsdc.sqlite")
		cur = con.cursor()
		try:
				last_event = cur.execute("select ename,location,start_date from dancers order by start_date desc limit 1").fetchall()[0]
				inlocal = set([ e[0] for e in cur.execute("select distinct uid from dancers").fetchall()])
				inremote = set( int(e['value']) for e in act("get_id","") )
				# if there new ids in database, it definitely was updated
				difflen = len(inlocal.difference(inremote))
		except (lite.OperationalError, IndexError):
				prepare_table(cur, "dancers", temporary=False)
				difflen = 1
		# assuming that usual event visitors in common all the same people,
		# there is a HUGE probability they are getting points
		# so taking 200 most-recent-points-gainers we can predict they will gain more
		# points in consequent events. And this why we shouldn't check all the database, only
		# some dancers
		if difflen == 0:
				dcore = cur.execute("select distinct uid from dancers order by start_date desc limit %s;" % dcore_lim).fetchall()
				prepare_table(cur, "dancers_tmp", temporary=False)
				c = Counter()
				for uid in dcore:
						#print "% 7d/%d" % (c.inc(),dcore_lim)
						if not add_entries(cur, 'dancers_tmp', uid[0]): continue
				con.commit()
				new_events = cur.execute("select count(*) from dancers_tmp where start_date > '%s'" % last_event[2]).fetchall()[0][0]
				if new_events > 0:
						print "New events, syncing db"
						con.close()
						sync_db()
						print "Sync done!"
				else:
						print "No new events"

		else:
				print "Non-zero difflen, syncing db"
				con.close()
				sync_db()
				print "Sync done!"
		#sync_db()


if __name__ == '__main__':
		main()
