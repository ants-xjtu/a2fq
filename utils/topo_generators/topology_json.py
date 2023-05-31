# Author: Guangyu Peng (gypeng2021@163.com)
import json

class Host:
    def __init__(self, name: str, ip: str = '', mac: str = ''):
        self.__name = name
        self.__ip = ip
        self.__mac = mac
        self.__commands = []

    def set_ip(self, ip: str):
        self.__ip = ip

    def set_mac(self, mac: str):
        self.__mac = mac

    def add_command(self, command: str):
        self.__commands.append(command)

    def get_name(self) -> str:
        return self.__name

    def get_commands(self) -> list:
        return self.__commands

    def dump(self) -> dict:
        return {
            "ip": self.__ip,
            "mac": self.__mac,
            "commands": self.__commands
        }

class Switch:
    def __init__(self, name: str, runtime_json: str = ''):
        self.__name = name
        self.__runtime_json = runtime_json

    def set_runtime_json(self, runtime_json: str):
        self.__runtime_json = runtime_json
    
    def get_name(self) -> str:
        return self.__name

    def dump(self) -> dict:
        return { "runtime_json": self.__runtime_json }

class Link:
    def __init__(self, lport: str, rport: str, 
                 latency: str, bandwidth: float=None):
        self.__lport = lport
        self.__rport = rport
        self.__latency = latency
        self.__bandwidth = bandwidth

    def set_lport(self, lport: str):
        self.__lport = lport

    def set_rport(self, rport: str):
        self.__rport = rport

    def set_latency(self, latency: str):
        self.__latency = latency

    def set_bandwidth(self, bandwidth: float):
        """
        bandwidth: Mbps
        """
        self.__bandwidth = bandwidth

    def dump(self) -> list:
        if self.__bandwidth is None:
            return [self.__lport, self.__rport, self.__latency]
        else:
            return [self.__lport, self.__rport, 
                    self.__latency, self.__bandwidth]

class Hosts:
    def __init__(self):
        self.__hosts = []

    def add_host(self, host: Host):
        self.__hosts.append(host)

    def dump(self) -> dict:
        hosts_dict = {}
        for host in self.__hosts:
            hosts_dict[host.get_name()] = host.dump()
        return hosts_dict

class Switches:
    def __init__(self):
        self.__switches = []

    def add_switch(self, switch: Switch):
        self.__switches.append(switch)

    def dump(self) -> dict:
        switch_dict = {}
        for switch in self.__switches:
            switch_dict[switch.get_name()] = switch.dump()
        return switch_dict

class Links:
    def __init__(self):
        self.__links = []

    def add_link(self, link: Link):
        self.__links.append(link)

    def dump(self) -> list:
        link_list = []
        for link in self.__links:
            link_list.append(link.dump())
        return link_list

class TopologyJson:
    def __init__(self):
        self.hosts = Hosts()
        self.switches = Switches()
        self.links = Links()

    def save_json(self, path: str):
        dict = {
            'hosts': self.hosts.dump(),
            'switches': self.switches.dump(),
            'links': self.links.dump()
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(dict, f, indent=4)
    

if __name__ == '__main__':
    topo_json = TopologyJson()

    host1 = Host(name='h1')
    host1.set_ip('10.0.1.1/24')
    host1.set_mac('08:00:00:00:01:11')
    host1.add_command('route add default gw 10.0.1.10 dev eth0')
    host1.add_command('arp -i eth0 -s 10.0.1.10 08:00:00:00:01:00')
    print(host1.get_commands())
    topo_json.hosts.add_host(host1)
    host2 = Host(name='h2', ip='10.0.2.2/24', mac='08:00:00:00:02:22')
    host2.add_command('route add default gw 10.0.2.20 dev eth0')
    host2.add_command('arp -i eth0 -s 10.0.2.20 08:00:00:00:02:00')
    print(host2.get_commands())
    topo_json.hosts.add_host(host2)

    switch1 = Switch(name='s1', runtime_json='sig-topo/s1-runtime.json')
    topo_json.switches.add_switch(switch1)

    link1 = Link('h1', 's1-p1', '0.1ms')
    link2 = Link('h2', 's1-p2', '0.1ms')
    topo_json.links.add_link(link1)
    topo_json.links.add_link(link2)

    #topo_json.save_json('./topo.json')