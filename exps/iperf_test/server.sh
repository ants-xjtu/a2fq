#!/bin/bash
cd $(dirname $0)
iperf -s -i 1.0   > ../../data2/iperf_test/20221228_152936/server_tcp_AFQ.txt
