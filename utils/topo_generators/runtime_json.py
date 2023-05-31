# Author: Guangyu Peng (gypeng2021@163.com)
import json

class TableEntry:
    def __init__(self, table: str):
        self.__entry = {'table': table}

    def set_default_action(self, default: bool):
        self.__entry['default_action'] = default

    def set_action_name(self, name: str):
        self.__entry['action_name'] = name

    def set_action_params(self, params: dict):
        self.__entry['action_params'] = params

    def set_match(self, matches: dict):
        self.__entry['match'] = matches

    def dump(self) -> dict:
        return self.__entry

class TableEntries:
    def __init__(self):
        self.__entries = []

    def add_table_entry(self, table_entry: TableEntry):
        self.__entries.append(table_entry)

    def dump(self) -> list:
        ret_list = []
        for entry in self.__entries:
            ret_list.append(entry.dump())
        return ret_list

class RuntimeJson:
    def __init__(self, target: str, p4info: str, bmv2_json: str):
        self.__target = target
        self.__p4info = p4info
        self.__bmv2_json = bmv2_json
        self.__table_entries = TableEntries()

    def set_target(self, target: str):
        self.__target = target

    def set_p4info(self, p4info: str):
        self.__p4info = p4info

    def set_bmv2_json(self, bmv2_json: str):
        self.__bmv2_json = bmv2_json

    def add_table_entry(self, table_entry: TableEntry):
        self.__table_entries.add_table_entry(table_entry)

    def save_json(self, path: str):
        dict = {
            'target': self.__target,
            'p4info': self.__p4info,
            'bmv2_json': self.__bmv2_json,
            'table_entries': self.__table_entries.dump(),
            'clone_session_entries': [
                {
                    'clone_session_id': 5,
                    'replicas': [
                        {
                            'egress_port': 100,
                            'instance': 1
                        }
                    ]
                }
            ]
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(dict, f, indent=4)

if __name__ == '__main__':
    runtime_json = RuntimeJson(target='bmv2', p4info='build/AFQ.p4.p4info.txt',
                               bmv2_json='build/AFQ.json')
    table_entry1 = TableEntry(table='MyIngress.ipv4_lpm')
    table_entry1.set_default_action(True)
    table_entry1.set_action_name('MyIngress.drop')
    table_entry1.set_action_params(params={})
    runtime_json.add_table_entry(table_entry1)
    table_entry2 = TableEntry(table='MyIngress.ipv4_lpm')
    table_entry2.set_match(matches={
        'hdr.ipv4.dstAddr': ['10.0.1.1', 32]
    })
    table_entry2.set_action_name(name='MyIngress.ipv4_forward')
    table_entry2.set_action_params(params={
        'dstAddr': '08:00:00:00:01:11',
        'port': 1
    })
    runtime_json.add_table_entry(table_entry2)
    # runtime_json.save_json('./runtime.json')