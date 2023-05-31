# Author: Guangyu Peng (gypeng2021@163.com)

exp_hosts = []

class ExpBase:
    def __init__(self, mininet, host_num: int):
        self.host_num = host_num
        exp_hosts.append(None)
        for i in range(1, 1+self.host_num):
            exp_hosts.append(mininet.get('h%d' % i))

    def host_process(self, host_id: int, command: str):
        exp_hosts[host_id].cmd(command)