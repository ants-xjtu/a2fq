#!/usr/bin/env python3
#
# Plot convergence graph of convergence exp data.
# Author: Guangyu Peng (gypeng2021@163.com)

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from lib.iperf_data import *
from lib.iperf_parser import IperfParser

def get_fairness_index(flow_rates: list):
    n = len(flow_rates)
    val_sum = sum(flow_rates)
    square_sum = sum(i*i for i in flow_rates)
    return (val_sum**2) / (n*square_sum)

FILE_PATTERN = '%s_%s_%d'
EXP_DATA_DIR_FILE = './exp_data_dir'
FLOW_ENTER_INTERVAL_FILE = './flow_enter_interval'
DUMBBELL_PAIRS_FILE = './dumbbell_pairs'
GROUP_FLOWS_FILE = './group_flows'
project_names = ['AFQ', 'A2FQ']
#project_names = ['basic']
measure_sides = ['server']
exp_data_dir = None
flow_enter_interval = None
dumbbell_pairs = None
group_flows = None

exp_datas = [
    {
        "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_232622_18_8M",
        "interval": 10,
        "group_flows": 3,
        "dumbbell_pairs": 18
    }, 
    {
        "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_233618_18_8M",
        "interval": 10,
        "group_flows": 3,
        "dumbbell_pairs": 18
    }, 
    {
        "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_231546_21_8M",
        "interval": 10,
        "group_flows": 3,
        "dumbbell_pairs": 21
    }, 
    {
        "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_230536_21_8M",
        "interval": 10,
        "group_flows": 3,
        "dumbbell_pairs": 21
    }, 
    {
        "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_225502_18_9M",
        "interval": 10,
        "group_flows": 3,
        "dumbbell_pairs": 18
    }, 
    # {
    #     "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_223057_18_9M",
    #     "interval": 10,
    #     "group_flows": 3,
    #     "dumbbell_pairs": 18
    # }, 
    {
        "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_224045_24_9M",
        "interval": 10,
        "group_flows": 3,
        "dumbbell_pairs": 24
    }, 
    {
        "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_215631_24_9M",
        "interval": 10,
        "group_flows": 3,
        "dumbbell_pairs": 24
    }, 
    {
        "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_222050_21_9M",
        "interval": 10,
        "group_flows": 3,
        "dumbbell_pairs": 21
    }, 
    {
        "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_221040_21_9M",
        "interval": 10,
        "group_flows": 3,
        "dumbbell_pairs": 21
    }, 
    {
        "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_212713_24_8M",
        "interval": 10,
        "group_flows": 3,
        "dumbbell_pairs": 24
    }, 
    {
        "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_211607_24_8M",
        "interval": 10,
        "group_flows": 3,
        "dumbbell_pairs": 24
    }, 
    # {
    #     "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_200859_great",
    #     "interval": 10,
    #     "group_flows": 2,
    #     "dumbbell_pairs": 12
    # }, 
    # {
    #     "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_195847_great",
    #     "interval": 10,
    #     "group_flows": 2,
    #     "dumbbell_pairs": 14
    # }, 
    {
        "data_dir": "../../data/conv16_udp_dumbbell_multiflow_sugon_kvm/20220509_194721_great",
        "interval": 10,
        "group_flows": 2,
        "dumbbell_pairs": 16
    }
]

iperf_parser = IperfParser()
percent_max = 0
percent_min = 100

for exp_data in exp_datas:
    exp_data_dir = exp_data["data_dir"]
    flow_enter_interval = exp_data["interval"]
    group_flows = exp_data["group_flows"]
    dumbbell_pairs = exp_data["dumbbell_pairs"]
    group_num = int(dumbbell_pairs / group_flows)

    fairness_indexes = []
    for project in project_names:
        for measure_side in measure_sides:
            id = 1
            flow_rates = []

            while True:
                file_path = exp_data_dir + '/' + \
                            FILE_PATTERN  % (project, measure_side, id)
                if not os.path.exists(file_path):
                    break

                group_id = int((id + group_flows - 1) / group_flows)
                lasting_time = ((group_num-1)*2+1-(group_id-1)*2 )*flow_enter_interval
                lasting_time = int(lasting_time)

                iperf_data = iperf_parser.iperf_parse(file_path)
                bandwidth_list = iperf_data.get_bandwidth_list(unit='Mbps', 
                                                            begin=0, end=2*lasting_time+1)
                
                # get bandwidth when all flows is active
                left_strip = (group_num - group_id) * flow_enter_interval
                left_index = 2*left_strip
                right_index = 2*left_strip+2*flow_enter_interval+1
                bandwidth_list = bandwidth_list[left_index:right_index]
                
                avg_rate = sum(bandwidth_list) / len(bandwidth_list)
                flow_rates.append(avg_rate)

                id = id + 1

            fairness = get_fairness_index(flow_rates)
            fairness_indexes.append(fairness)
        
    increase_percent = (fairness_indexes[1]-fairness_indexes[0]) * 100 / \
                        fairness_indexes[0]
    percent_max = max(percent_max, increase_percent)
    percent_min = min(percent_min, increase_percent)
    print(dumbbell_pairs, fairness_indexes[0], 
          fairness_indexes[1], increase_percent)

print("fairness increase percent: %.2f - %.2f" % (percent_min, percent_max))