#!/usr/bin/python
# Filename: handoff_failure.py

import os, sys
import traceback
import random
import logging

from ast import literal_eval

logger=logging.getLogger() 
logger.setLevel(logging.INFO)

consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setLevel(logging.INFO) 

logger.addHandler(consoleHandler)

file = ''

meas_report_stack = []
inter_meas_config = {}

# total_failure = 0
# inter_failure = 0
# intra_failure = 0
# no_meas = 0
# with_meas = 0

cur_freq = None
cur_cell = None

intra_offset = None
last_miss_cell = {}
cur_rss = [None, None]
serv_rss = {}

rsrq_to_snr = [-17.1,-18.2,-17,-16.6,-16.8,-16.4,-15.4,-14.6,-13.7,-12.4,-11.1,-9.9,-8.5,-7,-5.5,-3.8,-2.2,-0.5,1.7,3.5,5.3,6.3,7.5,9,10.4,10.8,10.6,11.1]

def get_saved_result(rsrq):
	global rsrq_to_snr

	try:
		if rsrq == 0:
			return (None,False)

		real_rsrq = int((rsrq + 1)/2 - 20)
		est_snr = 12
		if real_rsrq <= -3:
			est_snr = rsrq_to_snr[real_rsrq+30]
		if est_snr >= -14 and real_rsrq < -3:
			return (est_snr,True)
		return (est_snr,False)
	except:
		print("Error:",rsrq)
		return(rsrq_to_snr[0], False)

def print_last_miss_cell(fields=[]):
	global last_miss_cell

	allowed_gap = 0.5

	if not last_miss_cell:
		return

	# res = 'Not decided'
	rsrp = None
	rsrq = None
	time = None
	if fields:
		time = float(fields[0])
		freq = int(fields[2])
		cell = int(fields[3])
		rsrp = int(fields[4])
		rsrq = int(fields[5])

		# missed cells: not measured but available within the gap
		if fields and freq==last_miss_cell['targ_freq'] and cell==last_miss_cell['targ_cell'] and time - last_miss_cell['time'] < allowed_gap:
			res = False
			# can be judged based on existing information
			if last_miss_cell['serv_rsrp'] is not None and last_miss_cell['offset'] is not None:
				if rsrp > last_miss_cell['serv_rsrp'] + last_miss_cell['offset']:
					res = True

			logger.info(file + "," + str(last_miss_cell["time"]) + ",handover-failure: missed-cell," + str(last_miss_cell["time_before_disconnection"]) + "," + str(last_miss_cell["serv_freq"]) + "," + str(last_miss_cell["serv_cell"]) + "," + str(last_miss_cell["targ_freq"]) + "," + str(last_miss_cell['targ_cell']) + "," + str(res))
			
			last_miss_cell['targ_rsrp'] = rsrp
			last_miss_cell['targ_rsrq'] = rsrq
			last_miss_cell['is_saved'] = res
			last_miss_cell['1st_meas_time'] = time
			logger.info("[debug]" + file + "," + str(last_miss_cell["time"]) + ",handover-failure: missed-cell," + "," + str(res) + "," + str(last_miss_cell))
	
	else:
		logger.info(file + "," + str(time) + ",handover-failure: coverage hole," + str(last_miss_cell["time_before_disconnection"]) + "," + str(last_miss_cell["serv_freq"]) + "," + str(last_miss_cell["serv_cell"]) + "," + str(last_miss_cell["targ_freq"]) + "," + str(last_miss_cell['targ_cell']) + ",False")

	last_miss_cell.clear()

def process_rss(msg):
	global serv_rss, last_miss_cell, cur_freq, cur_cell, file
	headers = msg.strip().split(',')
	time = float(headers[0])
	freq = int(headers[1])
	cell = int(headers[2])
	rsrp = float(headers[3])

	serv_rss[(freq,cell)] = (time, rsrp)
	if not cur_freq:
		cur_freq = freq 
		cur_cell = cell

	if last_miss_cell and freq == last_miss_cell["targ_freq"] and cell == last_miss_cell["targ_cell"]:
		# missed cell
		if time - last_miss_cell['time_before_disconnection'] <= 1:
			res = (last_miss_cell["serv_rsrp"] and rsrp > last_miss_cell["serv_rsrp"])
			logger.info(file + "," + str(last_miss_cell["time"]) + ",handover-failure: missed-cell," + str(last_miss_cell["time_before_disconnection"]) + "," + str(last_miss_cell["serv_freq"]) + "," + str(last_miss_cell["serv_cell"]) + "," + str(last_miss_cell["targ_freq"]) + "," + str(last_miss_cell['targ_cell']) + "," + str(res))

		else:
			logger.info(file + "," + str(time) + ",handover-failure: coverage hole," + str(last_miss_cell["time_before_disconnection"]) + "," + str(last_miss_cell["serv_freq"]) + "," + str(last_miss_cell["serv_cell"]) + "," + str(last_miss_cell["targ_freq"]) + "," + str(last_miss_cell['targ_cell']) + ",False")

		last_miss_cell.clear()

	# if tag == "Measurement serving":
	# print_last_miss_cell(headers)

	# cur_rss[0] = int(headers[4])
	# cur_rss[1] = int(headers[5])
	# cur_freq = int(headers[2])
	# cur_cell = int(headers[3])



