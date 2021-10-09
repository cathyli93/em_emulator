#!/usr/bin/python
# Filename: handoff_failure.py

import sys
import traceback
import random

meas_report_stack = []
inter_meas_config = {}

total_failure = 0
inter_failure = 0
intra_failure = 0
no_meas = 0
with_meas = 0

cur_freq = -1
cur_cell = -1

file = ''

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

				# 1488308128.450830,serv rss,2300,44,-94,0
				if fields[1] == 'serv rss':
					cur_freq = int(fields[2])
					cur_cell = int(fields[3])

				if fields[1] == 'Measurement report':
					# filter measurements for monitoring
					if fields[6] not in ['a3', 'a4', 'a5']:
						continue

					if fields[6] == 'a3' and int(fields[-3]) < 0:
						continue

					# if fields[6] == 'a5' and int(fields[-3]) - int(fields[-2]) >= 30:
					# 	continue

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
						inter_meas_config = {}
						continue

					# fail_type = ''
					# is_configured_inter_freq = ''
					# if freq == cur_freq:
					# 	intra_failure += 1
					# 	fail_type = 'intra'
					# elif cur_freq > 0:
					# 	inter_failure += 1
					# 	fail_type = 'inter'
					# 	if freq in inter_meas_config:
					# 		is_configured_inter_freq = inter_meas_config[freq][0] + ',' + str(inter_meas_config[freq][1]) + ',' + str(inter_meas_config[freq][2])
						# print cur_freq, freq, fields

					# print 'get intra/inter'

					# meas_before = False
					# last_report_ts = None
					# first_report_ts = None
					# report_serv_rss = None
					# report_neig_rss = None
					# report_num = 0
					# report_type = ''

					last_same_report = None

					# diff_cell_id = None
					# diff_cell_freq = None
					# diff_serv_rss = None
					# diff_neig_rss = None
					# diff_report_time = None
					# diff_report_type = None

					last_diff_report = None

					# while meas_report_stack:
					# 	report = meas_report_stack[-1]
					for report in meas_report_stack:
						# print freq, cellid, report['type'], report['meas_freq'], report['neighbor']
						if report['type'] in ['a3','a4','a5'] and freq == report['meas_freq'] and cellid in report['neighbor']:
							# print report
							# print 'here'
							if not last_same_report:
								est_snr, saved = get_saved_result(report['rsrq'])

								last_same_report = {'serv_freq':report['freq'], 'serv_rsrp':report['rsrp'], 'serv_rsrq':report['rsrq'], 'est_snr':est_snr, 'targ_freq':report['meas_freq'], 'targ_rsrp':report['neighbor'][cellid][0], 'targ_rsrq':report['neighbor'][cellid][1], 'type':report['type'], 'time':report['time'], 'thresh1':report['thresh1'], 'thresh2':report['thresh2'], 'saved':saved}

						# elif report['type'] in ['a3', 'a4', 'a5'] and report['neighbor'] and cur_freq != report['meas_freq']:
						elif report['type'] in ['a3', 'a4', 'a5'] and report['neighbor']:
							if not last_diff_report:
								est_snr, saved = get_saved_result(report['rsrq'])

								diff_cell_id = report['neighbor'].keys()[0]

								last_diff_report = {'serv_freq':report['freq'], 'serv_rsrp':report['rsrp'], 'serv_rsrq':report['rsrq'], 'est_snr':est_snr, 'targ_freq': report['meas_freq'], 'type':report['type'], 'time':report['time'], 'targets':report['neighbor'], 'thresh1':report['thresh1'], 'thresh2':report['thresh2'], 'saved':saved}

						# meas_report_stack.pop()

					if last_same_report:
						# if not last_same_report['thresh2']:
						# 	last_same_report['thresh2'] = 'None' 
						print file + ',re-est with same report,' + str(time) + ',' + ','.join(['%s,%s'%(x, str(last_same_report[x])) for x in sorted(last_same_report.keys())])

						# fout1.write(file + ',re-est with report,%.3f,%s,%s,%d,%.3f,%.3f,%d,%d,%d,%d,%d,%d,%d,%d,%s\n'%(time, fail_type, report_type, report_num, (last_report_ts - first_report_ts), (time - last_report_ts), cur_freq, cur_cell, report_serv_rss[0], report_serv_rss[1], freq, cellid, report_neig_rss[0], report_neig_rss[1], is_configured_inter_freq))

					else:
						# no_meas += 1
						if last_diff_report:
							# if not last_diff_report['thresh2']:
							# 	last_diff_report['thresh2'] = 'None'
							report_list = last_diff_report['targets']
							report_str = ','.join(['%s,%s,%s'%(str(x), str(report_list[x][0]), str(report_list[x][1])) for x in report_list])
							last_diff_report['targets'] = report_str

							print file + ',re-est with diff report,' + str(time) + ',' + ','.join(['%s,%s'%(x, str(last_diff_report[x])) for x in sorted(last_diff_report.keys())])
							# fout1.write(file + ',re-est with diff cell,%.3f,%s,%s,%.3f,%.3f,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s\n'%(time, fail_type, diff_report_type, diff_report_time, (time - diff_report_time), cur_freq, cur_cell, diff_serv_rss[0], diff_serv_rss[1], freq, cellid, diff_cell_freq, diff_cell_id, diff_neig_rss[0], diff_neig_rss[1], is_configured_inter_freq))
						else:
							inter_meas_type = ''
							if cur_freq != freq:
								inter_meas_type = 'Not configured'
								if freq in inter_meas_config:
									inter_meas_type = inter_meas_config[freq]
								
							print file + ',re-est without report,serv_freq,' + str(cur_freq) + ',targ_freq,' + str(freq) + ',targ_cell,' + str(cellid) + ',' + inter_meas_type
							
							# print file + ',re-est with non-reported cell,' + str(time) + ',' + str(cur_freq) + ',' + str(cur_cell) + ',' + str(freq) + ',' + str(cellid)
							 # is_configured_inter_freq

							pass

					inter_meas_config = {}
					meas_report_stack = []
					cur_freq = freq
					cur_cell = cellid
					# total_failure += 1
					
				# [rrc]:1564509145.58,Handoff,1850,123,1850,187,91
				if fields[1] == 'Handoff':
					cur_freq = int(fields[-3])
					cur_cell = int(fields[-2])
					meas_report_stack = []
					inter_meas_config = {}

				# [rrc]:1565519752.6,ConnectionSetup,2452,139
				if fields[1] == 'ConnectionSetup':
					cur_freq = int(fields[-2])
					cur_cell = int(fields[-1])
					meas_report_stack = []
					inter_meas_config = {}

				# [rrc]:1565519742.57,ConnectionRelease
				if fields[1] == 'ConnectionRelease':
					meas_report_stack = []
					inter_meas_config = {}
					# print cur_freq, cur_cell

				# [rrc]:1565519758.24,Reconfig complete,1825,6
				if fields[1] == 'Reconfig complete':
					cur_freq = int(fields[-2])
					cur_cell = int(fields[-1])

				# [rrc]:1564507109.41,Meas Config,1825,161,1825 a3 1 None 0 148.1 180.1 159.1
				if fields[1] == 'Meas Config':
					inter_meas_config.clear()
					for i in range(4, len(fields)):
						content = fields[i].split()
						freq = int(content[0])
						# serv_offset = 0
						if freq == int(fields[2]):
							continue

						if content[1] == 'a3' and int(content[2]) < 0:
							continue

						# if content[1] == 'a5' and int(content[2]) - int(content[3]) >= 30:
						# 	continue

						inter_meas_config[freq] = content[1]

						# thresh2 = int(fields[i+3]) if fields[i+1] == 'a5' else None
						# inter_meas_config[inter_freq] = (fields[i+1], int(fields[i+2]), thresh2)

			except:
				print "Unexpected error:", sys.exc_info()[0], file, fields, traceback.format_exc()
				continue

			# except IndexError as e:
			# 	print file, fields, traceback.format_exc()
			# 	continue

	# print sys.argv[1], total_failure, with_meas, no_meas, intra_failure, inter_failure
	# fout2.write(','.join([sys.argv[1], str(total_failure), str(with_meas), str(no_meas), str(intra_failure), str(inter_failure)]) + '\n')

	# fout1.close()
	# fout2.close()