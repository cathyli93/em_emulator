# rem_private

## Dataset description:
### Intermediate mobility logs 
The logs include RRC OTA traces of the following types and formats:
- ``Connection setup`` rrc-ota:<unix_time>,Connection setup,<new_cell_freq>,<new_cell_id>
- ``Handover failure`` rrc-ota:<unix_time>,Handover failure,<new_cell_freq>,<new_cell_id>,<unix_time_when_lose_old_connection>
- ``Handover`` rrc-ota:<unix_time>,Handover,<source_cell_freq>,<source_cell_id>,<target_cell_freq>,<target_cell_id>,<unix_time_when_handover_started>
- ``Measurement report`` rrc-ota:<unix_time>,Measurement report,<current_cell_freq>,<current_cell_id>,<report_content>
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
	- results: a hash map from cell id to signal strengths; <cell_id>:[\<rsrp\>,\<rsrq\>,<cell_offset>]
- ``Measurement serving`` rrc-ota:<unix_time>,Measurement serving,<current_cell_freq>,<current_cell_id>,\<rsrp\>,\<rsrq\>
- ``Meas Config`` rrc-ota:<unix_time>,Meas Config,<current_cell_freq>,<current_cell_id>,\<configs\>
	- configs is a list of hash maps, each of which summarizes one measurement configuration with the following keys:
	- freq
	- event_type
	- threshold1
	- threshold2
	- serving_offset
	- cell_offset: a hash map from cell id to cell offset