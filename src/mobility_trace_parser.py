#!/usr/bin/python
# Filename: mobility_mngt.py

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET
from mobile_insight.analyzer.analyzer import *

import copy

import pickle

__all__ = ["MobilityParser"]

import time
import datetime


def string2timestamp(s):
    if s is None:
        return None

    seconds = "%.6f"%(time.mktime(s.timetuple()) + s.microsecond / 1000000.0)
    return seconds


class MobilityParser(Analyzer):

    def __init__(self):

        Analyzer.__init__(self)

        self.__handoff_sample = HandoffSample()

        self.__current_freq = None
        self.__current_cid = None

        self.__last_measure = None
        self.__handover_ongoing = None

        self.add_source_callback(self.__filter)

    def set_source(self,source):
        """
        :param source: the trace source.
        :type source: trace collector
        """
        Analyzer.set_source(self,source)

        source.enable_log("LTE_RRC_OTA_Packet")
        source.enable_log("LTE_PHY_Serv_Cell_Measurement")

    def __filter(self, event):
        log_item = event.data.decode()
        decoded_event = Event(event.timestamp, event.type_id, log_item)

        if event.type_id == "LTE_RRC_OTA_Packet":
            self.__on_lte_rrc_msg(decoded_event)

        if event.type_id == "LTE_PHY_Serv_Cell_Measurement":
            self.__serv_cell_meas(log_item)

    def __serv_cell_meas(self, decoded):
        for element in decoded['Subpackets']:
            if element['Serving Cell Index'] == 'PCell' and element['Is Serving Cell'] == 1:
                if self.__current_freq is None:
                    self.__current_freq = element['E-ARFCN']
                    self.__current_cid = element['Physical Cell ID']

                if element['E-ARFCN'] == self.__current_freq and element['Physical Cell ID'] == self.__current_cid:
                    self.__last_measure = decoded['timestamp']
                    print("rss:" + string2timestamp(decoded['timestamp']) + "," + str(element['E-ARFCN']) + "," + str(element['Physical Cell ID']) + "," + str(element["RSRP"]) + "," + str(element["RSRQ"]))

                break

    def reset(self):
        self.__handoff_sample = HandoffSample()

    def __on_lte_rrc_msg(self, msg):
        """
        Handle LTE RRC messages.

        :param msg: the event (message) from the trace collector.
        """
        log_item = msg.data
        if 'Msg' not in log_item:
            return

        cur_freq = log_item['Freq']
        cur_cellid = log_item['Physical Cell ID']
        msg_len = log_item['Msg Length']
        

        #Convert msg to xml format
        log_xml = ET.XML(log_item['Msg'])

        # The message is decoded XML messages
        for field in log_xml.iter('field'):
            if field.get('name') == "lte-rrc.rrcConnectionSetup_element":
                self.__handoff_sample = HandoffSample()
                self.__current_freq = cur_freq
                self.__current_cid = cur_cellid
                # self.__execution_failure = False
                self.__handover_ongoing = None

                print("rrc-ota:" + str(string2timestamp(log_item['timestamp'])) + 
                              "," + "Connection setup" + "," + str(cur_freq) + "," + str(cur_cellid))

            if field.get('name') == "lte-rrc.rrcConnectionReestablishmentRequest_element":
                # <field name="lte-rrc.reestablishmentCause" pos="13" show="1" showname="reestablishmentCause: handoverFailure (1)" size="1" value="04" />
                self.__handoff_sample = HandoffSample()

                tag = 'Handover failure'
                if self.__current_freq == cur_freq and self.__current_cid == cur_cellid:
                    tag = 'Reestablish'

                for val in field.iter('field'):
                    if val.get('name') == 'lte-rrc.reestablishmentCause':
                        if int(val.get('show')) == 1:
                            # self.__execution_failure = True
                            tag = 'Reestablish'
                        break

                print("rrc-ota:" + str(string2timestamp(log_item['timestamp'])) + "," + tag + "," + str(cur_freq) + "," + str(cur_cellid) + "," + str(string2timestamp(self.__last_measure)))

                self.__current_freq = cur_freq
                self.__current_cid = cur_cellid
                # self.__execution_failure = False
                self.__handover_ongoing = None

            # if field.get("name") == "lte-rrc.rrcConnectionReestablishmentComplete_element":
            #     tag = 'Handover failure'
            #     if self.__execution_failure:
            #         tag = 'Reestablish'
            #     print("rrc-ota:" + str(string2timestamp(log_item['timestamp'])) + 
            #                   "," + tag + "," + str(cur_freq) + "," + str(cur_cellid) + "," + str(string2timestamp(self.__last_measure)))

            #     self.__current_freq = cur_freq
            #     self.__current_cid = cur_cellid
            #     self.__execution_failure = False
            #     self.__handover_ongoing = None

            if field.get("name") == "lte-rrc.rrcConnectionReconfigurationComplete_element":
                if self.__handover_ongoing:
                    print("rrc-ota:" + str(string2timestamp(log_item['timestamp'])) + 
                        ",Handover," + str(self.__handover_ongoing[0]) + "," + str(self.__handover_ongoing[1]) + "," + str(cur_freq) + "," + str(cur_cellid) + "," + str(string2timestamp(self.__handover_ongoing[2])))

                self.__current_freq = cur_freq
                self.__current_cid = cur_cellid
                # self.__execution_failure = False
                self.__handover_ongoing = None

            if field.get('name') == "lte-rrc.mobilityControlInfo_element":
                # A handoff command: create a new HandoffState
                target_cell = None
                qr_target_cell_id = -1
                for val in field.iter('field'):
                    # Currently we focus on freq-level handoff
                    if val.get('name') == 'lte-rrc.dl_CarrierFreq':
                        target_cell = val.get('show')
                    if val.get('name') == 'lte-rrc.targetPhysCellId':
                        qr_target_cell_id = val.get('show')
                if not target_cell:
                    target_cell = self.get_analyzer(
                        "LteRrcAnalyzer").get_cur_cell().freq

                if target_cell:
                    # FIXME: consider 4G->3G handover (e.g., SRVCC, CSFB)
                    handoff_state = HandoffState("LTE", target_cell)
                    self.__handoff_sample.add_state_transition(handoff_state)
                    # Reset handoff sample
                    self.__handoff_sample = HandoffSample()

                    self.__handover_ongoing = (cur_freq, cur_cellid, log_item['timestamp'])

                    return

            if field.get('name') == "lte-rrc.measurementReport_element":
                meas_id = None
                rss = None
                neigh_cell_list = {}
                p_rsrp = None
                p_rsrq = None
                for val in field.iter('field'):
                    if val.get('name') == 'lte-rrc.measId':
                        meas_id = val.get('show')
                    if val.get('name') == 'lte-rrc.rsrpResult':
                        rss = int(val.get('show')) - 140
                    if val.get('name') == 'lte-rrc.measResultPCell_element':
                        for rss_field in val.iter('field'):
                            # <field name="lte-rrc.rsrpResult" pos="10" show="20" showname="rsrpResult: -121dBm &lt;= RSRP &lt; -120dBm (20)" size="1" value="14" />
                            if rss_field.get('name') == 'lte-rrc.rsrpResult':
                                p_rsrp = int(rss_field.get('show')) - 140
                            # <field name="lte-rrc.rsrqResult" pos="11" show="0" showname="rsrqResult: RSRQ &lt; -19.5dB (0)" size="1" value="00" />
                            if rss_field.get('name') == 'lte-rrc.rsrqResult':
                                p_rsrq = int(rss_field.get('show'))

                    if val.get('name') == 'lte-rrc.measResultNeighCells':
                        for n_cell in val.iter('field'):
                            if n_cell.get('name') == 'lte-rrc.MeasResultEUTRA_element':
                                n_cellid = -1
                                n_rsrp = None
                                n_rsrq = None
                                # n_offset = -1
                                # <field name="lte-rrc.rsrpResult" pos="14" show="28" showname="rsrpResult: -113dBm &lt;= RSRP &lt; -112dBm (28)" size="1" value="1c" />
                                for rss_field in n_cell.iter('field'):
                                    if rss_field.get('name') == 'lte-rrc.physCellId':
                                        n_cellid = int(rss_field.get('show'))
                                    if rss_field.get('name') == 'lte-rrc.rsrpResult':
                                        n_rsrp = int(rss_field.get('show')) - 140
                                    if rss_field.get('name') == 'lte-rrc.rsrqResult':
                                        n_rsrq = int(rss_field.get('show'))
                                neigh_cell_list[n_cellid] = [n_rsrp, n_rsrq]

                if meas_id and self.__handoff_sample.cur_state:
                    meas_report = self.__handoff_sample.cur_state.get_meas_report_obj(
                        meas_id)
                    self.__handoff_sample.add_meas_report(meas_report)

                    if meas_report[0] and meas_report[1]:
                        # add cell offset
                        for cell, item in neigh_cell_list.items():
                            if meas_report[1].event_list[0].type == 'a3' and cell in meas_report[0].cell_list:
                                item.append(meas_report[0].cell_list[cell])
                            else:
                                item.append(0)

                        serv_offset = 0
                        if meas_report[0].freq == cur_freq and cur_cellid in meas_report[0].cell_list:
                            serv_offset = meas_report[0].cell_list[cur_cellid]

                        print("rrc-ota:" + str(string2timestamp(log_item['timestamp'])) +
                                      ",Measurement report," + str(cur_freq) + "," + str(cur_cellid) + "," + str({"serving_rsrp":p_rsrp,"serving_rsrq":p_rsrq,"event_type":meas_report[1].event_list[0].type, "time_to_trigger":meas_report[1].time_to_trigger, "measure_freq":meas_report[0].freq, "hyst":meas_report[1].hyst,"serving_offset":serv_offset, "threshold1": meas_report[1].event_list[0].threshold1, "threshold2": meas_report[1].event_list[0].threshold2, "results":neigh_cell_list}))
                
                print("rrc-ota:" + str(string2timestamp(log_item['timestamp'])) + ",Measurement serving," + str(cur_freq) + ',' + str(cur_cellid) + ',' + str(p_rsrp) + ',' + str(p_rsrq)) 

                self.__current_freq = cur_freq
                self.__current_cid = cur_cellid
                # self.__execution_failure = False

            if field.get('name') == "lte-rrc.measConfig_element":
                meas_state = None
                if self.__handoff_sample.cur_state:
                    # Meas control may take stateful addition/deletion,
                    # So need current copy whenever available
                    meas_state = copy.deepcopy(self.__handoff_sample.cur_state)
                else:
                    meas_state = MeasState()

                for val in field.iter('field'):
                    if val.get('name') == 'lte-rrc.MeasObjectToAddMod_element':
                        # Add measurement object
                        meas_obj = self.__get_meas_obj(val)
                        if meas_obj:
                            meas_state.measobj[meas_obj.obj_id] = meas_obj

                    if val.get('name') == 'lte-rrc.measObjectToRemoveList':
                        # Remove measurement object
                        for item in val.iter('field'):
                            if item.get('name') == 'lte-rrc.MeasObjectId' \
                                    and item.get('show') in meas_state.measobj:
                                del meas_state.measobj[item.get('show')]

                    if val.get(
                            'name') == 'lte-rrc.ReportConfigToAddMod_element':
                        # Add/modify a report config
                        report_config = self.__get_report_config(val)
                        if report_config:
                            meas_state.report_list[report_config.report_id] = report_config

                    if val.get('name') == 'lte-rrc.reportConfigToRemoveList':
                        # Remove a report config
                        for item in val.iter('field'):
                            if item.get('name') == 'lte-rrc.ReportConfigId' \
                                    and item.get('show') in meas_state.report_list:
                                del meas_state.report_list[item.get('show')]

                    if val.get('name') == 'lte-rrc.MeasIdToAddMod_element':
                        # Add a measurement ID
                        meas_id = -1
                        meas_obj_id = -1
                        report_id = -1
                        for item in val.iter('field'):
                            if item.get('name') == 'lte-rrc.measId':
                                meas_id = item.get('show')
                            if item.get('name') == 'lte-rrc.measObjectId':
                                meas_obj_id = item.get('show')
                            if item.get('name') == 'lte-rrc.reportConfigId':
                                report_id = item.get('show')
                        meas_state.measid_list[meas_id] = (
                            meas_obj_id, report_id)

                    if val.get('name') == 'lte-rrc.measIdToRemoveList':
                        # Remove a measurement ID
                        for item in val.iter('field'):
                            if item.get('name') == 'lte-rrc.MeasId' \
                                    and item.get('show') in meas_state.measid_list:
                                del meas_state.measid_list[item.get('show')]

                to_print_list = []
                for meas_id in meas_state.measid_list:
                    obj_id, config_id = meas_state.measid_list[meas_id]
                    # print obj_id, config_id
                    
                    # if obj_id in meas_state.measobj and meas_state.measobj[obj_id].freq != cur_freq:
                    if obj_id in meas_state.measobj:
                        if config_id in meas_state.report_list and meas_state.report_list[config_id].event_list[0].type in ['a3','a4','a5']:
                            meas_event = meas_state.report_list[config_id].event_list[0]
                            # exclude a3-event for monitoring only
                            if meas_event.type == 'a3' and meas_event.threshold1 < 0:
                                continue

                            celloffset = {}
                            self_offset = 0
                            if meas_event.type == 'a3':
                                meas_obj_tmp = meas_state.measobj[obj_id]
                                # if meas_obj_tmp.cell_list:
                                for c in meas_obj_tmp.cell_list:
                                    if c == cur_cellid and meas_obj_tmp.freq == cur_freq:
                                        self_offset = meas_obj_tmp.cell_list[c]
                                    else:
                                        celloffset = meas_obj_tmp.cell_list[c]

                            to_print_list.append({"freq":meas_state.measobj[obj_id].freq, "event_type":meas_event.type, "threshold1":meas_event.threshold1, "threshold2":meas_event.threshold2, "serving_offset":self_offset, "cell_offset":celloffset}) 

                if to_print_list:        
                    print("rrc-ota:" + str(string2timestamp(log_item['timestamp'])) + ",Meas Config," + str(cur_freq) + "," + str(cur_cellid) + "," + str({"info":to_print_list}))

                # Generate a new state to the handoff sample
                self.__handoff_sample.add_state_transition(meas_state)

                # self.__mobility_state_machine.update_state_machine(self.__handoff_sample)
                # #Reset handoff sample
                # self.__handoff_sample = HandoffSample()
                self.log_info(str(string2timestamp(log_item['timestamp'])
                                  ) + " Measurement control")

                self.__current_freq = cur_freq
                self.__current_cid = cur_cellid
                # self.__execution_failure = False

    def __get_meas_obj(self, msg):
        """
        Parse MeasObjectToAddMod_element, return a measurement object

        :param msg: the XML msg with MeasObjectToAddMod_element
        :returns: a measurement objects to be added
        """
        measobj_id = -1
        for field in msg.iter('field'):
            if field.get('name') == "lte-rrc.measObjectId":
                measobj_id = field.get('show')

            # <field name="lte-rrc.CellsToAddMod_element" pos="20" show="" showname="CellsToAddMod" size="3" value="">
            #     <field name="lte-rrc.cellIndex" pos="20" show="1" showname="cellIndex: 1" size="1" value="00" />
            #     <field name="lte-rrc.physCellId" pos="21" show="442" showname="physCellId: 442" size="2" value="374f" />
            #     <field hide="yes" name="per.enum_index" pos="22" show="15" showname="Enumerated Index: 15" size="1" value="4f" />
            #     <field name="lte-rrc.cellIndividualOffset" pos="22" show="15" showname="cellIndividualOffset: dB0 (15)" size="1" value="4f" />
            # </field>

            if field.get('name') == "lte-rrc.measObjectEUTRA_element":

                # A LTE meas obj
                field_val = {}

                field_val['lte-rrc.carrierFreq'] = None
                field_val['lte-rrc.offsetFreq'] = 0

                for val in field.iter('field'):
                    field_val[val.get('name')] = val.get('show')
                if field_val['lte-rrc.carrierFreq']:
                    freq = int(field_val['lte-rrc.carrierFreq'])
                    offsetFreq = int(field_val['lte-rrc.offsetFreq'])
                    lte_meas_obj = LteMeasObjectEutra(measobj_id, freq, offsetFreq)

                    for cell_obj in field.iter('field'):
                        if cell_obj.get('name') == 'lte-rrc.CellsToAddMod_element':
                            cell_id = None
                            cell_offset = None
                            for val in cell_obj.iter('field'):
                                if val.get('name') == 'lte-rrc.physCellId':
                                    cell_id = int(val.get('show'))
                                if val.get('name') == 'lte-rrc.cellIndividualOffset':
                                    val_list = val.get('showname').split(' ')
                                    if len(val_list) == 3 and val_list[1][:2] == 'dB':
                                        cell_offset = int(val_list[1][2:])
                            if cell_id and cell_offset:
                                lte_meas_obj.add_cell(cell_id, cell_offset)
                    return lte_meas_obj

        return None  # How can this happen?

    def __get_report_config(self, msg):
        """
        Parse ReportConfigToAddMod_element, return a report config

        :param msg: the XML msg with ReportConfigToAddMod_element
        :returns: a measurement objects to be added
        """
        report_id = -1
        hyst = 0
        time_to_trigger = 0
        for val in msg.iter('field'):
            if val.get('name') == "lte-rrc.reportConfigId":
                report_id = val.get('show')
            # <field name="lte-rrc.hysteresis" pos="25" show="3" showname="hysteresis: 1.5dB (3)" size="1" value="08" />
            # qianru_to_merge: correct hyst value
            if val.get('name') == 'lte-rrc.hysteresis':
                hyst_list = val.get('showname').split(' ')
                if len(hyst_list) == 3 and hyst_list[1][-2:] == 'dB':
                    hyst = float(hyst_list[1][:-2])
                # hyst = int(val.get('show'))
            # <field name="lte-rrc.timeToTrigger" pos="28" show="8" showname="timeToTrigger: ms320 (8)" size="1" value="48" />
            if val.get('name') == 'lte-rrc.timeToTrigger':
                ttt_list = val.get('showname').split()
                if len(ttt_list) >= 2 and ttt_list[1][:2] == 'ms':
                    time_to_trigger = int(ttt_list[1][2:])

        report_config = LteReportConfig(report_id, hyst / 2)
        report_config.time_to_trigger = time_to_trigger

        for val in msg.iter('field'):
            if val.get('name') == 'lte-rrc.eventA1_element':
                for item in val.iter('field'):
                    if item.get('name') == 'lte-rrc.threshold_RSRP':
                        report_config.add_event(
                            'a1', int(item.get('show')) - 140)
                        break
                    if item.get('name') == 'lte-rrc.threshold_RSRQ':
                        report_config.add_event(
                            'a1', (int(item.get('show')) - 40) / 2)
                        break

            if val.get('name') == 'lte-rrc.eventA2_element':
                for item in val.iter('field'):
                    if item.get('name') == 'lte-rrc.threshold_RSRP':
                        report_config.add_event(
                            'a2', int(item.get('show')) - 140)
                        break
                    if item.get('name') == 'lte-rrc.threshold_RSRQ':
                        report_config.add_event(
                            'a2', (int(item.get('show')) - 40) / 2)
                        break

            if val.get('name') == 'lte-rrc.eventA3_element':
                for item in val.iter('field'):
                    if item.get('name') == 'lte-rrc.a3_Offset':
                        report_config.add_event(
                            'a3', int(item.get('show')) / 2)
                        break

            if val.get('name') == 'lte-rrc.eventA4_element':
                for item in val.iter('field'):
                    if item.get('name') == 'lte-rrc.threshold_RSRP':
                        report_config.add_event(
                            'a4', int(item.get('show')) - 140)
                        break
                    if item.get('name') == 'lte-rrc.threshold_RSRQ':
                        report_config.add_event(
                            'a4', (int(item.get('show')) - 40) / 2)
                        break

            if val.get('name') == 'lte-rrc.eventA5_element':
                threshold1 = None
                threshold2 = None
                for item in val.iter('field'):
                    if item.get('name') == 'lte-rrc.a5_Threshold1':
                        for item2 in item.iter('field'):
                            if item2.get('name') == 'lte-rrc.threshold_RSRP':
                                threshold1 = int(item2.get('show')) - 140
                                break
                            if item2.get('name') == 'lte-rrc.threshold_RSRQ':
                                threshold1 = (int(item2.get('show')) - 40) / 2
                                break
                    if item.get('name') == 'lte-rrc.a5_Threshold2':
                        for item2 in item.iter('field'):
                            if item2.get('name') == 'lte-rrc.threshold_RSRP':
                                threshold2 = int(item2.get('show')) - 140
                                break
                            if item2.get('name') == 'lte-rrc.threshold_RSRQ':
                                threshold2 = (int(item2.get('show')) - 40) / 2
                                break
                report_config.add_event('a5', threshold1, threshold2)

            if val.get('name') == 'lte-rrc.eventB1_element':
                for item in val.iter('field'):
                    if item.get('name') == 'lte-rrc.threshold_RSRP':
                        report_config.add_event(
                            'b1', int(item.get('show')) - 140)
                        break
                    if item.get('name') == 'lte-rrc.threshold_RSRQ':
                        report_config.add_event(
                            'b1', (int(item.get('show')) - 40) / 2)
                        break
                    if item.get('name') == 'lte-rrc.threshold_RSCP':
                        report_config.add_event(
                            'b1', int(item.get('show')) - 115)
                        break

            if val.get('name') == 'lte-rrc.eventB2_element':

                threshold1 = None
                threshold2 = None
                for item in val.iter('field'):
                    if item.get('name') == 'lte-rrc.b2_Threshold1':
                        for item2 in item.iter('field'):
                            if item2.get('name') == 'lte-rrc.threshold_RSRP':
                                threshold1 = int(item2.get('show')) - 140
                                break
                            if item2.get('name') == 'lte-rrc.threshold_RSRQ':
                                threshold1 = (int(item2.get('show')) - 40) / 2
                                break
                    if item.get('name') == 'lte-rrc.b2_Threshold2':
                        for item2 in item.iter('field'):
                            if item2.get('name') == 'lte-rrc.threshold_RSRP':
                                threshold2 = int(item2.get('show')) - 140
                                break
                            if item2.get('name') == 'lte-rrc.threshold_RSRQ':
                                threshold2 = (int(item2.get('show')) - 40) / 2
                                break
                            if item2.get('name') == 'lte-rrc.utra_RSCP':
                                threshold2 = int(item2.get('show')) - 115
                                break
                report_config.add_event('b2', threshold1, threshold2)

        if report_config.event_list:
            return report_config
        else:
            # periodical report. No impact on handoff
            return None

