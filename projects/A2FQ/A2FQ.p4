/* -*- P4_16 -*- */
#include <core.p4>
#include <v1model.p4>

#define PKT_INSTANCE_TYPE_EGRESS_CLONE 2
#define PKT_INSTANCE_TYPE_INGRESS_RECIRC 4

typedef bit<64> bufferSize_t;
typedef int<3> alphaExp_t;
typedef bit<3> alphaShift_t;
typedef bit<5> qid_t;
typedef bit<64> bid_t;
typedef bit<256> sketchLine_t;    // 4(hashes) * 64(bit)
typedef bit<64> round_t;
typedef bit<6> qNum_t;

/*************************************************************************
*********************** P A R A M E T E R S  *****************************
*************************************************************************/

const bufferSize_t MAX_BUFFER_SIZE = 204800;  // Bytes
const alphaExp_t ALPHA_EXP = 0;               // alpha is 2^(ALPHA_EXP)

const bit<32> MAX_PORT = 64;     // valid port : [0, MAX_PORT-1]
const qNum_t QUEUE_NUM = 32;    // qid: [0, QUEUE_NUM-1]

const bit<8> BPR_EXP = 11;     // bpr is 2^(BPR_EXP) Bytes
const bit<32> BUCKETS = 4096;  // # of buckets in sketch 

const bid_t INT_MAX = 18446744073709551615;     // 2^64 - 1

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/
const bit<16> TYPE_IPV4 = 0x800;
const bit<8> TYPE_TCP = 6;
const bit<8> TYPE_UDP = 17;

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<8>    diffserv;
    bit<16>   totalLen;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

header tcp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<3>  res;
    bit<3>  ecn;
    bit<6>  ctrl;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

header udp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<16> len;
    bit<16> checksum;
}

struct metadata {
    @field_list(0) bufferSize_t buffer_out;
    @field_list(0) bit<32> q_buffer_index;
    @field_list(0) bufferSize_t q_buffer_out;
    bufferSize_t q_buffer_in;
    bufferSize_t buffer_in;
    round_t cur_round;
    bufferSize_t dt_threshold;
    bid_t bid_val;
    bit<1> is_cur_queue_empty;
    bit<1> drop_flag;
    qNum_t q_num;
}

struct headers {
    ethernet_t   ethernet;
    ipv4_t       ipv4;
    tcp_t        tcp;
    udp_t        udp;
}

/*************************************************************************
*********************** P A R S E R  ***********************************
*************************************************************************/

parser MyParser(packet_in packet,
                out headers hdr,
                inout metadata meta,
                inout standard_metadata_t standard_metadata) {

    state start {
        transition parse_ethernet;
    }

    state parse_ethernet {
        packet.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4: parse_ipv4;
            default: accept;
        }
    }

    state parse_ipv4 {
        packet.extract(hdr.ipv4);
        transition select(hdr.ipv4.protocol) {
            TYPE_TCP: parse_tcp;
            TYPE_UDP: parse_udp;
            default: accept;
        }
    }

    state parse_tcp {
        packet.extract(hdr.tcp);
        transition accept;
    }

    state parse_udp {
        packet.extract(hdr.udp);
        transition accept;
    }
}


/*************************************************************************
************   C H E C K S U M    V E R I F I C A T I O N   *************
*************************************************************************/

control MyVerifyChecksum(inout headers hdr, inout metadata meta) {   
    apply {  }
}


/*************************************************************************
**************  I N G R E S S   P R O C E S S I N G   *******************
*************************************************************************/
bid_t max_bid(in bid_t left, in bid_t right) {
  return left > right ? left : right;
}

bid_t min_bid(in bid_t left, in bid_t right) {
  return left < right ? left : right;
}

