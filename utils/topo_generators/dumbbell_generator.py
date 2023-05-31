#!/usr/bin/env python3
# Author: Guangyu Peng (gypeng2021@163.com)
from runtime_json import *
from topology_json import *
import argparse
import os

class DumbbellGenerator:
    """Generate configuration files of dumbbell topology for bmv2 p4 switch.
       
       Attributes:
           pairs : int              // number of host pairs in dumbbell topo
           delay : string           // link propagation delay
           location : string        // target directory to create dumbbell-topp/
           project_name : string    // P4 project name
           
           topology_json : TopologyJson
           s1_runtime_json : RuntimeJson
           s2_runtime_json : RuntimeJson 
    """
    DIRECT_NAME = 'dumbbell-topo/'
    TARGET = 'bmv2'
    P4INFO = 'build/%s.p4.p4info.txt'
    BMV2_JSON = 'build/%s.json'

    def __get_project_name(self):
        parts = self.location.rpartition('/')
        self.project_name = parts[-1]

    def __init__(self, pairs: int, delay: str, location: str, bandwidth: float):
        """Initialize some attributes to generate topology. 
           Use generate_topology() to do the real work.
        """
        self.pairs = pairs
        if self.pairs <= 0 or self.pairs > 250:
            raise ValueError('Argument pairs should be within [1, 250]')
        self.delay = delay
        self.location = location.rstrip('/').rstrip('\\')
        self.__get_project_name()
        self.bandwidth = bandwidth

    def generate_topology(self):
        self.create_topology_json()
        self.create_runtime_json()
        direct_path = self.location+'/'+self.DIRECT_NAME
        if not os.path.exists(direct_path):
            os.makedirs(direct_path)
        self.topology_json.save_json(direct_path+'topology.json')
        self.s1_runtime_json.save_json(direct_path+'s1-runtime.json')
        self.s2_runtime_json.save_json(direct_path+'s2-runtime.json')

    def create_topology_json(self):
        self.topology_json = TopologyJson()
        # sender hosts
        for i in range(1, 1+self.pairs):
            host = Host(name = 'h%d' % i)
            host.set_ip('10.0.%d.%d/24' % (i, i))
            host.set_mac('08:00:00:00:%.2x:%.2x' % (i, i))
            host.add_command('route add default gw 10.0.%d.254 dev eth0' % i)
            host.add_command(
                'arp -i eth0 -s 10.0.%d.254 08:00:00:00:%.2x:fe' % (i, i)
            )
            self.topology_json.hosts.add_host(host)
        # receiver hosts
        for i in range(1, 1+self.pairs):
            host = Host(name = 'h%d' % (i+self.pairs))
            host.set_ip('10.1.%d.%d/24' % (i, i))
            host.set_mac('08:00:00:01:%.2x:%.2x' % (i, i))
            host.add_command('route add default gw 10.1.%d.254 dev eth0' % i)
            host.add_command(
                'arp -i eth0 -s 10.1.%d.254 08:00:00:01:%.2x:fe' % (i, i)
            )
            self.topology_json.hosts.add_host(host)
        # switches
        switch1 = Switch(
            name = 's1', runtime_json=self.DIRECT_NAME+'s1-runtime.json'
        )
        switch2 = Switch(
            name = 's2', runtime_json=self.DIRECT_NAME+'s2-runtime.json'
        )
        self.topology_json.switches.add_switch(switch1)
        self.topology_json.switches.add_switch(switch2)
        # s1 links
        for i in range(1, 1+self.pairs):
            link = Link(lport='h%d' % i, 
                        rport='s1-p%d' % i, 
                        latency=self.delay,
                        bandwidth=self.bandwidth)
            self.topology_json.links.add_link(link)
        # s1-s2
        self.topology_json.links.add_link(
            Link(lport='s1-p0', rport='s2-p0', 
                 latency=self.delay, bandwidth=self.bandwidth)
        )
        # s2 links
        for i in range(1, 1+self.pairs):
            link = Link(lport='h%d' % (i+self.pairs), 
                        rport='s2-p%d' % i,
                        latency=self.delay,
                        bandwidth=self.bandwidth)
            self.topology_json.links.add_link(link)

    def __get_runtime_json(self, 
                           other_side_ip: str,
                           other_side_mask: int,
                           other_side_mac: str,
                           other_side_port: int,
                           dst_ip_pattern: str,
                           dst_mac_pattern: str
                           ) -> RuntimeJson:
        runtime_json = RuntimeJson(target=self.TARGET,
                                   p4info=self.P4INFO % self.project_name,
                                   bmv2_json=self.BMV2_JSON % self.project_name)
        # default table entry
        default_entry = TableEntry(table='MyIngress.ipv4_lpm')
        default_entry.set_default_action(True)
        default_entry.set_action_name('MyIngress.drop')
        default_entry.set_action_params({})
        runtime_json.add_table_entry(default_entry)
        # entry for host in the other side
        other_side_entry = TableEntry(table='MyIngress.ipv4_lpm')
        other_side_entry.set_match({
            'hdr.ipv4.dstAddr': [other_side_ip, other_side_mask]
        })
        other_side_entry.set_action_name(name='MyIngress.ipv4_forward')
        other_side_entry.set_action_params({
            'dstAddr': other_side_mac,
            'port': other_side_port
        })
        runtime_json.add_table_entry(other_side_entry)
        # entry for host in this side
        for i in range(1, 1+self.pairs):
            table_entry = TableEntry(table='MyIngress.ipv4_lpm')
            table_entry.set_match({
                'hdr.ipv4.dstAddr': [dst_ip_pattern % (i, i), 32]
            })
            table_entry.set_action_name(name='MyIngress.ipv4_forward')
            table_entry.set_action_params({
                'dstAddr': dst_mac_pattern % (i, i),
                'port': i
            })
            runtime_json.add_table_entry(table_entry)
        return runtime_json

    def create_runtime_json(self):
        self.s1_runtime_json = self.__get_runtime_json(
                                other_side_ip='10.1.0.0',
                                other_side_mask=16,
                                other_side_mac='08:00:00:01:00:00',
                                other_side_port=0,
                                dst_ip_pattern='10.0.%d.%d',
                                dst_mac_pattern='08:00:00:00:%.2x:%.2x'
                                )
        self.s2_runtime_json = self.__get_runtime_json(
                                other_side_ip='10.0.0.0',
                                other_side_mask=16,
                                other_side_mac='08:00:00:00:00:00',
                                other_side_port=0,
                                dst_ip_pattern='10.1.%d.%d',
                                dst_mac_pattern='08:00:00:01:%.2x:%.2x'
                                )

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--pairs', help='number of host pairs',
                        type=int, required=True)
    parser.add_argument('-d', '--delay', help='link propagation delay, i.e. 0.1ms',
                        type=str, required=False, default='0.1ms')
    parser.add_argument('-l', '--location', help='path to target directory',
                        type=str, required=True)
    parser.add_argument('-b', '--bandwidth', help='link bandwidth(Mbps)',
                        type=float, required=False, default=None)
    return parser.parse_args()

