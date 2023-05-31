# Author: Guangyu Peng (gypeng2021@163.com)
from multiprocessing import Pool
from time import sleep

from mininet_exp_lib.exp_base import ExpBase

class IperfTest(ExpBase):
    CLIENT_SCRIPT = 'client.sh'
    SERVER_SCRIPT = 'server.sh'
    def __init__(self, mininet, host_num: int):
        super().__init__(mininet, host_num)

    def run_exp(self, exp_dir: str, duration: int):
        with Pool(processes=1) as server_pool:
            server_pool.starmap(
                self.host_process, 
                [((self.host_num >> 1) + 1, 
                  exp_dir+self.SERVER_SCRIPT+' &')]
            )
            sleep(1)
            with Pool(processes=1) as client_pool:
                client_pool.starmap(
                    self.host_process,
                    [(1, exp_dir+self.CLIENT_SCRIPT+' &')]
                )
        print('[IperfTest]: waiting for {}s...'.format(duration))
        sleep(duration)
        print('[IperfTest]: IperfTest finished!')