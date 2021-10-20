# rem_private

## Usage

### Raw log parser
```
sh /path/to/repo/src/batch_monitor.sh /path/to/raw/log/folder
```

### Mobility analyzer
```
python /path/to/repo/src/handoff_failure.py /path/to/intermediate/log/folder > mobility_profile.log
```

## Dataset description:

We generate mobility logs for a fine-grained high-speed railway dataset [1].
There are two types of logs:
- [Mobility profile](https://github.com/cathyli93/rem_private/blob/main/dataset/hsr_profile.log): the profile of mobility events
- [Intermediate mobility traces](https://www.dropbox.com/sh/naq2efo6s9ylwgj/AABnxzR-QfASMMKNjiakgLmAa?dl=0): more details in plain text for deeper analysis

### Mobility profiles
The profile logs describe mobility events of successful/failed handovers. We record the following information for each event:
- ``handover`` message has the format of "<file_name>,<time_of_handover_finished>,handover,<time_of_handover_start>,<source_freq>,<source_cell>,<target_freq>,<target_cell>"
- ``handover-failure`` message has the format of "<file_name>,<time_of_handover_finished>,handover-failure: <failure_cause>,<time_of_disconnection>,<source_freq>,<source_cell>,<target_freq>,<target_cell>[,can_be_avoided_by_REM]"
    - Options of ``failure_cause``: mobility message loss (command/feedback), missed neighbor cells, coverage hole (cannot be avoided by REM).

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
- ``Meas Config`` rrc-ota:<unix_time>,Meas Config,<current_cell_freq>,<current_cell_id>,\<configs\>; 
configs is a list of hash maps, each of which summarizes one measurement configuration with the following keys:
	- freq
	- event_type
	- threshold1
	- threshold2
	- serving_offset
	- cell_offset: a hash map from cell id to cell offset