# Handoff rule inference modules
############################################


class HandoffState:
    """
    A state abstraction to represent the handoff target
    This is used for handoff policy inference.

    In current implement, we choose frequency-level handoff target granualrity
    (rather than cell level). This is based on the observation that cells of the
    same frequency are homogeneous. Operators in reality tend to not differentiate them
    """

    def __init__(self, rat, freq):
        self.rat = rat  # Radio access technology (3G or 4G)
        self.freq = freq  # Frequency band

    def equals(self, handoff_state):

        if handoff_state.__class__.__name__ != "HandoffState":
            return False
        return handoff_state.freq == self.freq \
            and handoff.rat == self.rat

    def dump(self):
        return "(" + str(self.rat) + "," + str(self.freq) + ")\n"


class MeasState:
    """
    A Measurement state for the handoff policy inference
    """

    def __init__(self):
        # TODO: initialize some containers
        # FIXME: change the key of measobj: freq to obj_id
        self.measobj = {}  # obj_id->measobject
        self.report_list = {}  # report_id->reportConfig
        self.measid_list = {}  # meas_id->(obj_id,report_id)

    def get_measobj(self, meas_id):
        """
        Given the measurement ID, returns the corresponding measurement object

        :param meas_id: measurement ID
        :type meas_id: integer
        :returns: Measurement object in it, or None if the id does not exist
        """
        # meas_obj = None
        # for i in self.measobj:
        #     if self.measobj[i].obj_id == self.measid_list[item][0]:
        #         meas_obj = self.measobj[i]
        # return meas_obj
        if meas_id not in self.measid_list \
                or self.measid_list[meas_id][0] not in self.measobj:
            # print "get_measobj: meas_id="+str(meas_id)+" meas_obj="+str(self.measid_list[meas_id])
            # print "debug: "+str(self.measobj.keys())
            return None
        else:
            return self.measobj[self.measid_list[meas_id][0]]

    def get_reportconfig(self, meas_id):
        """
        Given the measurement ID, returns the corresponding report configuration object

        :param meas_id: measurement ID
        :type meas_id: integer
        :returns: ReportConfig in it, or None if the id does not exist
        """
        if meas_id not in self.measid_list \
                or self.measid_list[meas_id][1] not in self.report_list:
            return None
        else:
            return self.report_list[self.measid_list[meas_id][1]]

    def get_meas_report_obj(self, meas_id):
        """
        return the measurement report obj
        :param meas_id: measurement ID
        :type meas_id: integer
        :returns: (measobj,report_config) pair
        """
        measobj = self.get_measobj(meas_id)
        report_config = self.get_reportconfig(meas_id)

        return (measobj, report_config)

    def equals(self, meas_state):
        """
        Compare two states to see if they are equivalent

        :param meas_state: another measurement state
        :type meas_state: MeasState
        :returns: True if two states are equivalent, False otherwise
        """

        if meas_state.__class__.__name__ != "MeasState":
            return False

        # Algorithm for comparison:
        # Compare all objects in measid_list
        # For each one, check its freq, and the event/threshold configurations
        if len(self.measid_list) != len(meas_state.measid_list):
            return False
        for meas_id in self.measid_list:

            # Get its measobj and reportConfig
            meas_obj = self.get_measobj(meas_id)
            report_obj = self.get_reportconfig(meas_id)
            if not meas_obj or not report_obj:
                # Should not happen unless bug exists
                return False

            # Find if this measurement object also exists int meas_state
            meas_id_exist = False
            for meas_id2 in meas_state.measid_list:
                meas_obj2 = meas_state.get_measobj(meas_id2)
                report_obj2 = meas_state.get_reportconfig(meas_id2)
                if meas_obj.equals(
                        meas_obj2) and report_obj.equals(report_obj2):
                    meas_id_exist = True
                    break
            if not meas_id_exist:
                return False
        return True

    def dump(self):
        """
        Report the cell's active-state configurations

        :returns: a string that encodes the cell's active-state configurations
        :rtype: string
        """
        res = ""
        for item in self.measobj:
            res += self.measobj[item].dump()
        for item in self.report_list:
            res += self.report_list[item].dump()
        for item in self.measid_list:
            res += "MeasObj " + str(item) + ' ' + \
                str(self.measid_list[item]) + '\n'
        return res


