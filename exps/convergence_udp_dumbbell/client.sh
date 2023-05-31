#!/bin/bash
#
# Server script, used for convergence test of dumbbell topology.
# Author: Guangyu Peng (gypeng2021@163.com)

cd $(dirname $0)

# Import parameters
source parameters
source ../lib/general.sh
source ../lib/dumbbell.sh
DATA_DIR_FILE="exp_data_dir"
PROJECT_NAME_FILE="project_name"

# Host id
if [ $(is_nonnegative $1) = "N" ]; then
  exit 1
fi
host_id=$[$1]
if [ $[host_id] -le 0 -o \
     $[host_id] -gt $[dumbbell_pairs] ]; then
  exit 1
fi

# Data file path
read DATA_DIR_PATH < ${DATA_DIR_FILE}
read project_name < ${PROJECT_NAME_FILE}
data_file_path=${DATA_DIR_PATH}/${project_name}_${client_data_prefix}
data_file_path=${data_file_path}${host_id}

# Compute waiting time before starting iperf,
# and the duration of flow after starting iperf.
waiting_time=$[(host_id-1)*flow_enter_interval]
lasting_time=$[( (dumbbell_pairs-1)*2+1-(host_id-1)*2 )*flow_enter_interval]
#waiting_time=0
#lasting_time=${flow_enter_interval}
# echo ${waiting_time} ${lasting_time}

# Wait and start iperf tcp client
sleep ${waiting_time}
iperf -u -c $(dumbbell::server_ip ${host_id}) -i ${iperf_test_gap} \
  -t ${lasting_time} -b ${udp_bandwidth} > ${data_file_path}
