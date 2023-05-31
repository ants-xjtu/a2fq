#!/bin/bash
#
# Server script, used for convergence test of dumbbell topology.
# Author: Guangyu Peng (gypeng2021@163.com)

cd $(dirname $0)

# Import parameters
source parameters
source ../lib/general.sh
DATA_DIR_FILE="exp_data_dir"
PROJECT_NAME_FILE="project_name"

# Host id
if [ $(is_nonnegative $1) = "N" ]; then
  exit 1
fi
host_id=$[$1]
if [ $[host_id] -le $[dumbbell_pairs] -o \
     $[host_id] -gt $[2*dumbbell_pairs] ]; then
  exit 1
fi

# Data file path
read DATA_DIR_PATH < ${DATA_DIR_FILE}
read project_name < ${PROJECT_NAME_FILE}
data_file_path=${DATA_DIR_PATH}/${project_name}_${server_data_prefix}
data_file_path=${data_file_path}$[${host_id}-${dumbbell_pairs}]
# echo ${data_file_path}
# Start iperf tcp server
iperf -s -u -i ${iperf_test_gap} > ${data_file_path}