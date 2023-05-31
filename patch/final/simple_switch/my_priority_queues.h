/* Copyright 2013-present Barefoot Networks, Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/*
 * Guangyu Peng (gypeng2021@163.com)
 *
 */

//! @file my_priority_queues.h
//! This file defines a template class of priority queues in all out ports.
//! when pushing a packet, we need to set specific port id with specific queue id (qid);
//! when popping a packet, we need to set a worker_id which identifies an egress worker thread
//! (every port is mapped to a specific worker thread), the worker thread evenly choose a port
//! to pop packet.
//! Within an out port, each queue has a strict priority, by default queue[0] has the highest priority,
//! we can also set the id of queue with highest priority for an out port, i.e. rotate priority,
//! when setting queue[i] with highest priority, queue[i+1] has the second highest priority, 
//! queue[i-1] has the lowest priority

#ifndef SIMPLE_SWITCH_MY_PRIORITY_QUEUES_H_
#define SIMPLE_SWITCH_MY_PRIORITY_QUEUES_H_

#include <algorithm>  // for std::make_pair
#include <condition_variable>
#include <deque>
#include <mutex>
#include <queue>
#include <unordered_map>
#include <vector>

template <typename T, typename FMap>
class MyPriorityQueues {
  using MutexType = std::mutex;
  using LockType = std::unique_lock<MutexType>;

 public:
  //! Initiate priority queues. 
  //!
  //! Parameters
  //!   \p nb_workers: number of worker threads.
  //!   \p capacity: default capacity of each queue, which can be
  //!                changed later.
  //!   \p map_to_worker: a function object mapping port_id to worker_id([0, nb_workers-1]).
  //!   \p nb_priorities: number of multi priority queues in each port, 
  //!                     queue_id should in range [0, nb_priorities-1].
  MyPriorityQueues(size_t nb_workers, size_t capacity,
                   FMap map_to_worker, size_t nb_priorities = 2)
      : nb_workers(nb_workers),
        capacity(capacity),
        map_to_worker(std::move(map_to_worker)),
        nb_priorities(nb_priorities),
        mutex(nb_workers),
        workers_info(nb_workers) { }

  //! Push an item into a specific priority queue.
  //!
  //! If priority queue \p queue_id of port \p port_id is full, the
  //! function will return `0` immediately. Otherwise, \p item will be copied to
  //! the queue and the function will return `1`. 
  //!
  //! Exceptions 
  //! If \p port_id or \p queue_id are incorrect, an exception of type 
  //! std::out_of_range will be thrown (same if the FMap object provided to 
  //! the constructor does not behave correctly).
  int push_front(size_t port_id, size_t queue_id, const T &item) {
    size_t worker_id = map_to_worker(port_id);
    LockType lock(mutex.at(worker_id));
    auto &worker_info = workers_info.at(worker_id);
    check_worker_info(port_id, &worker_info);
    auto &port_info = worker_info.ports_info.at(port_id);
    auto &q_capacities = port_info.queue_capacities;
    auto &pri_queues = port_info.pri_queues;
    if (pri_queues.at(queue_id).size() >= q_capacities.at(queue_id))
      return 0;
    pri_queues.at(queue_id).emplace_front(item);
    ++port_info.port_size;
    ++worker_info.size;
    worker_info.q_not_empty.notify_one();
    return 1;
  }

  int push_front(size_t port_id, const T &item) {
    return push_front(port_id, 0, item);
  }

  //! Same as push_front(size_t port_id, size_t queue_id, const T &item), but
  //! \p item is moved instead of copied.
  int push_front(size_t port_id, size_t queue_id, T &&item) {
    size_t worker_id = map_to_worker(port_id);
    LockType lock(mutex.at(worker_id));
    auto &worker_info = workers_info.at(worker_id);
    check_worker_info(port_id, &worker_info);
    auto &port_info = worker_info.ports_info.at(port_id);
    auto &q_capacities = port_info.queue_capacities;
    auto &pri_queues = port_info.pri_queues;
    if (pri_queues.at(queue_id).size() >= q_capacities.at(queue_id))
      return 0;
    pri_queues.at(queue_id).emplace_front(std::move(item));
    ++port_info.port_size;
    ++worker_info.size;
    worker_info.q_not_empty.notify_one();
    return 1;
  }

