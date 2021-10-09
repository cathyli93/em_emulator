#!/usr/bin/python
# Filename: handoff_failure.py

import sys
import traceback
import random

file = ''

meas_report_stack = []
inter_meas_config = {}
intra_offset = None
cur_freq = -1
cur_cell = -1
cur_rss = [None, None]
after_reest = False
last_miss_cell = {}

# [-30, -5]
rsrq_to_snr = [-17.1,-18.2,-17,-16.6,-16.8,-16.4,-15.4,-14.6,-13.7,-12.4,-11.1,-9.9,-8.5,-7,-5.5,-3.8,-2.2,-0.5,1.7,3.5,5.3,6.3,7.5,9,10.4,10.8,10.6,11.1]

def get_saved_result(rsrq):
	global rsrq_to_snr

	if rsrq == 0:
		# if random.random() < 0.444:
		# 	return (-13.7,True)
		return (None,None)

	real_rsrq = int((rsrq + 1)/2 - 20)
	est_snr = 12
	if real_rsrq <= -3:
		est_snr = rsrq_to_snr[real_rsrq+30]
	if est_snr >= -14 and real_rsrq < -3:
		return (est_snr,True)

	return (est_snr,False)

# 1488308128.450830,serv rss,2300,44,-94,0
def print_last_miss_cell(fields=[]):
	global last_miss_cell

	allowed_gap = 0.5

	if not last_miss_cell:
		return

	res = 'Not decided'
	rsrp = None
	rsrq = None
	time = None
	if fields:
		time = float(fields[0])
		freq = int(fields[2])
		cell = int(fields[3])
		rsrp = int(fields[4])
		rsrq = int(fields[5])

		# print fields, last_miss_cell

	
		if fields and freq==last_miss_cell['targ_freq'] and cell==last_miss_cell['targ_cell'] and time - last_miss_cell['time'] < allowed_gap and last_miss_cell['serv_rsrp'] and last_miss_cell['offset'] != None:
			if rsrp > last_miss_cell['serv_rsrp'] + last_miss_cell['offset']:
				res = 'Saved'
			else:
				res = 'Not saved'

	last_miss_cell['targ_rsrp'] = rsrp
	last_miss_cell['targ_rsrq'] = rsrq
	last_miss_cell['res'] = res
	last_miss_cell['1st_meas_time'] = time
	print ','.join(['%s,%s'%(key,str(value)) for key,value in last_miss_cell.items()])
		# last_miss_cell = {'time':time,'serv_freq':cur_freq,'serv_rsrp':cur_rss[0],'serv_rsrq':cur_rss[1],'targ_freq':freq,'targ_cell':cellid,'offset':intra_offset}

	last_miss_cell.clear()


