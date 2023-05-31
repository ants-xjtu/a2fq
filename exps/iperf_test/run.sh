#!/bin/bash
#
# Run iperf_test, with parameters set in parameters.sh.
# Author: Guangyu Peng (gypeng2021@163.com)

set -e
cd $(dirname $0)
WORK_DIR=$(pwd)
DATA_DIR="exp_data_dir"
TOPO_GEN="../../utils/topo_generators/dumbbell_generator.py"
TOPO_JSON="dumbbell-topo/topology.json"
EXP_TYPE="IperfTest"
CLIENT_SCRIPT="client.sh"
SERVER_SCRIPT="server.sh"

# Import parameters and libs
source parameters
source ../lib/dumbbell.sh

# Experiment data directory
if [ ! -d ${exp_data_dir} ]; then
  mkdir -p ${exp_data_dir}
fi 
cp ./parameters ${exp_data_dir}
echo ${exp_data_dir} > ${DATA_DIR}

# Do experiments for each project
for project_dir in ${exp_projects[@]}; do
  project_dir=$(dirname ${project_dir}/tmp)
  project_name=${project_dir##*/}
  # echo ${project_name}
  
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
  
  # generate server and client scripts for iperf UDP test
  cat > ${SERVER_SCRIPT} << EOF
#!/bin/bash
cd \$(dirname \$0)
iperf -s -u -i ${iperf_test_gap} \
  > ${exp_data_dir}/server_udp_${project_name}.txt
EOF
  cat > ${CLIENT_SCRIPT} << EOF
#!/bin/bash
cd \$(dirname \$0)
iperf -c $(dumbbell::server_ip 1) -u -i ${iperf_test_gap} \
  -t ${iperf_total_time} -b ${iperf_udp_bandwith} \
  > ${exp_data_dir}/client_udp_${project_name}.txt
EOF

  # start mininet and do experiment
  cd ${project_dir}
  make run
  sleep 1
  make stop
  sleep 60
  cd ${WORK_DIR}

  # generate server and client scripts for iperf TCP test
  cat > ${SERVER_SCRIPT} << EOF
#!/bin/bash
cd \$(dirname \$0)
iperf -s -i ${iperf_test_gap} \
  > ${exp_data_dir}/server_tcp_${project_name}.txt
EOF
  cat > ${CLIENT_SCRIPT} << EOF
#!/bin/bash
cd \$(dirname \$0)
iperf -c $(dumbbell::server_ip 1) -i ${iperf_test_gap} \
  -t ${iperf_total_time} \
  > ${exp_data_dir}/client_tcp_${project_name}.txt
EOF

  # start mininet and do experiment
  cd ${project_dir}
  make run
  sleep 1
  make stop
  sleep 60
  cd ${WORK_DIR}
done

echo "[run.sh]: Exp data saved in $(cd ${exp_data_dir}; pwd)"