control MyIngress(inout headers hdr,
                  inout metadata meta,
                  inout standard_metadata_t standard_metadata) {
    action drop() {
        mark_to_drop(standard_metadata);
    }
    
    action ipv4_forward(macAddr_t dstAddr, egressSpec_t port) {
        hdr.ipv4.ttl = hdr.ipv4.ttl - 1;
        hdr.ethernet.srcAddr = hdr.ethernet.dstAddr;
        hdr.ethernet.dstAddr = dstAddr;
        standard_metadata.egress_spec = port;
    }
    
    table ipv4_lpm {
        key = {
            hdr.ipv4.dstAddr: lpm;
        }
        actions = {
            ipv4_forward;
            drop;
        }
        size = 1024;
        default_action = drop();
    }
    
    /* Registers in Ingress pipeline */
    register<sketchLine_t>(MAX_PORT*BUCKETS) count_min_sketch;
    register<round_t>(MAX_PORT) round_reg;      // current round for each out port
    register<bufferSize_t>(1) buffer_in_reg;    // total bytes input to shared buffer
    register<bufferSize_t>(1) buffer_out_reg;   // total bytes output from shared buffer
    // total bytes input to each queue for each port
    register<bufferSize_t>(MAX_PORT*(bit<32>)QUEUE_NUM) q_buffer_in_reg;
    // total bytes output from each queue for each port
    register<bufferSize_t>(MAX_PORT*(bit<32>)QUEUE_NUM) q_buffer_out_reg;

    register<qNum_t>(MAX_PORT) queue_num_reg;   // active queues in each port
    register<bit<1>>(MAX_PORT) has_reduced_reg;

    action hash_i(out bit<32> ind1, out bit<32> ind2, out bit<32> ind3, out bit<32> ind4) {
        bit<32> srcIp = hdr.ipv4.srcAddr;
        bit<32> dstIp = hdr.ipv4.dstAddr;
        bit<8> proto = hdr.ipv4.protocol;
        bit<16> srcPort;
        bit<16> dstPort;
        srcPort = (proto == TYPE_TCP ? hdr.tcp.srcPort :
                   (proto == TYPE_UDP ? hdr.udp.srcPort : 0));
        dstPort = (proto == TYPE_TCP ? hdr.tcp.dstPort :
                   (proto == TYPE_UDP ? hdr.udp.dstPort : 0));
        hash(ind1, HashAlgorithm.crc32, (bit<32>)standard_metadata.egress_spec*(bit<32>)BUCKETS,
             {srcIp, dstIp, proto, srcPort, dstPort}, BUCKETS);
        hash(ind2, HashAlgorithm.crc16, (bit<32>)standard_metadata.egress_spec*(bit<32>)BUCKETS,
             {srcIp, dstIp, proto, srcPort, dstPort}, BUCKETS);
        hash(ind3, HashAlgorithm.csum16, (bit<32>)standard_metadata.egress_spec*(bit<32>)BUCKETS,
             {srcIp, dstIp, proto, srcPort, dstPort}, BUCKETS);
        hash(ind4, HashAlgorithm.identity, (bit<32>)standard_metadata.egress_spec*(bit<32>)BUCKETS,
             {srcIp, dstIp, proto, srcPort, dstPort}, BUCKETS);
    }

    action read_sketch(out bid_t val) {
        val = INT_MAX;
        bit<32> ind1;
        bit<32> ind2;
        bit<32> ind3;
        bit<32> ind4;
        hash_i(ind1, ind2, ind3, ind4);
        sketchLine_t tmp;
        count_min_sketch.read(tmp, ind1);
        val = min_bid(val, tmp[255:192]); 
        count_min_sketch.read(tmp, ind2);
        val = min_bid(val, tmp[191:128]);
        count_min_sketch.read(tmp, ind3);
        val = min_bid(val, tmp[127:64]);
        count_min_sketch.read(tmp, ind4);
        val = min_bid(val, tmp[63:0]);
    }

    action update_sketch(in bid_t val) {
        bit<32> ind1;
        bit<32> ind2;
        bit<32> ind3;
        bit<32> ind4;
        hash_i(ind1, ind2, ind3, ind4);
        sketchLine_t tmp;
        bid_t v1;
        bid_t v2;
        bid_t v3;
        bid_t v4;
        count_min_sketch.read(tmp, ind1);
        v1 = tmp[255:192];
        v2 = tmp[191:128];
        v3 = tmp[127:64];
        v4 = tmp[63:0];
        v1 = max_bid(v1, val);
        tmp = v1 ++ v2 ++ v3 ++ v4;
        count_min_sketch.write(ind1, tmp);
        count_min_sketch.read(tmp, ind2);
        v1 = tmp[255:192];
        v2 = tmp[191:128];
        v3 = tmp[127:64];
        v4 = tmp[63:0];
        v2 = max_bid(v2, val);
        tmp = v1 ++ v2 ++ v3 ++ v4;
        count_min_sketch.write(ind2, tmp);
        count_min_sketch.read(tmp, ind3);
        v1 = tmp[255:192];
        v2 = tmp[191:128];
        v3 = tmp[127:64];
        v4 = tmp[63:0];
        v3 = max_bid(v3, val);
        tmp = v1 ++ v2 ++ v3 ++ v4;
        count_min_sketch.write(ind3, tmp);
        count_min_sketch.read(tmp, ind4);
        v1 = tmp[255:192];
        v2 = tmp[191:128];
        v3 = tmp[127:64];
        v4 = tmp[63:0];
        v4 = max_bid(v4, val);
        tmp = v1 ++ v2 ++ v3 ++ v4;
        count_min_sketch.write(ind4, tmp);
    }

    action update_round_number() {
        round_reg.read(meta.cur_round, (bit<32>)standard_metadata.egress_spec);
        qid_t queue_id = (qid_t)(meta.cur_round) & (qid_t)(QUEUE_NUM-1);
        bit<19> queue_len;
        get_queue_length(standard_metadata.egress_spec, queue_id, queue_len);
        if (queue_len == 0) {
            meta.is_cur_queue_empty = 1;
            meta.cur_round = meta.cur_round + 1;
        }
        round_reg.write((bit<32>)standard_metadata.egress_spec, meta.cur_round);
    }

    action update_queue_number() {
        // Calculate dt threshold
        buffer_in_reg.read(meta.buffer_in, 0);
        buffer_out_reg.read(meta.buffer_out, 0);
        bufferSize_t avail_buffer = MAX_BUFFER_SIZE - (meta.buffer_in - meta.buffer_out);
        if(ALPHA_EXP >= 0) {
            meta.dt_threshold = avail_buffer << ((alphaShift_t)ALPHA_EXP);
        }
        else {
            meta.dt_threshold = avail_buffer >> ((alphaShift_t)(-ALPHA_EXP));
        }
        // Calculate q_high and q_low
        bufferSize_t q_low = meta.dt_threshold >> 4;
        bufferSize_t q_high = meta.dt_threshold > 6144 ? meta.dt_threshold - 6144 : 0;
        // Get q2 size
        round_t q2_round = meta.cur_round + 1; //- (round_t)meta.is_cur_queue_empty;
        qid_t q2_id = (qid_t)(q2_round) & (qid_t)(QUEUE_NUM-1);
        bit<32> q2_index = (bit<32>)((bit<32>)standard_metadata.egress_spec
                           * (bit<32>)QUEUE_NUM + (bit<32>)q2_id);
        bufferSize_t q2_buffer_in;
        bufferSize_t q2_buffer_out;
        q_buffer_in_reg.read(q2_buffer_in, q2_index);
        q_buffer_out_reg.read(q2_buffer_out, q2_index);
        bufferSize_t q2_size = q2_buffer_in - q2_buffer_out;
        // Update queue number
        bit<1> has_reduced;
        has_reduced_reg.read(has_reduced, (bit<32>)standard_metadata.egress_spec);
        queue_num_reg.read(meta.q_num, (bit<32>)standard_metadata.egress_spec);
        if(meta.q_num < 2) {
            meta.q_num = QUEUE_NUM;
        }
        if(q2_size > q_high) {
            if(has_reduced == 0) {
                if(meta.q_num > 2) {
                    meta.q_num = meta.q_num - 1;
                }
                has_reduced = 1;
            }
        }
        else if(q2_size < q_low && q2_size != 0) {
            if(meta.q_num < QUEUE_NUM) {
                meta.q_num = meta.q_num + 1;
            }
        }
        if(meta.is_cur_queue_empty == 1) {
            has_reduced = 0;
        }
        has_reduced_reg.write((bit<32>)standard_metadata.egress_spec, has_reduced);
        queue_num_reg.write((bit<32>)standard_metadata.egress_spec, meta.q_num);
    }

    action select_queue() {
        // Get bid number
        read_sketch(meta.bid_val);
        /// if flow hasn't sent in a while,
        /// bump it's round to current round.
        meta.bid_val = max_bid(meta.bid_val, (bid_t)(meta.cur_round << BPR_EXP));
        meta.bid_val = meta.bid_val + (bid_t)standard_metadata.packet_length;
        // Get packet sending round
        round_t pkt_round = (round_t)(meta.bid_val >> BPR_EXP);
        // If round too far ahead, drop pkt
        if(pkt_round-meta.cur_round >= (round_t)meta.q_num) {
            meta.drop_flag = 1;
        }
        standard_metadata.priority = (qid_t)pkt_round & (qid_t)(QUEUE_NUM-1);
    }

    action check_dt() {
        meta.q_buffer_index = (bit<32>)((bit<32>)standard_metadata.egress_spec
                              * (bit<32>)QUEUE_NUM + (bit<32>)standard_metadata.priority);
        q_buffer_in_reg.read(meta.q_buffer_in, meta.q_buffer_index);
        q_buffer_out_reg.read(meta.q_buffer_out, meta.q_buffer_index);
        // Check dt condition
        bufferSize_t packet_size = (bufferSize_t)standard_metadata.packet_length;
        bufferSize_t used_buffer = meta.buffer_in - meta.buffer_out;
        bufferSize_t used_q_buffer = meta.q_buffer_in - meta.q_buffer_out;
        if(used_buffer + packet_size > MAX_BUFFER_SIZE ||
           used_q_buffer + packet_size > meta.dt_threshold) {
            meta.drop_flag = 1;
        }
    }

    action update_buffer_in() {
        bufferSize_t packet_size = (bufferSize_t)standard_metadata.packet_length;
        meta.buffer_in = meta.buffer_in + packet_size;
        meta.q_buffer_in = meta.q_buffer_in + packet_size;
        buffer_in_reg.write(0, meta.buffer_in);
        q_buffer_in_reg.write(meta.q_buffer_index, meta.q_buffer_in);
    }

    action sync_buffer_out() {
        bufferSize_t old_buffer_out;
        bufferSize_t old_q_buffer_out;
        buffer_out_reg.read(old_buffer_out, 0);
        q_buffer_out_reg.read(old_q_buffer_out, meta.q_buffer_index);
        if(meta.buffer_out < old_buffer_out) {
            meta.buffer_out = old_buffer_out;
        }
        if(meta.q_buffer_out < old_q_buffer_out) {
            meta.q_buffer_out = old_q_buffer_out;
        }
        buffer_out_reg.write(0, meta.buffer_out);
        q_buffer_out_reg.write(meta.q_buffer_index, meta.q_buffer_out);
    }

    apply {
        // Packet is recirculated from egress pipeline
        if(standard_metadata.instance_type == PKT_INSTANCE_TYPE_INGRESS_RECIRC) {
            // Update reg data
            sync_buffer_out();
            drop();
        }
        // Packet is normal
        else {
            if(hdr.ipv4.isValid() && ipv4_lpm.apply().hit) {
                update_round_number();
                update_queue_number();
                select_queue();
                if(meta.drop_flag == 1) {
                    drop();
                }
                else {
                    update_sketch(meta.bid_val);
                    check_dt();
                    if(meta.drop_flag == 1) {
                        drop();
                    }
                    else {
                        update_buffer_in();
                    }
                }
            }   
            else {
                drop();
            }    
        }
    }
}