class MeasReportSeq:
    """
    An abstraction for measurement report sequence
    """

    def __init__(self):
        self.meas_report_queue = []

    def add_meas_report(self, meas_report):
        """
        Append a measurement report.
        Currently we abstract the concrete measured signal strength

        :param meas_report: a (MeasObject,ReportConfig) pair for that report
        :type meas_report:(MeasObject,ReportConfig)
        :returns: True if successfully appended, False otherwise
        """
        if meas_report.__class__.__name__ != "tuple":
            return False
        if meas_report[0].__class__.__name__ != "LteMeasObjectEutra" \
                and meas_report[0].__class__.__name__ != "LteMeasObjectUtra" \
                and meas_report[0].__class__.__name__ != "LteMeasObjectGERAN" \
                and meas_report[0].__class__.__name__ != "LteMeasObjectCDMA2000" \
                and meas_report[1].__class__.__name__ != "LteReportConfig":
            return False
        if meas_report[0] and meas_report[1]:
            self.meas_report_queue.append(meas_report)
        return True

    def merge_seq(self, meas_report_seq):
        """
        Merge two measurement report sequence with longest common substring (LCS) algorithm
        This is the core function of mobility policy inference

        :param meas_report_seq: measurement report sequence
        :type meas_report_seq: MeasReportSeq
        :returns: True if succeeded, False otherwise
        """
        if meas_report_seq.__class__.__name__ != "MeasReportSeq":
            return False

        # TODO: this function should be moved to MobilityStateMachine,
        # because it needs to resolve global conflicts
        # TODO: replace the following code with LCS algorithm
        # As first step, we simply replace the existing sequence
        self.meas_report_queue = meas_report_seq.meas_report_queue

    def equals(self, meas_report_seq):
        """
        Compare if two measurement sequences are equivalent

        :param meas_report_seq: measurement report sequence
        :type meas_report_seq: MeasReportSeq
        :returns: True if equivalent, False otherwise
        """
        if meas_report_seq.__class__.__name__ != "MeasReportSeq":
            return False


