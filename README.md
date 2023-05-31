# A2FQ

A2FQ is an Adaptive Approximate Fair Queueing mechanism which considers shared-buffer in switches. A2FQ is adaptive to traffic dynamics by dynamically changing the number of effective queues according to traffic characteristics.

This repo contains our p4 implementation of A2FQ on [Bmv2](https://github.com/p4lang/behavioral-model), and evaluation scripts on mininet.

## Contents

* `patch`: patch code of bmv2 that implements Multi-priority queues and RSP scheduling.
* `projects`: p4 code on bmv2.
  * `projects/A2FQ`: p4 code of A2FQ on bmv2.
  * `projects/AFQ`: p4 code of AFQ on bmv2.
* `exps`: scripts of evaluating A2FQ on mininet.
  * `exps/iperf_test`: test iperf connectivity between two hosts.
  * `exps/convergence_udp_dumbbell`: convergence test of udp flows in dumbbell topology, start 1 flow each time.
  * `exps/convergence_udp_dumbbell_multiflow`: similar to `exps/convergence_udp_dumbbell`, except that it starts multiple flows each time.
* `utils`: helper code to run p4 applications on bmv2 and mininet.

## How to Use

### Prepare Environments

1. Install p4 software environments according to the [tutorial](https://github.com/p4lang/tutorials#to-build-the-virtual-machine).
2. Apply our patch to enable Multi-priority queues and RSP scheduling.
   ```shell
    cp patch/final/p4include/v1model.p4 /usr/local/share/p4c/p4include/
    cp patch/final/simple_switch/* <bmv2_src_dir>/targets/simple_switch/
   ```
3. Recompile and install bmv2.

### Run A2FQ interactively

```shell
cd projects/A2FQ
make run
make stop
```

### Run evaluation automatically

```shell
cd exps/iperf_test
./run.sh
```

## Contact

If you have any questions, contact [Danfeng Shan](https://dfshan.github.io/).