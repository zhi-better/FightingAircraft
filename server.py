import json
import time

import pygame

from main import CommandType
from utils.SocketTcpTools import *
from utils.cls_airplane import *


def get_ipv4_address():
    try:
        # 获取主机名
        host_name = socket.gethostname()

        # 获取主机名对应的 IPv4 地址
        ip_address = socket.gethostbyname(host_name)

        return ip_address
    except socket.error as e:
        print(f"Error occurred: {e}")
        return None


class PlayerIDAllocator:
    def __init__(self):
        self.next_available_id = 1
        self.used_ids = set()

    def allocate_player_id(self):
        # 分配玩家 ID
        player_id = self.next_available_id
        self.used_ids.add(player_id)

        # 更新下一个可用的 ID
        while self.next_available_id in self.used_ids:
            self.next_available_id += 1

        return player_id

    def release_player_id(self, player_id):
        # 释放玩家 ID
        if player_id in self.used_ids:
            self.used_ids.remove(player_id)

    def get_next_available_id(self):
        # 获取下一个可用的 ID，不分配
        return self.next_available_id


class FightingAircraftGameServer:
    def __init__(self):
        self.server = TcpSererTools(get_ipv4_address(), port=4444)
        self.server.start()
        self.server.set_callback_fun(self.server_callback)
        self.clock = pygame.time.Clock()
        self.allocator = PlayerIDAllocator()
        self.player_map = {}
        self.time_stamp = 0
        self.update_frame_data = {"command": CommandType.cmd_frame_update.value,
                                  'time_stamp': self.time_stamp,
                                  "actions": []}

        self.server_start()

    def server_callback(self, data, tcp_client):
        """
        服务器的处理函数
        :param data:
        :return:
        """
        data = json.loads(data.decode())
        print(data)
        cmd = CommandType(data['command'])
        data_resp = {}
        if cmd == CommandType.cmd_login:
            data_resp['command'] = CommandType.cmd_login_resp.value
            data_resp['player_id'] = self.allocator.allocate_player_id()

            # 保存玩家和对应的发送端口
            self.player_map[data_resp['player_id']] = tcp_client
            self.server.send(tcp_client, data=json.dumps(data_resp), pack_data=True, data_type=DataType.TypeString)
            # self.server.send(server.tcp_clients[0], data=json.dumps(data_resp), pack_data=True, data_type=DataType.TypeString)

            if len(self.player_map.keys()) > 1:
                start_data = {"command": CommandType.cmd_matching_successful.value,
                              'time_stamp': 0,
                              'map_id': 5,
                              "planes": []}
                for key in self.player_map.keys():
                    start_data["planes"].append({"player_id": key, "position_x": 1000, "position_y": 1000})

                for client in self.server.tcp_clients:
                    self.server.send(client,
                                data=json.dumps(start_data),
                                pack_data=True,
                                data_type=DataType.TypeString)

                self.time_stamp = 0
        elif cmd == CommandType.cmd_player_action:
            action_data = {'player_id': data['player_id'], 'action': data['action']}
            self.update_frame_data["actions"].append(action_data)
        else:
            print(data)


    def server_start(self):
        while True:
            # 保证服务器以 30FPS 的速度转播玩家操作
            self.clock.tick(30)
            if len(self.server.tcp_clients):
                for client in self.server.tcp_clients:
                    self.server.send(client, data=json.dumps(self.update_frame_data), pack_data=True,
                                data_type=DataType.TypeString)
                # 清空用户操作，更新时间戳
                self.update_frame_data["actions"].clear()
                self.time_stamp += 1
                self.update_frame_data['time_stamp'] = self.time_stamp


if __name__ == '__main__':
    server = FightingAircraftGameServer()
