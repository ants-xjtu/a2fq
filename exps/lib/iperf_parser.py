#!/usr/bin/env python3
#
# Parse iperf data file into IperfData object.
# Author: Guangyu Peng (gypeng2021@163.com)

from lib.iperf_data import *
import re

class IperfParser:

    def __init__(self):
        self.head_re = re.compile(r'.*Interval\s+Transfer\s+Bandwidth.*')
        self.interval_re = re.compile(r'\d+\.\d+\s*-\s*\d+\.\d+\s*sec')
        self.transfer_re = re.compile(r'\d+\.?\d*\s*[GMK]?Bytes')
        self.bandwidth_re = re.compile(r'\d+\.?\d*\s*[GMK]?bits/sec')
        self.number_re = re.compile(r'\d+\.?\d*')
        self.alpha_re = re.compile(r'[a-zA-Z]+')

    def iperf_parse(self, filepath: str, encoding='utf-8') -> IperfData:
        iperf_data = IperfData()
        start_time_list = []
        end_time_list = []
        transfer_bytes_list = []
        bandwidth_Mbps_list = []

        with open(filepath, 'r', encoding=encoding) as f:
            line = f.readline()
            while line:
                head_match = self.head_re.match(line)
                line = f.readline()
                if head_match is not None:
                    break
        
            while line:
                interval = self.interval_re.search(line).group(0)
                transfer = self.transfer_re.search(line).group(0)
                bandwidth = self.bandwidth_re.search(line).group(0)
                #print(interval, transfer, bandwidth)
                start_time, end_time = self._parse_interval(interval)
                transfer_bytes = self._parse_transfer(transfer)
                bandwidth_Mbps = self._parse_bandwidth(bandwidth)
                start_time_list.append(start_time)
                end_time_list.append(end_time)
                transfer_bytes_list.append(transfer_bytes)
                bandwidth_Mbps_list.append(bandwidth_Mbps)
                line = f.readline()
        
        for stime, etime, transfer_bytes, bandwidth_Mbps in zip(
                                                start_time_list, 
                                                end_time_list, 
                                                transfer_bytes_list, 
                                                bandwidth_Mbps_list
                                                ):
            iperf_entry = IperfEntry(stime, etime, 
                                     transfer_bytes, bandwidth_Mbps)
            iperf_data.add_entry(iperf_entry)
        return iperf_data

    def _parse_interval(self, interval: str):
        numbers = self.number_re.findall(interval)
        return (numbers[0], numbers[1])

    def _parse_transfer(self, transfer: str) -> int:
        # return unit is Bytes
        number_str = self.number_re.search(transfer).group(0)
        unit_str = self.alpha_re.search(transfer).group(0)
        number = float(number_str)
        if unit_str == 'KBytes':
            number = number * 1024
        elif unit_str == 'MBytes':
            number = number * 1024 * 1024
        elif unit_str == 'GBytes':
            number = number * 1024 * 1024 * 1024
        return int(number)

    def _parse_bandwidth(self, bandwidth: str) -> float:
        # return unit is Mbps
        number_str = self.number_re.search(bandwidth).group(0)
        unit_str = self.alpha_re.search(bandwidth).group(0)
        number = float(number_str)
        if unit_str == 'Kbits':
            number = number / 1000
        elif unit_str == 'bits':
            number = number / 1000 / 1000
        elif unit_str == 'Gbits':
            number = number * 1000
        return number

if __name__ == '__main__':
    file_path = '../../data/conv_dumbbell_virtualbox/20220407_173032/A2FQ_client_1'
    IperfParser().iperf_parse(file_path)