def main():
    args = get_args()
    dumbbell_generator = DumbbellGenerator(args.pairs, args.delay, 
                                           args.location, args.bandwidth)
    dumbbell_generator.generate_topology()
    print('[DumbbellGenerator]: Generated dumbbell-topo/ in %s' % args.location)

if __name__ == '__main__':
    # 输入：目标目录位置，哑铃拓扑中主机对数(最多250)，链路传播时延
    # 输出：目标目录位置下的dumbbell-topo文件夹，
    #      包括topology.json s1-runtime.json s2-runtime.json
    # senders_ip = ['10.0.1.1/24', '10.0.2.2/24', '10.0.3.3/24', '10.0.4.4/24']
    # gateway_ip = ['10.0.1.254/24', '10.0.2.254/24', '10.0.3.254/24', '10.0.4.254/24']
    # sender_mac = ['08:00:00:00:01:01', '08:00:00:00:02:02', '08:00:00:00:03:03']
    # gatewy_mac = ['08:00:00:00:01:FE', '08:00:00:00:02:FE', '08:00:00:00:03:FE']
    # gateway_port = [1, 2, 3, 4, 5]

    # joined_mac = ['08:00:00:00:00:00', '08:00:00:01:00:00']
    # joined_port = [0, 0]

    # receivs_ip = ['10.1.1.1/24', '10.1.2.2/24', '10.1.3.3/24', '10.1.4.4/24']
    # gateway_ip = ['10.1.1.254/24', '10.1.2.254/24', '10.1.3.254/24', '10.1.4.254/24']
    # receiv_mac = ['08:00:00:01:01:01', '08:00:00:01:02:02', '08:00:00:01:03:03']
    # gatewy_mac = ['08:00:00:01:01:FE', '08:00:00:01:02:FE', '08:00:00:01:03:FE']
    main()
