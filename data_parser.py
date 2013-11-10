#!/usr/bin/env python

import time
import re

class DataParseError(Exception):
		pass

__DIVISISION__ = "West Coast Swing"
__TIMEFORMAT__ = u"%Y-%m-%d %H:%M:%S"
__ROLES__ = [ "leader", "follower" ]

# before 01.01.2012
# 0 < Novice < 20
# 0 < Intermediate < 25

# after 01.01.2012
# 0 < Novice < 15
# 0 < Intermediate < 30

class DEvent:
		def __init__(self, eventdict, role, division):
				self.name = eventdict["name"].replace("'","\\'")
				self.placement = eventdict["result"]
				self.points = int(eventdict["points"])
				self.start_date = time.strftime("%Y-%m-%d %H:%M:%S", time.strptime(eventdict["start_date"], __TIMEFORMAT__))
				self.end_date = time.strftime("%Y-%m-%d %H:%M:%S", time.strptime(eventdict["end_date"], __TIMEFORMAT__))
				self.location = eventdict["location"].replace("'","\'")
				self.role = role
				self.division = division
				self.tier = self._tier_calculator()

		def _tier_calculator(self):
				# example tier_calc[place][points]
				tier_calc = {
						"1" : { "5": 1, "10": 2, "15": 3, },
						"2" : { "4": 1, "8": 2, "12": 3, },
						"3" : { "3" : 1, "6" : 2, "10" : 3, },
						"4" : { "2" : 1, "4" : 2, "8" : 3, },
						"5" : { "1" : 1, "2" : 2, "6" : 3, },
						"f" : { "1" : "2 or 3" },
					}
				try:
						return tier_calc[str(self.placement).lower()][str(self.points)]
				except KeyError:
						return "%s/%s" % (str(self.placement).lower(),str(self.points))
				

class DDivision:
		def __init__(self, divisiondict):
				self.name = divisiondict["name"]
				if divisiondict["leader_points"] == divisiondict["follower_points"] and divisiondict["leader_points"] == 0:
								raise DataParseError("No valid points in this category")
				self.role = "leader" if divisiondict["leader_points"]!=0 else "follower"
				self.points = int(divisiondict[self.role+"_points"])
				self.placements = []
				for e in divisiondict[self.role+"_placements"]:
						self.placements.append(DEvent(e, self.role, self.name))

		def points_in_division(self):
				return int(self.points)




class WSDCDataParser:
		def __init__(self, indata):
				self.indata = indata
				self.name = self.indata["full_name"].replace("'","\\'")
				self.wcsid = int(self.indata["wscid"])
				self.results = None
				first_name_match = re.match(".*, (.*)", self.name)

				if first_name_match: self.first_name = first_name_match.groups()[0]
				else: self.first_name = ""
				last_name_match = re.match("(.*), .*", self.name)
				if last_name_match: self.last_name = last_name_match.groups()[0]
				else: self.last_name = ""

				for e in indata["results"]:
						if e["name"] == __DIVISISION__:
								self.results = e["divisions"]
								break
				if not self.results: raise DataParseError('No results for dancer: "%s"' % self.name)
				self.divisions = [ DDivision(div) for div in  self.results ]
				# NOTE: divisions are fixed set. It is not stable, but main of them: Newcomer,
				# Novice, Advanced and All-Star are stable
