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


def getpage(url, data=None, headers={}):
		if data: data = urllib.urlencode(data)
		#auth(config.login)
		#req = urllib2.urlopen(url)
		req = urllib2.Request(url, data, headers)
		response = urllib2.urlopen(req)
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

"""
create table dancers (
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
"""

def main():
		con = lite.connect('wsdc.sqlite')
		cur = con.cursor()
		#uid = act("get_id", "Puzanova")[0]['value']
		all_ids = act("get_id","")
		total = len(all_ids)
		curr = 0
		for e in all_ids:
				#name = 
				#act_list = act("get_id", name)
				#if len(act_list) > 1:
				#		for e in act_list:
				#				print e["label"]
						#sys.exit(0)
				#if len(act_list) == 0: continue
				curr += 1
				uid = e['value']
				dmatch = re.match("(.*) \(%s\)" % uid, e['label'])
				dname =  dmatch.groups()[0]
				first_name_match = re.match(".*, (.*)", dname)
				if first_name_match: first_name = first_name_match.groups()[0]
				else: first_name = ""
				last_name_match = re.match("(.*), .*", dname)
				if last_name_match: last_name = last_name_match.groups()[0]
				else: last_name = ""
				#print str(curr)+"/"+str(total)
				try:
						data = WSDCDataParser(act("get_history", uid))
				except DataParseError:
						continue
				p_list = []
				for d in data.divisions:
				#		print d.name, d.points_in_division()
						for p in d.placements:
								p_list.append(p)
				p_list.sort(cmp=p_sort)
				for p in p_list:
						query = "INSERT INTO dancers VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"
						cur.execute(query,
								(
										int(uid),
										first_name,
										last_name,
										p.role,
										p.name,
										p.placement,
										int(p.points),
										time.strftime("%Y-%m-%d %H:%M:%S", p.start_date),
										time.strftime("%Y-%m-%d %H:%M:%S", p.end_date),
										p.location,
										p.division,
										p.tier,
								))
						con.commit()
						# print p.placement, p.tier, p.division, p.name, time.strftime("%m/%Y", p.start_date)
		# http://swingdancecouncil.herokuapp.com/pages/dancer_search_by_fragment.json?term=She
		con.close()

if __name__ == '__main__':
		main()