  int push_front(size_t port_id, T &&item) {
    return push_front(port_id, 0, std::move(item));
  }

  //! Retrieves an element for the worker thread indentified by \p worker_id and
  //! moves it to \p pItem. The id of the port which contained this element is 
  //! copied to \p port_id and the qid of the served queue is copied to \p queue_id.
  //! 
  //! Elements are retrieved evenly from all ports this worker thread arranges.
  //! In each port, the queue with highest priority (which can be set by 
  //! rotate_priority method) are served first.
  //!
  //! If no elements are available, the function will block.
  //!
  //! Exceptions
  //! If \p worker_id not in range [0, nb_workers-1], an exception of type 
  //! std::out_of_range will be thrown.
  void pop_back(size_t worker_id, size_t *port_id, size_t *queue_id,
                T *pItem) {
    LockType lock(mutex.at(worker_id));
    auto &worker_info = workers_info.at(worker_id);
    while (worker_info.size == 0) {
      worker_info.q_not_empty.wait(lock);
    }
    size_t nports = worker_info.ports_id.size();
    for (size_t p_cnt = 0; p_cnt < nports; ++p_cnt) {
      size_t pid = next_port(&worker_info);
      auto &port_info = worker_info.ports_info.at(pid);
      if (port_info.port_size == 0) continue;
      for (size_t q_cnt = 0; q_cnt < nb_priorities; ++q_cnt) {
        size_t qid = (port_info.highest_pri_queue+q_cnt) % nb_priorities;
        auto &queue = port_info.pri_queues.at(qid);
        if (queue.size() == 0) continue;
        *port_id = pid;
        *queue_id = qid;
        *pItem = std::move(queue.back());
        queue.pop_back();
        --port_info.port_size;
        --worker_info.size;
        break;
      }
      break;
    }
  }

  void pop_back(size_t worker_id, size_t *port_id, T *pItem) {
    size_t queue_id;
    return pop_back(worker_id, port_id, &queue_id, pItem);
  }

  //! Get the total occupancies of all the priority queues for 
  //! the port identified by \p port_id.

  //! Exceptions 
  //! If the FMap object are incorrect, an exception of type 
  //! std::out_of_range will be thrown.
  size_t size(size_t port_id) const {
    size_t worker_id = map_to_worker(port_id);
    LockType lock(mutex.at(worker_id));
    auto &worker_info = workers_info.at(worker_id);
    auto &ports_info = worker_info.ports_info;
    if(ports_info.find(port_id) == ports_info.end()) return 0;
    auto &port_info = ports_info.at(port_id);
    return port_info.port_size;
  }
  
  //! Get the occupancy of priority queue \p queue_id for
  //! the port with id \p port_id.
  //!
  //! Exceptions 
  //! If \p queue_id are incorrect, an exception of type 
  //! std::out_of_range will be thrown (same if the FMap object provided to 
  //! the constructor does not behave correctly).
  size_t size(size_t port_id, size_t queue_id) const {
    size_t worker_id = map_to_worker(port_id);
    LockType lock(mutex.at(worker_id));
    auto &worker_info = workers_info.at(worker_id);
    auto &ports_info = worker_info.ports_info;
    if(ports_info.find(port_id) == ports_info.end()) return 0;
    auto &port_info = ports_info.at(port_id);
    return port_info.pri_queues.at(queue_id).size();
  }

  //! Set the capacity \p c of all the priority queues for 
  //! the port identified by \p port_id.
  //!
  //! Exceptions 
  //! If the FMap object is incorrect, an exception of type 
  //! std::out_of_range will be thrown.
  void set_capacity(size_t port_id, size_t c) {
    size_t worker_id = map_to_worker(port_id);
    LockType lock(mutex.at(worker_id));
    auto &worker_info = workers_info.at(worker_id);
    check_worker_info(port_id, &worker_info);
    auto &port_info = worker_info.ports_info.at(port_id);
    SetCapacityFn fn(c);
    for (size_t i = 0; i < nb_priorities; i++) {
      fn(i, port_info);
    }
  }

