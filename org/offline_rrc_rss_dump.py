#!/usr/bin/python

import os
import sys
import logging

from mobile_insight.monitor import OfflineReplayer
from mobility_mngt import MobilityMngt2

from mobile_insight.analyzer.analyzer import *

from time import mktime
import datetime

def datetime2unixts(s):
    # dt=datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")
    # return time.mktime(dt.timetuple()) + (dt.microsecond / 1000000.0)
    return mktime(s.timetuple()) + s.microsecond * 1.0 * 1e-6

class LteRssAnalyzer(Analyzer):
	def __init__(self):
		Analyzer.__init__(self)

		self.add_source_callback(self.__msg_callback)

		self.sample = None

	def set_source(self, source):
		Analyzer.set_source(self, source)

		source.enable_log("LTE_PHY_Connected_Mode_Intra_Freq_Meas")

	def __msg_callback(self, msg):
		if msg.type_id == "LTE_PHY_Connected_Mode_Intra_Freq_Meas":
			self.call_back_intra_meas(msg)

	# {'Serving Physical Cell ID': 276, 'Number of Detected Cells': 0, 'log_msg_len': 52, 'E-ARFCN': 1850, 'timestamp': datetime.datetime(2019, 8, 11, 4, 34, 38, 180111), 'type_id': 'LTE_PHY_Connected_Mode_Intra_Freq_Meas', 'Number of Neighbor Cells': 1, 'Version': 4, 'RSRP(dBm)': -103.3125, 'RSRQ(dB)': -13.5625, 'Detected Cells': [], 'Neighbor Cells': [{'RSRP(dBm)': -105.25, 'Physical Cell ID': 190, 'RSRQ(dB)': -14.6875}], 'Sub-frame Number': 711, 'Serving Cell Index': 'PCell'}
	def call_back_intra_meas(self, msg):
		log_item = msg.data.decode()
		timestamp = datetime2unixts(log_item['timestamp'])
		cell = log_item['Serving Physical Cell ID']
		freq = log_item['E-ARFCN']
		rsrp = log_item['RSRP(dBm)']
		rsrq = log_item['RSRQ(dB)']
		print '[rss]:' + str(timestamp) + ',serving,' + str(freq) + ',' + str(cell) + ',' + str(rsrp) + ',' + str(rsrq)


if __name__ == "__main__":
	if len(sys.argv) < 2:
		print 'Usage: python', sys.argv[0], '{one mi2log/mi3log file}'
	src = OfflineReplayer()
	src.set_input_path(sys.argv[1])

	lte_rss_analyzer = LteRssAnalyzer()
	lte_rss_analyzer.set_source(src)

	lte_mobility_analyzer = MobilityMngt2()
	lte_mobility_analyzer.set_source(src)

	src.run()
	