/*************************************************************************
****************  E G R E S S   P R O C E S S I N G   *******************
*************************************************************************/

control MyEgress(inout headers hdr,
                 inout metadata meta,
                 inout standard_metadata_t standard_metadata) {

    register<bufferSize_t>(1) buffer_out_reg;   // total bytes output from shared buffer
    // total bytes output from each queue for each port
    register<bufferSize_t>(MAX_PORT*(bit<32>)QUEUE_NUM) q_buffer_out_reg;

    action update_buffer_out() {
        buffer_out_reg.read(meta.buffer_out, 0);
        q_buffer_out_reg.read(meta.q_buffer_out, meta.q_buffer_index);
        meta.buffer_out = meta.buffer_out + (bufferSize_t)standard_metadata.packet_length;
        meta.q_buffer_out = meta.q_buffer_out + (bufferSize_t)standard_metadata.packet_length;
        buffer_out_reg.write(0, meta.buffer_out);
        q_buffer_out_reg.write(meta.q_buffer_index, meta.q_buffer_out);
    }

    action check_queue_empty(out bit<1> is_empty) {
        bit<19> queue_len;
        get_queue_length(standard_metadata.egress_port, standard_metadata.qid, queue_len);
        if(queue_len == 0) {
            is_empty = 1;
        }
        else {
            is_empty = 0;
        }
    }

    apply {
        // Packet is cloned from egress
        if(standard_metadata.instance_type == PKT_INSTANCE_TYPE_EGRESS_CLONE) {
            recirculate_preserving_field_list(0);
        }
        // Packet is normal
        else {
            update_buffer_out();
            bit<1> is_empty;
            check_queue_empty(is_empty);
            if(is_empty == 1) {
                qid_t queue_id = (standard_metadata.qid+1) & (qid_t)(QUEUE_NUM-1);
                rotate_priority(standard_metadata.egress_port, queue_id);
            }
            clone_preserving_field_list(CloneType.E2E, 5, 0);
        }
    }
}

