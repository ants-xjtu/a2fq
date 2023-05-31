#!/usr/bin/env python3
#
# Define IperfData and IperfEntry class to maintain iperf data.
# Author: Guangyu Peng (gypeng2021@163.com)

class IperfEntry:
    
    def __init__(self, start_time: str, end_time: str, 
                transfer_bytes: int, bandwidth: float):
        """
        Parameters:
            start_time: string, interval begin time, unit:sec, e.g. "0.0"
            end_time: string, interval end time, unit:sec, e.g. "0.5"
            transfer_bytes: int, unit:byte, e.g. 102400
            bandwidth: float, unit:Mbps, e.g. 20.2
        """
        self.start_time_str = start_time
        self.start_time_num = float(start_time)
        self.end_time_str = end_time
        self.end_time_num = float(end_time)
        self.transfer_bytes = transfer_bytes
        self.bandwidth = bandwidth

class IperfData:
    
    def __init__(self):
        self.__entries = []

    def _get_bandwidth(self, bandwidth: float, unit: str) -> float:
        res = float(bandwidth)
        if unit == 'bps':
            res = res * 1000 * 1000
        elif unit == 'Kbps':
            res = res * 1000
        elif unit == 'Mbps':
            res = res
        elif unit == 'Gbps':
            res = res / 1000
        else:
            raise ValueError('parameter unit error!')
        return res

    def add_entry(self, entry: IperfEntry):
        self.__entries.append(entry)
    
    def size(self):
        return len(self.__entries)

    def get_end_time_strs(self, begin=0, end=None):
        # TODO offset
        if end is None:
            end = self.size()
        res = []
        for entry in self.__entries[begin:end]:
            res.append(entry.end_time_str)
        return res

    def get_end_time_nums(self, begin=0, end=None, offset=0):
        if end is None:
            end = self.size()
        res = []
        for entry in self.__entries[begin:end]:
            res.append(entry.end_time_num + offset)
        return res

    def get_bandwidth_list(self, unit: str, begin=0, end=None):
        """
        unit: 'bps'|'Kbps'|'Mbps'|'Gbps'
        """
        if end is None:
            end = self.size()
        res = []
        for entry in self.__entries[begin:end]:
            res.append(self._get_bandwidth(entry.bandwidth, unit))
        return res

    def get_avg_bandwidth(self, unit: str, begin=0, end=None):
        """
        unit: 'bps'|'Kbps'|'Mbps'|'Gbps'
        """
        if end is None:
            end = self.size()
        res = 0
        num = 0
        for entry in self.__entries[begin:end]:
            res = res + entry.bandwidth
            num = num + 1
        res = res / num
        return self._get_bandwidth(res, unit)