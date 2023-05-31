#!/usr/bin/env python3
#
# Plot convergence graph of convergence exp data.
# Author: Guangyu Peng (gypeng2021@163.com)

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from lib.iperf_data import *
from lib.iperf_parser import IperfParser
from lib.libplot import *
from lib.csv_utils import write_csv

FILE_PATTERN = '%s_%s_%d'
EXP_DATA_DIR_FILE = './exp_data_dir'
FLOW_ENTER_INTERVAL_FILE = './flow_enter_interval'
DUMBBELL_PAIRS_FILE = './dumbbell_pairs'
GROUP_FLOWS_FILE = './group_flows'
PAPER_DATA_DIR = '../../data_paper_convergence'
project_names = ['AFQ', 'A2FQ']
#project_names = ['basic']
measure_sides = ['server']
exp_data_dir = None
flow_enter_interval = None
dumbbell_pairs = None
group_flows = None
y_min = None
y_max = None
wide = False

with open(EXP_DATA_DIR_FILE, 'r', encoding='utf-8') as f:
    exp_data_dir = f.readline()
    if exp_data_dir[-1] == '\n':
        exp_data_dir = exp_data_dir[0:-1]

with open(FLOW_ENTER_INTERVAL_FILE, 'r', encoding='utf-8') as f:
    flow_enter_interval = f.readline()
    if flow_enter_interval[-1] == '\n':
        flow_enter_interval = flow_enter_interval[0:-1]
    flow_enter_interval = int(flow_enter_interval)

with open(GROUP_FLOWS_FILE, 'r', encoding='utf-8') as f:
    group_flows = f.readline()
    if group_flows[-1] == '\n':
        group_flows = group_flows[0:-1]
    group_flows = int(group_flows)

with open(DUMBBELL_PAIRS_FILE, 'r', encoding='utf-8') as f:
    dumbbell_pairs = f.readline()
    if dumbbell_pairs[-1] == '\n':
        dumbbell_pairs = dumbbell_pairs[0:-1]
    dumbbell_pairs = int(dumbbell_pairs)

group_num = int(dumbbell_pairs / group_flows)

def sum_bandwidth_lists(bandwidth_lists: list):
    if len(bandwidth_lists) == 0:
        return []
    result = bandwidth_lists[0]
    #print(len(result))
    for i in range(1, len(bandwidth_lists)):
        #print(len(bandwidth_lists[i]))
        tmp_len = len(bandwidth_lists[i])
        res_len = len(result)
        if res_len < tmp_len:
            result = result + [0.0 for i in range(tmp_len-res_len)]
        for j in range(tmp_len):
            result[j] = result[j] + bandwidth_lists[i][j]
    return result

iperf_parser = IperfParser()
for project in project_names:
    for measure_side in measure_sides:
        convergence_plotter = ConvergencePlotter(y_min=y_min, y_max=y_max, wide=wide)
        id = 1
        bandwidth_lists = []
        real_time_list = []
        while True:
            file_path = exp_data_dir + '/' + \
                        FILE_PATTERN  % (project, measure_side, id)
            if not os.path.exists(file_path):
                break

            group_id = int((id + group_flows - 1) / group_flows)
            offset = (group_id-1) * flow_enter_interval
            lasting_time = ((group_num-1)*2+1-(group_id-1)*2 )*flow_enter_interval
            lasting_time = int(lasting_time)
            
            #offset = 0.0
            print(file_path)
            iperf_data = iperf_parser.iperf_parse(file_path)
            time_list = iperf_data.get_end_time_nums(begin=0, end=2*lasting_time+1, 
                                                     offset=offset)
            time_list = [offset] + time_list
            # print(time_list)
            bandwidth_list = iperf_data.get_bandwidth_list(unit='Mbps', 
                                                           begin=0, end=2*lasting_time+1)
            bandwidth_list = [0.0] + bandwidth_list
            bandwidth_list[-1] = 0.0
            bandwidth_lists.append(bandwidth_list)

            if len(time_list) > len(real_time_list):
                real_time_list = time_list

            if id % group_flows == 0:
                bandwidth_sum = sum_bandwidth_lists(bandwidth_lists)
                convergence_plotter.add_flow(
                    real_time_list, bandwidth_sum, id, group_flows
                )
                # csv_rows_list = []
                # for x, y in zip(real_time_list, bandwidth_sum):
                #     csv_rows_list.append([x, y])
                # flow_start = id - group_flows + 1
                # label = 'flow%d-%d' % (flow_start, id)
                # csv_file_path = PAPER_DATA_DIR + '/%s-%s-goodput.csv' % (project, label)
                # write_csv(filepath=csv_file_path,
                #           title=['Time(s)', 'Goodput(Mbps)'],
                #           rows_list=csv_rows_list)

                bandwidth_lists = []
                real_time_list = []
            id = id + 1
        fig_path = exp_data_dir + '/%s_%s.png' % (project, measure_side)
        print(fig_path)
        convergence_plotter.save_fig(fig_path)
