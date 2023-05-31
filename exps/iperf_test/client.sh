#!/bin/bash
cd $(dirname $0)
iperf -c 10.1.1.1 -i 1.0   -t 20   > ../../data2/iperf_test/20221228_152936/client_tcp_AFQ.txt
