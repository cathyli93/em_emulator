#!/usr/bin/python
# Filename: handoff_failure.py

import sys
import traceback
import random

from ast import literal_eval

meas_report_stack = []
inter_meas_config = {}

total_failure = 0
inter_failure = 0
intra_failure = 0
no_meas = 0
with_meas = 0

cur_freq = None
cur_cell = None

file = ''

rsrq_to_snr = [-17.1,-18.2,-17,-16.6,-16.8,-16.4,-15.4,-14.6,-13.7,-12.4,-11.1,-9.9,-8.5,-7,-5.5,-3.8,-2.2,-0.5,1.7,3.5,5.3,6.3,7.5,9,10.4,10.8,10.6,11.1]

def get_saved_result(rsrq):
	global rsrq_to_snr

	try:

		if rsrq == 0:
		# if random.random() < 0.444:
		# 	return (-13.7,True)
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

def process_rrc_ota(msg):
	# type_id = type_id.strip()
	global meas_report_stack, inter_meas_config, cur_freq, cur_cell, file

	meta = msg
	info = {}
	info_start = msg.find('{')
	if info_start >= 0:
		info_end = msg.rfind('}')
		meta = msg[:info_start]
		info = literal_eval(msg[info_start:info_end+1])

	headers = meta.strip(',').split(',')
	time = float(headers[0])

	tag = headers[1]

	# 1488308128.450830,serv rss,2300,44,-94,0
	# if tag == 'serv rss':
	# 	cur_freq = int(fields[2])
	# 	cur_cell = int(fields[3])

	if tag == 'Measurement report':
		# filter measurements for monitoring
		if info['event_type'] not in ['a3', 'a4', 'a5']:
			return

		if info['event_type'] == 'a3' and info['threshold1'] < 0:
			return

					# if fields[6] == 'a5' and int(fields[-3]) - int(fields[-2]) >= 30:
					# 	continue

		info['time'] = time 
		info['freq'] = int(headers[2])
		info['cid'] = int(headers[3])
		meas_report_stack.append(info)
			
		# meas_report_stack.append({'time':float(time), 'freq':int(fields[2]), 'type':fields[6], 'meas_freq':int(fields[8]), 'neighbor':n_cells, 'rsrp':int(fields[4]), 'rsrq':int(fields[5]), 'ttt':int(fields[7]), 'thresh1':int(fields[-3]), 'thresh2':'None' if fields[-2] == 'None' else int(fields[-2])})

		# {"serving_rsrp":p_rsrp,"serving_rsrq":p_rsrq,"event_type":meas_report[1].event_list[0].type, "time_to_trigger":meas_report[1].time_to_trigger, "measure_freq":meas_report[0].freq, "hyst":meas_report[1].hyst,"serving_offset":serv_offset, "threshold1": meas_report[1].event_list[0].threshold1, "threshold2": meas_report[1].event_list[0].threshold2, "results":neigh_cell_list}

	# [rrc]:1565527724.94,Reestablish with,1825,244,handover_failure
	if tag == "Reestablish":
		freq = int(headers[2])
		cellid = int(headers[3])
		if freq == cur_freq and cellid == cur_cell:
			cur_freq = freq
			cur_cell = cellid
			meas_report_stack = []
			inter_meas_config = {}

	if tag == 'Handover failure':
		freq = int(headers[2])
		cellid = int(headers[3])

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
			print(file + "," + str(time) + ",handover failure: loss," + "[disruption]" + "," + str(last_same_report["is_saved"]) + "," + str(last_same_report))

		else:
						# no_meas += 1
			if last_diff_report:
							# if not last_diff_report['thresh2']:
							# 	last_diff_report['thresh2'] = 'None'
				report_list = last_diff_report['targets']
				report_str = ','.join(['%s,%s,%s'%(str(x), str(report_list[x][0]), str(report_list[x][1])) for x in report_list])
				last_diff_report['targets'] = report_str

				print(file + "," + str(time) + ",handover failure: loss," + "[disruption]" + "," + str(last_diff_report["is_saved"]) + "," + str(last_diff_report))

				# print(file + ',re-est with diff report,' + str(time) + ',' + ','.join(['%s,%s'%(x, str(last_diff_report[x])) for x in sorted(last_diff_report.keys())]))

			else:
				inter_meas_type = ''
				if cur_freq != freq:
					inter_meas_type = 'Not configured'
					if freq in inter_meas_config:
						inter_meas_type = inter_meas_config[freq]
								
				print(file + ',re-est without report,serv_freq,' + str(cur_freq) + ',targ_freq,' + str(freq) + ',targ_cell,' + str(cellid) + ',' + inter_meas_type)
							
							# print file + ',re-est with non-reported cell,' + str(time) + ',' + str(cur_freq) + ',' + str(cur_cell) + ',' + str(freq) + ',' + str(cellid)
							 # is_configured_inter_freq


		inter_meas_config = {}
		meas_report_stack = []
		cur_freq = freq
		cur_cell = cellid
		# total_failure += 1
					
	# [rrc]:1564509145.58,Handoff,1850,123,1850,187,91
	if tag == 'Handover':
		cur_freq = int(headers[4])
		cur_cell = int(headers[5])
		meas_report_stack = []
		inter_meas_config = {}

	# [rrc]:1565519752.6,ConnectionSetup,2452,139
	if tag == 'Connection setup':
		cur_freq = int(headers[2])
		cur_cell = int(headers[3])
		meas_report_stack = []
		inter_meas_config = {}

	# 			# [rrc]:1565519742.57,ConnectionRelease
	# if tag == 'ConnectionRelease':
	# 	meas_report_stack = []
	# 	inter_meas_config = {}
	# 				# print cur_freq, cur_cell

	# 			# [rrc]:1565519758.24,Reconfig complete,1825,6
	# if tag == 'Reconfig complete':
	# 	cur_freq = int(fields[-2])
	# 	cur_cell = int(fields[-1])

	# [rrc]:1564507109.41,Meas Config,1825,161,1825 a3 1 None 0 148.1 180.1 159.1
	if tag == 'Meas Config':
		inter_meas_config.clear()
		# info = 
		for item in info["info"]:
			freq = item["freq"]
			if freq == int(headers[2]):
				continue

			if item["event_type"] == 'a3' and item["threshold1"] < 0:
				continue

			inter_meas_config[freq] = item["event_type"]

						# thresh2 = int(fields[i+3]) if fields[i+1] == 'a5' else None
						# inter_meas_config[inter_freq] = (fields[i+1], int(fields[i+2]), thresh2)

if __name__ == '__main__':
	# fout1 = open(sys.argv[2], 'a+')
	# fout2 = open(sys.argv[3], 'a+')
	file = sys.argv[1]
	with open(sys.argv[1], 'r') as f:
		for line in f:
			try:
				type_id = line.split(':')[0]
				if type_id == "rrc-ota":
					process_rrc_ota(line[8:])

				# if type_id != 'rrc-ota':
				# 	if type_id[-3:] == 'txt':
				# 		file = type_id
				# 	continue

			except:
				print("Unexpected error:", sys.exc_info()[0], file, line, traceback.format_exc())
				continue

			# except IndexError as e:
			# 	print file, fields, traceback.format_exc()
			# 	continue

	# print sys.argv[1], total_failure, with_meas, no_meas, intra_failure, inter_failure
	# fout2.write(','.join([sys.argv[1], str(total_failure), str(with_meas), str(no_meas), str(intra_failure), str(inter_failure)]) + '\n')

	# fout1.close()
	# fout2.close()