class HandoffSample:
    """
    A handoff sample based on observation
    """

    def __init__(self):
        self.cur_state = None
        #(From_State,To_State,tx_cond)
        # For the first element, its tx_cond is meaningless
        self.tx_list = []
        self.tx_cond = MeasReportSeq()

    def add_meas_report(self, meas_report):
        """
        Add a measurement report_event

        :param meas_report: a new measurement report
        :type meas_report: (meas_obj,report_config)
        """

        # If current state is None, ignore the input (i.e., drop this sample)
        if self.cur_state:
            self.tx_cond.add_meas_report(meas_report)

    def add_state_transition(self, new_state):
        """
        Append a new state and its transition condition.

        :param new_state: a MeasState or a HandoffState
        :type new_state: MeasState or HandoffState
        :returns: True if succeeds, or False otherwise
        """
        if new_state.__class__.__name__ != "MeasState" \
                and new_state.__class__.__name__ != "HandoffState":
            return False

        if new_state.equals(self.cur_state):
            # If they are same states, no transition
            return False

        self.tx_list.append((self.cur_state, new_state, self.tx_cond))
        self.cur_state = new_state

        # Reset measurement sequence
        self.tx_cond = MeasReportSeq()
        return True


# Helper modules
############################################
class LteMeasObjectEutra:
    """
    LTE Measurement object configuration
    """

    def __init__(self, measobj_id, freq, offset_freq):
        self.obj_id = measobj_id
        self.freq = freq  # carrier frequency
        self.offset_freq = offset_freq  # frequency-specific measurement offset
        self.cell_list = {}  # cellID->cellIndividualOffset
        # TODO: add cell blacklist

    def equals(self, meas_obj):
        """
        Compare if this meas_obj is equal to another one

        :param meas_obj: a measurement object
        :type meas_obj: LteMeasObjectEutra
        :returns: True if they are equivalent, False otherwise
        """
        return meas_obj.__class__.__name__ == "LteMeasObjectEutra" \
            and self.freq == meas_obj.freq \
            and self.offset_freq == meas_obj.offset_freq \
            and self.cell_list == meas_obj.cell_list

    def add_cell(self, cell_id, cell_offset):
        """
        Add a cell individual offset

        :param cell_id: the cell identifier
        :type cell_id: int
        :param cell_offset: the cell individual offset
        :type cell_offset: int
        """
        self.cell_list[cell_id] = cell_offset

    def dump(self):
        """
        Report the cell's LTE measurement configurations

        :returns: a string that encodes the cell's LTE measurement configurations
        :rtype: string
        """
        # res = self.__class__.__name__+' '+str(self.obj_id)+' '\
        # +str(self.freq)+' '+ str(self.offset_freq)+'\n'
        res = (self.__class__.__name__
               + ' ' + str(self.obj_id)
               + ' ' + str(self.freq)
               + ' ' + str(self.offset_freq)
               + '\n')
        for item in self.cell_list:
            res += str(item) + ' ' + str(self.cell_list[item]) + '\n'
        return res


