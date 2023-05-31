# Author: Guangyu Peng (gypeng2021@163.com)
from multiprocessing import Pool
from time import sleep

from mininet_exp_lib.exp_base import ExpBase

class DumbbellExp(ExpBase):
    CLIENT_SCRIPT = 'client.sh'
    SERVER_SCRIPT = 'server.sh'
    def __init__(self, mininet, host_num: int):
        super().__init__(mininet, host_num)

    def run_exp(self, exp_dir: str, duration: int):
        with Pool(processes=(self.host_num >> 1)) as server_pool:
            server_cmd_pattern = exp_dir + self.SERVER_SCRIPT + ' %d &'
            server_list = []
            for i in range((self.host_num>>1)+1, self.host_num+1):
                server_list.append((i, server_cmd_pattern % i))
            server_pool.starmap(self.host_process, server_list)
            sleep(5)
            with Pool(processes=(self.host_num >> 1)) as client_pool:
                client_cmd_pattern = exp_dir + self.CLIENT_SCRIPT + ' %d &'
                client_list = []
                for i in range(1, (self.host_num>>1)+1):
                    client_list.append((i, client_cmd_pattern % i))
                client_pool.starmap(self.host_process, client_list)
        print('[DumbbellExp]: waiting for {}s...'.format(duration))
        sleep(duration)
        print('[DumbbellExp]: DumbbellExp finished!')