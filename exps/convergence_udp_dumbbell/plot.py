#!/usr/bin/env python3
#
# Plot convergence graph of convergence exp data.
# Author: Guangyu Peng (gypeng2021@163.com)

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from lib.iperf_data import *
from lib.iperf_parser import IperfParser
from lib.libplot import *

FILE_PATTERN = '%s_%s_%d'
EXP_DATA_DIR_FILE = './exp_data_dir'
FLOW_ENTER_INTERVAL_FILE = './flow_enter_interval'
DUMBBELL_PAIRS_FILE = './dumbbell_pairs'
project_names = ['AFQ', 'A2FQ']
#project_names = ['basic']
measure_sides = ['server']
exp_data_dir = None
flow_enter_interval = None
dumbbell_pairs = None
y_min = -0.5
y_max = None

with open(EXP_DATA_DIR_FILE, 'r', encoding='utf-8') as f:
    exp_data_dir = f.readline()
    if exp_data_dir[-1] == '\n':
        exp_data_dir = exp_data_dir[0:-1]

with open(FLOW_ENTER_INTERVAL_FILE, 'r', encoding='utf-8') as f:
    flow_enter_interval = f.readline()
    if flow_enter_interval[-1] == '\n':
        flow_enter_interval = flow_enter_interval[0:-1]
    flow_enter_interval = int(flow_enter_interval)

with open(DUMBBELL_PAIRS_FILE, 'r', encoding='utf-8') as f:
    dumbbell_pairs = f.readline()
    if dumbbell_pairs[-1] == '\n':
        dumbbell_pairs = dumbbell_pairs[0:-1]
    dumbbell_pairs = int(dumbbell_pairs)

iperf_parser = IperfParser()
for project in project_names:
    for measure_side in measure_sides:
        convergence_plotter = ConvergencePlotter(y_min=y_min, y_max=y_max)
        id = 1
        while True:
            file_path = exp_data_dir + '/' + \
                        FILE_PATTERN  % (project, measure_side, id)
            if not os.path.exists(file_path):
                break

            offset = (id-1) * flow_enter_interval
            lasting_time=((dumbbell_pairs-1)*2+1-(id-1)*2)*flow_enter_interval
            #offset = 0.0
            iperf_data = iperf_parser.iperf_parse(file_path)
            time_list = iperf_data.get_end_time_nums(begin=0, end=lasting_time*2+1, 
                                                     offset=offset)
            time_list = [offset] + time_list
            # print(time_list)
            bandwidth_list = iperf_data.get_bandwidth_list(unit='Mbps', 
                                                           begin=0, end=lasting_time*2+1)
            bandwidth_list = [0.0] + bandwidth_list
            bandwidth_list[-1] = 0.0
            # print(bandwidth_list)
            convergence_plotter.add_flow(time_list, bandwidth_list, id)
            id = id + 1
        fig_path = exp_data_dir + '/%s_%s.png' % (project, measure_side)
        print(fig_path)
        convergence_plotter.save_fig(fig_path)