/*************************************************************************
*************   C H E C K S U M    C O M P U T A T I O N   **************
*************************************************************************/

control MyComputeChecksum(inout headers hdr, inout metadata meta) {
     apply {
	    update_checksum(
            hdr.ipv4.isValid(),
            { 
                hdr.ipv4.version,
                hdr.ipv4.ihl,
                hdr.ipv4.diffserv,
                hdr.ipv4.totalLen,
                hdr.ipv4.identification,
                hdr.ipv4.flags,
                hdr.ipv4.fragOffset,
                hdr.ipv4.ttl,
                hdr.ipv4.protocol,
                hdr.ipv4.srcAddr,
                hdr.ipv4.dstAddr 
            },
            hdr.ipv4.hdrChecksum,
            HashAlgorithm.csum16
        );
    }
}


/*************************************************************************
***********************  D E P A R S E R  *******************************
*************************************************************************/

control MyDeparser(packet_out packet, in headers hdr) {
    apply {
        packet.emit(hdr.ethernet);
        packet.emit(hdr.ipv4);
        packet.emit(hdr.tcp);
        packet.emit(hdr.udp);
    }
}

/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

V1Switch(
MyParser(),
MyVerifyChecksum(),
MyIngress(),
MyEgress(),
MyComputeChecksum(),
MyDeparser()
) main;
