#!/usr/bin/python

import os
import sys
import logging

from mobile_insight.monitor import OfflineReplayer
from mobility_trace_parser import MobilityParser

from mobile_insight.analyzer.analyzer import *

from time import mktime
import datetime


if __name__ == "__main__":
	if len(sys.argv) < 2:
		print('Usage: python3', sys.argv[0], '<one mi2log/mi3log file>')
	src = OfflineReplayer()
	src.set_input_path(sys.argv[1])

	lte_mobility_analyzer = MobilityParser()
	lte_mobility_analyzer.set_source(src)

	src.run()
	