class LteReportConfig:
    """
    LTE measurement report configuration
    """

    def __init__(self, report_id=None, hyst=None):
        self.report_id = report_id
        self.hyst = hyst
        self.event_list = []
        self.time_to_trigger = 0

    def equals(self, report_config):
        """
        Compare the equivalence of two ReportConfig

        :param report_config: report configuration
        :types report_config: LteReportConfig
        :returns: True if they are equivalent, False otherwise
        """
        if report_config.__class__.__name__ != "LteReportConfig" \
                or self.hyst != report_config.hyst:
            return False
        for item in self.event_list:
            item_exist = False
            for item2 in report_config.event_list:
                if item.equals(item2):
                    item_exist = True
                    break
            if not item_exist:
                return False
        return True

    def add_event(self, event_type, threshold1, threshold2=None):
        """
        Add a measurement event

        :param event_type: a measurement type (r.f. 5.5.4, TS36.331)
        :type event_type: string
        :param threshold1: threshold 1
        :type threshold1: int
        :param threshold2: threshold 2
        :type threshold2: int
        """
        self.event_list.append(
            LteRportEvent(
                event_type,
                threshold1,
                threshold2))

    def dump(self):
        """
        Report the cell's measurement report configurations

        :returns: a string that encodes the cell's measurement report configurations
        :rtype: string
        """
        res = (self.__class__.__name__
               + ' ' + str(self.report_id)
               + ' ' + str(self.hyst) + '\n')
        for item in self.event_list:
            res += (str(item.type)
                    + ' ' + str(item.threshold1)
                    + ' ' + str(item.threshold2) + '\n')
        return res


class LteRportEvent:
    """
    Abstraction for LTE report event
    """

    def __init__(self, event_type, threshold1, threshold2=None):
        self.type = event_type
        self.threshold1 = threshold1
        self.threshold2 = threshold2

    def equals(self, report_event):
        """
        Compare two report event

        :param report_event: a LTE report event configuration
        :type report_event: LteReportEvent
        :returns: True if they are equivalent, False otherwise
        """
        return report_event.__class__.__name__ == "LteRportEvent" \
            and self.type == report_event.type \
            and self.threshold1 == report_event.threshold1 \
            and self.threshold2 == report_event.threshold2
############################################
