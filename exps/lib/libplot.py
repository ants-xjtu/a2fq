#!/usr/bin/env python3
#
# Classes for plotting exp graph.
# Author: Guangyu Peng (gypeng2021@163.com)

import matplotlib.pyplot as plt

plt.rc('font', family='Times New Roman')
plt.rcParams['font.size'] = 12

class ConvergencePlotter:
    def __init__(self, y_min=None, y_max=None, wide=False):
        # self.x_list = []
        # self.y_list = []
        # self.flow_ids = []
        if wide:
            plt.figure(figsize=(10, 5))
        else:
            plt.figure()
        self.line_style = ['-', '--', '-.', ':']
        if y_min is not None and y_max is not None:
            axes = plt.gca()
            axes.set_ylim([y_min, y_max])

    def __get_line_style(self, id):
        if id >= len(self.line_style):
            return '--'
        else:
            return self.line_style[id]
    
    def add_flow(self, x, y, flow_id, group_flows=None):
        if group_flows is None or group_flows == 1:
            plt.plot(x, y, marker='.', linestyle=self.__get_line_style(flow_id),
                ms=1, label='flow-%d' % flow_id)
        else:
            flow_start = flow_id - group_flows + 1
            plt.plot(x, y, marker='.', linestyle=self.__get_line_style(flow_id),
                ms=1, label='flow %d-%d' % (flow_start, flow_id))

    def save_fig(self, path, dpi=600):
        plt.xlabel('Time (s)')
        plt.ylabel('Goodput (Mbps)')
        plt.legend(loc='upper center')
        plt.savefig(path, dpi=dpi)

class FairnessPlotter:
    def __init__(self):
        plt.figure()

    def plot(self, x, y_list, legend_list, marker_list):
        for y, legend, marker in zip(y_list, legend_list, marker_list):
            plt.plot(x, y, marker=marker, ms=5, label=legend)

    def save_fig(self, path, dpi=600):
        plt.xlabel('Number of Flows')
        plt.ylabel("Jain's fairness index")
        plt.legend()
        plt.savefig(path, dpi=dpi)