def process_rrc_ota(msg):
	# type_id = type_id.strip()
	global meas_report_stack, inter_meas_config, cur_freq, cur_cell, file, last_miss_cell

	meta = msg
	info = {}
	info_start = msg.find('{')
	if info_start >= 0:
		info_end = msg.rfind('}')
		meta = msg[:info_start]
		info = literal_eval(msg[info_start:info_end+1])

	headers = meta.strip().strip(',').split(',')
	time = float(headers[0])

	tag = headers[1]

	# 1488308128.450830,serv rss,2300,44,-94,0
	# if tag == 'serv rss':
	# 	cur_freq = int(fields[2])
	# 	cur_cell = int(fields[3])

	if tag == "Measurement serving":
		cur_freq = int(headers[2])
		cur_cell = int(headers[3])

	if tag == 'Measurement report':
		# print_last_miss_cell()
		cur_freq = int(headers[2])
		cur_cell = int(headers[3])

		if info['event_type'] not in ['a3', 'a4', 'a5']:
			return

		if info['event_type'] == 'a3' and info['threshold1'] < 0:
			return

		if info['event_type'] == 'a5' and info['threshold1'] - info['threshold2'] >= 30:
			return

		info['time'] = time 
		info['freq'] = int(headers[2])
		info['cid'] = int(headers[3])
		meas_report_stack.append(info)

		# cur_freq = int(headers[2])
		# cur_cell = int(headers[3])
		# cur_rss[0] = info['serving_rsrp']
		# cur_rss[1] = info['serving_rsrq']
			
		# meas_report_stack.append({'time':float(time), 'freq':int(fields[2]), 'type':fields[6], 'meas_freq':int(fields[8]), 'neighbor':n_cells, 'rsrp':int(fields[4]), 'rsrq':int(fields[5]), 'ttt':int(fields[7]), 'thresh1':int(fields[-3]), 'thresh2':'None' if fields[-2] == 'None' else int(fields[-2])})

		# {"serving_rsrp":p_rsrp,"serving_rsrq":p_rsrq,"event_type":meas_report[1].event_list[0].type, "time_to_trigger":meas_report[1].time_to_trigger, "measure_freq":meas_report[0].freq, "hyst":meas_report[1].hyst,"serving_offset":serv_offset, "threshold1": meas_report[1].event_list[0].threshold1, "threshold2": meas_report[1].event_list[0].threshold2, "results":neigh_cell_list}

	# [rrc]:1565527724.94,Reestablish with,1825,244,handover_failure
	if tag == "Reestablish":
		# print_last_miss_cell()

		# if freq == cur_freq and cellid == cur_cell:
		cur_freq = int(headers[2])
		cur_cell = int(headers[3])
		meas_report_stack = []
		inter_meas_config = {}

		last_miss_cell.clear()

			# cur_rss = [None, None]
			# intra_offset = None

	if tag == 'Handover failure':
		# logger.info("[warning]" + file + "," + "handover-failure" + "," + str(headers))
		# print_last_miss_cell()

		freq = int(headers[2])
		cellid = int(headers[3])

		last_miss_cell.clear()

		last_same_report = None
		last_diff_report = None

		for report in meas_report_stack:
			if report['event_type'] in ['a3','a4','a5'] and freq == report['measure_freq'] and cellid in report['results']:
				if not last_same_report:
					est_snr, saved = get_saved_result(report['serving_rsrq'])

					last_same_report = {'serv_freq':report['freq'], 
					'serv_cell':report['cid'], 
					'serv_rsrp':report['serving_rsrp'], 
					'serv_rsrq':report['serving_rsrq'], 
					'est_snr':est_snr, 
					'targ_freq':report['measure_freq'], 
					'targ_rsrp':report['results'][cellid][0], 
					'targ_rsrq':report['results'][cellid][1], 
					'type':report['event_type'], 
					'time':report['time'], 
					'thresh1':report['threshold1'], 
					'thresh2':report['threshold2'],
					'is_saved':saved}

						# elif report['type'] in ['a3', 'a4', 'a5'] and report['neighbor'] and cur_freq != report['meas_freq']:
			elif report['event_type'] in ['a3', 'a4', 'a5'] and report['results']:
				if not last_diff_report:
					est_snr, saved = get_saved_result(report['serving_rsrq'])

					# diff_cell_id = report['results'].keys()[0]

					last_diff_report = {'serv_freq':report['freq'],
					'serv_cell':report['cid'],
					'serv_rsrp':report['serving_rsrp'], 
					'serv_rsrq':report['serving_rsrq'],
					'est_snr':est_snr, 
					'targ_freq': report['measure_freq'],
					'type':report['event_type'],
					'time':report['time'],
					'targets':report['results'], 
					'thresh1':report['threshold1'], 
					'thresh2':report['threshold2'],
					'is_saved':saved}

		if last_same_report:
			logger.info(file + "," + str(time) + ",handover-failure: loss," + str(headers[4]) + "," + str(last_same_report["serv_freq"]) + "," + str(last_same_report["serv_cell"]) + "," + str(freq) + "," + str(cellid) + "," + str(last_same_report["is_saved"]))

			logger.debug("[debug]" + file + "," + str(time) + ",handover-failure: loss," + "," + str(last_same_report["is_saved"]) + "," + str(last_same_report))

		elif last_diff_report:
			report_list = last_diff_report['targets']
			report_str = ','.join(['%s,%s,%s'%(str(x), str(report_list[x][0]), str(report_list[x][1])) for x in report_list])
			last_diff_report['targets'] = report_str

			logger.info(file + "," + str(time) + ",handover-failure: loss," + str(headers[4]) + "," + str(last_diff_report["serv_freq"]) + "," + str(last_diff_report["serv_cell"]) + "," + str(freq) + "," + str(cellid) + "," + str(last_diff_report["is_saved"]))
			logger.debug("[debug]" + file + "," + str(time) + ",handover-failure: loss," + "," + str(last_diff_report["is_saved"]) + ","  + str(last_diff_report))

		else:
			# inter_meas_type = ''
			# if 
			# 	inter_meas_type = 'Not configured'
			# 	if freq in inter_meas_config:
			# 		inter_meas_type = inter_meas_config[freq]

			if cur_freq != freq and freq not in inter_meas_config:
				rss_time, rss_val = serv_rss[(cur_freq,cur_cell)]

				last_miss_cell = {'time':time,'serv_freq':cur_freq,'serv_cell':cur_cell,'serv_rsrp':rss_val,'targ_freq':freq,'targ_cell':cellid,'offset':intra_offset,"time_before_disconnection":rss_time}
				logger.debug("[debug]" + str(last_miss_cell))

			else:
				logger.info(file + "," + str(time) + ",handover-failure: coverage hole," + str(headers[4]) + "," + str(cur_freq) + "," + str(cur_cell) + "," + str(freq) + "," + str(cellid) + ",False")
					# print("[debug]" + file + "," + str(time) + ",handover-failure: coverage hole,")
					# print_last_miss_cell()
					# last_miss_cell.clear()

		inter_meas_config = {}
		meas_report_stack = []
		cur_freq = freq
		cur_cell = cellid

		# cur_rss = [None, None]
		# intra_offset = None
					
	# [rrc]:1564509145.58,Handoff,1850,123,1850,187,91
	if tag == 'Handover':
		# print_last_miss_cell()

		logger.info(file + "," + str(time) + ",handover," + str(headers[6]) + "," + str(cur_freq) + "," + str(cur_cell) + "," + str(headers[4]) + "," + str(headers[5]))

		cur_freq = int(headers[4])
		cur_cell = int(headers[5])
		meas_report_stack = []
		inter_meas_config = {}

		# last_miss_cell.clear()

		# cur_rss = [None, None]
		# intra_offset = None

	# [rrc]:1565519752.6,ConnectionSetup,2452,139
	if tag == 'Connection setup':
		# if not (last_miss_cell and cur_freq == int(headers[2]) and cur_cell == int(headers[3])):
		# 	print_last_miss_cell()
		# 	intra_offset = None

		cur_freq = int(headers[2])
		cur_cell = int(headers[3])
		meas_report_stack = []
		inter_meas_config = {}

		# last_miss_cell.clear()

		# cur_rss = [None, None]

	# [rrc]:1564507109.41,Meas Config,1825,161,1825 a3 1 None 0 148.1 180.1 159.1
	if tag == 'Meas Config':
		# print_last_miss_cell()

		cur_freq = int(headers[2])
		cur_cell = int(headers[3])

		inter_meas_config.clear() 
		for item in info["info"]:
			freq = item["freq"]
			if freq == int(headers[2]):
				# if item["event_type"] == "a3":
				# 	intra_offset = item["threshold1"]
				continue

			if item["event_type"] == 'a3' and item["threshold1"] < 0:
				continue

			if item["event_type"] == 'a5' and item["threshold1"] - item["threshold2"] >= 30:
				continue

			inter_meas_config[freq] = item["event_type"]


if __name__ == '__main__':

	files_to_process = []
	for root, dirs, files in os.walk(sys.argv[1]):
		for f in files:
			if f.endswith(".mi2log.txt") or f.endswith(".qmdl.txt"):
				# if f >= "mobility_diag_log_20190811_1101211565492481444.mi2log.txt" and f <= 
				path = os.path.abspath(os.path.join(root, f))
				files_to_process.append(path)

	files_to_process.sort()
	for f in files_to_process:
		file = f

		with open(f, 'r') as lines:
			for line in lines:
				try:
					type_id = line.split(':')[0]
					if type_id == "rrc-ota":
						process_rrc_ota(line[8:])
					if type_id == "rss":
						process_rss(line[4:])

				except:
					print("Unexpected error:", sys.exc_info()[0], file, line, traceback.format_exc())
					continue

			print_last_miss_cell()