  //! Set the capacity \p c of priority queue \p queue_id for
  //! the port with id \p port_id.
  //!
  //! Exceptions 
  //! If \p queue_id are incorrect, an exception of type 
  //! std::out_of_range will be thrown (same if the FMap object provided to 
  //! the constructor does not behave correctly).
  void set_capacity(size_t port_id, size_t queue_id, size_t c) {
    size_t worker_id = map_to_worker(port_id);
    LockType lock(mutex.at(worker_id));
    auto &worker_info = workers_info.at(worker_id);
    check_worker_info(port_id, &worker_info);
    auto &port_info = worker_info.ports_info.at(port_id);
    SetCapacityFn fn(c);
    fn(queue_id, port_info);
  }

  //! @deprecated This method does nothing now.
  //! Set the capacity \c of all priority queues for all ports.
  void set_capacity_for_all(size_t c) {
    // empty block
  }

  //! Set the highest priority queue \p queue_id for the port \p port_id.
  //! If \p queue_id not in range [0, nb_priorities-1], this method does nothing.
  //!
  //! Exceptions
  //! If FMap object does not behave correctly, an exception of type 
  //! std::out_of_range will be thrown.
  void rotate_priority(size_t port_id, size_t queue_id) {
    if (queue_id >= nb_priorities) return;
    size_t worker_id = map_to_worker(port_id);
    LockType lock(mutex.at(worker_id));
    auto &worker_info = workers_info.at(worker_id);
    check_worker_info(port_id, &worker_info);
    auto &port_info = worker_info.ports_info.at(port_id);
    port_info.highest_pri_queue = queue_id;
  }

  //! Get queue id of the highest priority queue for the port \p port_id.
  //! 
  //! Exceptions
  //! If FMap object does not behave correctly, an exception of type 
  //! std::out_of_range will be thrown.
  size_t get_highest_pri_qid(size_t port_id) const {
    size_t worker_id = map_to_worker(port_id);
    LockType lock(mutex.at(worker_id));
    auto &worker_info = workers_info.at(worker_id);
    auto &ports_info = worker_info.ports_info;
    if(ports_info.find(port_id) == ports_info.end()) return 0;
    auto &port_info = ports_info.at(port_id);
    return port_info.highest_pri_queue;
  }

  //! Deleted copy constructor
  MyPriorityQueues(const MyPriorityQueues &) = delete;
  //! Deleted copy assignment operator
  MyPriorityQueues &operator =(const MyPriorityQueues &) = delete;
  //! Deleted move constructor
  MyPriorityQueues(MyPriorityQueues &&) = delete;
  //! Deleted move assignment operator
  MyPriorityQueues &operator =(MyPriorityQueues &&) = delete;

 private:
  struct PortInfo {
    PortInfo(size_t priorities, size_t capacity)
        : queue_capacities(priorities, capacity),
          pri_queues(priorities) { }

    std::vector<size_t> queue_capacities;
    std::vector<std::deque<T>> pri_queues;
    size_t highest_pri_queue{0};
    size_t port_size{0};
  };

  struct SetCapacityFn {
    explicit SetCapacityFn(size_t c)
        : c(c) { }

    void operator ()(size_t qid, PortInfo &info) const {
      info.queue_capacities.at(qid) = c;
    }

    size_t c;
  };

  struct WorkerInfo {
    mutable std::condition_variable q_not_empty{};
    // port_id to PortInfo
    std::unordered_map<size_t, PortInfo> ports_info;
    std::vector<size_t> ports_id;
    size_t next_index{0};
    size_t size{0};
  };

  void check_worker_info(size_t port_id, WorkerInfo *w_info) {
    if(w_info->ports_info.find(port_id) == w_info->ports_info.end()) {
      w_info->ports_id.push_back(port_id);
      w_info->ports_info.insert(
          std::make_pair(port_id, PortInfo(nb_priorities, capacity)));
    }
  }

  size_t next_port(WorkerInfo *w_info) {
    size_t index = w_info->next_index;
    // You should make sure ports_id.size() != 0 when calling this method
    w_info->next_index = (w_info->next_index+1) % w_info->ports_id.size();
    return w_info->ports_id.at(index);
  }
  
  mutable std::vector<MutexType> mutex;
  size_t nb_workers;
  size_t nb_priorities;
  size_t capacity;
  FMap map_to_worker;
  std::vector<WorkerInfo> workers_info;
};

#endif // SIMPLE_SWITCH_MY_PRIORITY_QUEUES_H_