if __name__ == '__main__':
	# fout1 = open(sys.argv[2], 'a+')
	# fout2 = open(sys.argv[3], 'a+')
	with open(sys.argv[1], 'r') as f:
		for line in f:
			try:
				type_id, content = line.split(':')
				if type_id != '[rrc]':
					if type_id[-3:] == 'txt':
						file = type_id
					continue
				
				type_id = type_id.strip()
				content = content.strip()

				fields = content.split(',')
				time = float(fields[0])

				# # [rrc]:1564509164.3,Measurement report,1850,187,-92,16,a3,100,1850,83 -89 19 2,0.5,0,1,None,8
				# if fields[1] == 'Freq':
				# 	cur_freq = int(fields[2])

				# 1488308128.450830,serv rss,2300,44,-94,0
				if fields[1] == 'serv rss':
					print_last_miss_cell(fields)

					cur_rss[0] = int(fields[4])
					cur_rss[1] = int(fields[5])
					cur_freq = int(fields[2])
					cur_cell = int(fields[3])

				if fields[1] == 'Measurement report':
					# measurement report is followed by 'serv rss' (duplicate), so not responsible for updating current rss
					# filter measurements for monitoring
					if fields[6] not in ['a3', 'a4', 'a5']:
						continue

					if fields[6] == 'a3' and int(fields[-3]) < 0:
						continue

					if fields[6] == 'a5' and int(fields[-3]) - int(fields[-2]) >= 30:
						continue

					n_cells = {}
					for i in range(9, len(fields) - 5):
						if not fields[i]:
							continue
						details = fields[i].split()
						if details[0]:
							n_cells[int(details[0])] = (int(details[1]), int(details[2]), int(details[3]))
					meas_report_stack.append({'time':float(time), 'freq':int(fields[2]), 'type':fields[6], 'meas_freq':int(fields[8]), 'neighbor':n_cells, 'rsrp':int(fields[4]), 'rsrq':int(fields[5]), 'ttt':int(fields[7]), 'thresh1':int(fields[-3]), 'thresh2':'None' if fields[-2] == 'None' else int(fields[-2])})

					# cur_freq = int(fields[2])

				# [rrc]:1565527724.94,Reestablish with,1825,244,handover_failure
				if fields[1] == 'Reestablish with':
					freq = int(fields[2])
					cellid = int(fields[3])
					# print 'get freq, cell id'

					# print freq, cellid

					if fields[-1] == 'handover_failure' or (freq == cur_freq and cellid == cur_cell):
						cur_freq = freq
						cur_cell = cellid
						meas_report_stack = []
						inter_meas_config.clear()
						continue

					last_same_report = False

					# diff_cell_id = None
					# diff_cell_freq = None
					# diff_serv_rss = None
					# diff_neig_rss = None
					# diff_report_time = None
					# diff_report_type = None

					last_diff_report = False

					# while meas_report_stack:
					# 	report = meas_report_stack[-1]
					for report in meas_report_stack:
						# print freq, cellid, report['type'], report['meas_freq'], report['neighbor']
						if report['type'] in ['a3','a4','a5'] and freq == report['meas_freq'] and cellid in report['neighbor']:
							last_same_report = True
							break

						# elif report['type'] in ['a3', 'a4', 'a5'] and report['neighbor'] and cur_freq != report['meas_freq']:
						elif report['type'] in ['a3', 'a4', 'a5'] and report['neighbor']:
							last_diff_report = True


					if not last_same_report and not last_diff_report:
						inter_meas_type = ''
						if cur_freq != freq:
							inter_meas_type = 'Not configured'
							if freq in inter_meas_config:
								inter_meas_type = inter_meas_config[freq]

						if inter_meas_type == 'Not configured':
							last_miss_cell = {'time':time,'serv_freq':cur_freq,'serv_rsrp':cur_rss[0],'serv_rsrq':cur_rss[1],'targ_freq':freq,'targ_cell':cellid,'offset':intra_offset}
						else:
							print_last_miss_cell()
							last_miss_cell.clear()

					else:
						print_last_miss_cell()
						last_miss_cell.clear()

					meas_report_stack = []
					inter_meas_config.clear()
					intra_offset = None

					cur_freq = freq
					cur_cell = cellid
					cur_rss = [None, None]					

				# [rrc]:1564509145.58,Handoff,1850,123,1850,187,91
				if fields[1] == 'Handoff':
					cur_freq = int(fields[-3])
					cur_cell = int(fields[-2])
					cur_rss = [None, None]

					meas_report_stack = []
					inter_meas_config.clear()
					intra_offset = None

					print_last_miss_cell()
					last_miss_cell = {}

				# 1565519752.6,ConnectionSetup,2452,139
				if fields[1] == 'ConnectionSetup':
					cur_freq = int(fields[-2])
					cur_cell = int(fields[-1])
					cur_rss = [None, None]

					meas_report_stack = []
					inter_meas_config.clear()
					intra_offset = None

					print_last_miss_cell()
					last_miss_cell = {}

				# 1565519742.57,ConnectionRelease
				if fields[1] == 'ConnectionRelease':
					meas_report_stack = []
					inter_meas_config.clear()
					intra_offset = None

					print_last_miss_cell()
					last_miss_cell = {}

				# 1540979550.092899,Reconfig complete,38400,295
				if fields[1] == 'Reconfig complete':
					cur_freq = int(fields[-2])
					cur_cell = int(fields[-1])

				# 1564507109.41,Meas Config,1825,161,1825 a3 1 None 0 148.1 180.1 159.1
				if fields[1] == 'Meas Config':
					inter_meas_config.clear()
					for i in range(4, len(fields)):
						content = fields[i].split()
						freq = int(content[0])
						# serv_offset = 0
						if freq == int(fields[2]):
							if content[1] == 'a3':
								intra_offset = int(content[2])
							continue

						inter_meas_config[freq] = content[1]

			except:
				print "Unexpected error:", sys.exc_info()[0], file, fields, traceback.format_exc()
				continue

		print_last_miss_cell()
