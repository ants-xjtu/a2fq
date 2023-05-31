#!/bin/bash
#
# Run convergence test of dumbbell topology, with parameters 
# set in parameters.sh.
# Author: Guangyu Peng (gypeng2021@163.com)

set -e
cd $(dirname $0)
WORK_DIR=$(pwd)
DATA_DIR="exp_data_dir"
PROJECT_NAME="project_name"
TOPO_GEN="../../utils/topo_generators/dumbbell_generator.py"
TOPO_JSON="dumbbell-topo/topology.json"
EXP_TYPE="DumbbellExp"

# Import parameters and libs
source parameters

# Experiment data directory
if [ ! -d ${exp_data_dir} ]; then
  mkdir -p ${exp_data_dir}
fi 
cp ./parameters ${exp_data_dir}
echo ${exp_data_dir} > ${DATA_DIR}
echo ${flow_enter_interval} > flow_enter_interval
echo ${dumbbell_pairs} > dumbbell_pairs

# Calculate mininet waiting time
mininet_wait=$[( (dumbbell_pairs-1)*2+1 )*flow_enter_interval + 30]
#echo ${mininet_wait}

# Do experiments for each project
for project_dir in ${exp_projects[@]}; do
  project_dir=$(dirname ${project_dir}/tmp)
  project_name=${project_dir##*/}
  echo ${project_name} > ${PROJECT_NAME}

  # generate topology
  ${TOPO_GEN} -p ${dumbbell_pairs} -d ${link_delay} -b ${link_bandwidth} -l ${project_dir}

  # generate Makefile
  cat > ${project_dir}/Makefile << EOF
BMV2_SWITCH_EXE = simple_switch_grpc
TOPO = ${TOPO_JSON}
run_args += --disable_debug --no_pcap --exp ${EXP_TYPE} 
run_args += --wait ${mininet_wait} --script_dir ${WORK_DIR}

include ../../utils/Makefile
EOF
  sleep 2

  # start mininet and do experiment
  cd ${project_dir}
  make run
  sleep 1
  make stop
  sleep 60
  cd ${WORK_DIR}
done

echo "[run.sh]: Exp data saved in $(cd ${exp_data_dir}; pwd)"
