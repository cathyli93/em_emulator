# rem_private

Dataset description:

- Intermediate data logs contain readable mobility traces. Currently, it includes RRC OTA traces of the following types:
	- Connection setup: rrc-ota:<timestamp>,Connection setup,<new_cell_freq>,<new_cell_id>
	- Handover failure: rrc-ota:<timestamp>,Handover failure,<new_cell_freq>,<new_cell_id>,<timestamp_of_losing_old_connection>
	- Handover: rrc-ota:<timestamp>,Handover,<source_cell_freq>,<source_cell_id>,<target_cell_freq>,<target_cell_id>,<timestamp_when_handover_started>
	- Measurement report: rrc-ota:<timestamp>,Measurement report,<current_cell_freq>,<current_cell_id>,<report_content>
		- report_content is a Hash map (dictionary in Python) with the following keys:
			- serving_rsrp
			- serving_rsrq
			- measure_freq
			- event_type
			- threshold1
			- threshold2
			- time_to_trigger
			- hyst
			- serving_offset
			- measure_freq
			- results: a hash map from cell id to signal strengths
				- <cell_id>:[<rsrp>,<rsrq>,<cell_offset>]
	- Measurement serving: rrc-ota:<timestamp>,Measurement serving,<current_cell_freq>,<current_cell_id>,<rsrp>,<rsrq>
	- Meas Config: rrc-ota:<timestamp>,Meas Config,<current_cell_freq>,<current_cell_id>,<configs>
		- configs is a list of hash maps, each of which summarizes one measurement configuration with the following keys:
			- freq
			- event_type
			- threshold1
			- threshold2
			- serving_offset
			- cell_offset: a hash map from cell id to cell offset