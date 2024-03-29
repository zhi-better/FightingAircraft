import argparse
import json
import queue
import random
import threading
import time
import pygame

from utils.SocketTcpTools import *
from utils.cls_airplane import *
from utils.cls_game_data import CommandType


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


class IDAllocator:
    def __init__(self):
        self.next_available_id = 1
        self.used_ids = set()

    def allocate_id(self):
        # 分配玩家 ID
        player_id = self.next_available_id
        self.used_ids.add(player_id)

        # 更新下一个可用的 ID
        while self.next_available_id in self.used_ids:
            self.next_available_id += 1

        return player_id

    def release_id(self, player_id):
        # 释放玩家 ID
        if player_id in self.used_ids:
            self.used_ids.remove(player_id)

    def get_next_available_id(self):
        # 获取下一个可用的 ID，不分配
        return self.next_available_id


class FightingAircraftGameServer:
    def __init__(self):
        self.room_max_player_number = 1
        self.room_info_map = {}                 # 房间和玩家 id 的 map
        self.matching_queue = queue.Queue()     # 所有目前正在匹配队列等待的玩家 id
        self.player_id_2_player_info = {}       # 从 id 到玩家其他信息的 map
        self.tcp_client_2_player_id = {}        # 从 tcp 连接到玩家 id 的 map
        self.server = TcpSererTools(get_ipv4_address(), port=4444)
        self.server.start()
        self.server.set_callback_fun(self.server_callback)
        self.clock = pygame.time.Clock()
        self.player_id_allocator = IDAllocator()
        self.room_id_allocator = IDAllocator()
        self.time_stamp = 0
        # self.update_frame_data = {"command": CommandType.cmd_frame_update.value,
        #                           'time_stamp': self.time_stamp,
        #                           "actions": []}
        self.lock = threading.Lock()

        # self.server_start()

    def server_callback(self, cmd, param):
        """
        服务器的处理函数
        :param data:
        :return:
        """
        self.lock.acquire()
        if cmd == CallbackCommand.RecvData:
            data = param['data']
            tcp_client = param['tcp_client']

            data = json.loads(data.decode())
            cmd = CommandType(data['command'])
            data_resp = {}
            if cmd == CommandType.cmd_login:
                data_resp['command'] = CommandType.cmd_login_resp.value
                new_player_id = self.player_id_allocator.allocate_id()

                # 保存玩家和对应的发送端口
                data_resp['player_id'] = new_player_id
                # data_resp['room_max_player_number'] = self.room_max_player_number
                self.tcp_client_2_player_id[tcp_client] = new_player_id
                self.player_id_2_player_info[new_player_id] = \
                    {'tcp_client': tcp_client, 'plane_name': data['plane_name']}
                self.matching_queue.put(new_player_id)
                self.server.send(tcp_client, data=json.dumps(data_resp),
                                 pack_data=True, data_type=DataType.TypeString)
                # self.server.send(server.tcp_clients[0], data=json.dumps(data_resp), pack_data=True, data_type=DataType.TypeString)

                if self.matching_queue.qsize() >= self.room_max_player_number:
                    start_data = {"command": CommandType.cmd_matching_successful.value,
                                  'sync_time_stamp': 0,
                                  'map_id': int(random.random() * 36 + 1),
                                  "planes": []}
                    # 准备好所有待发送数据
                    room_number = self.room_id_allocator.allocate_id()
                    room_player_tcp_list = []
                    for idx in range(self.room_max_player_number):
                        player_id = self.matching_queue.get()
                        info = self.player_id_2_player_info[player_id]
                        # 此处引用传递，已经将 self.player_id_2_player_info[player_id] 内容修改了
                        info['room_number'] = room_number
                        room_player_tcp_list.append(
                            self.player_id_2_player_info[player_id]['tcp_client'])
                        start_data["planes"].append(
                            {"player_id": player_id,
                             # "position_x": random.random() * 5000,
                             # "position_y": random.random() * 5000,
                             # 'plane_name': info['plane_name']
                             "position_x": 2000,
                             "position_y": 2000,
                             'plane_name': info['plane_name']
                             })

                    self.room_info_map[room_number] = {'tcp_list': room_player_tcp_list,
                                                       'sync_time_stamp': 0,
                                                       'actions': {}}
                    # 给所有的匹配成功的客户端发送消息
                    for client in room_player_tcp_list:
                        self.server.send(
                            tcp_socket=client,
                            data=json.dumps(start_data),
                            pack_data=True,
                            data_type=DataType.TypeString)
                else:
                    # 此处需要通知其他在匹配队列的玩家目前人数更新
                    start_data = {"command": CommandType.cmd_matching_state_change.value,
                                  'room_max_player_number': self.room_max_player_number,
                                  "queue_current_players": self.matching_queue.qsize()}
                    # 给每一个等待的玩家实时通知此时的匹配消息
                    for player_id in self.matching_queue.queue:
                        self.server.send(
                            self.player_id_2_player_info[player_id]['tcp_client'],
                            data=json.dumps(start_data),
                            pack_data=True,
                            data_type=DataType.TypeString)

            elif cmd == CommandType.cmd_player_action:
                player_id = data['player_id']
                room_number = self.player_id_2_player_info[player_id]['room_number']
                actions = self.room_info_map[room_number]['actions']
                actions[player_id] = data['action']
            elif cmd == CommandType.cmd_game_over:
                data = param['data']

                data = json.loads(data.decode())
                player_id = data['player_id']
                # 首先找到房间号
                room_number = self.player_id_2_player_info[player_id]['room_number']
                # 删除房间
                del self.room_info_map[room_number]
                print('the number of room[{}] has been removed, room remaining: {}.'.format(
                    room_number, len(list(self.room_info_map.keys()))))
            else:
                print(data)
        elif cmd == CallbackCommand.SocketClose:
            tcp_client = param
            player_id = self.tcp_client_2_player_id[tcp_client]
            # 首先需要判断它是否仍在匹配队列
            if player_id in self.matching_queue.queue:
                self.matching_queue.queue.remove(player_id)
                # 此处需要通知其他在匹配队列的玩家目前人数更新
                start_data = {"command": CommandType.cmd_matching_state_change.value,
                              'room_max_player_number': self.room_max_player_number,
                              "queue_current_players": self.matching_queue.qsize()}
                # 给每一个等待的玩家实时通知此时的匹配消息
                for player_id in self.matching_queue.queue:
                    self.server.send(
                        self.player_id_2_player_info[player_id]['tcp_client'],
                        data=json.dumps(start_data),
                        pack_data=True,
                        data_type=DataType.TypeString)
            else:
                if player_id in self.player_id_2_player_info:
                    room_number = self.player_id_2_player_info[player_id]['room_number']
                    # 首先判断他在哪个房间，如果房间没人了，直接把房间删了，否则就发送通知，某玩家离线
                    room_info = self.room_info_map[room_number]
                    room_info['tcp_list'].remove(tcp_client)
                    player_left_number = len(room_info['tcp_list'])
                    print('player_id: {} has offline, the room_number: {} has left {} players.'.format(
                        player_id, room_number, player_left_number))
                    if player_left_number == 0:
                        del self.room_info_map[room_number]
                        print('the number of room[{}] has been removed, room remaining: {}.'.format(
                            room_number, len(list(self.room_info_map.keys()))))

                    # 删除这两个用户
                    del self.player_id_2_player_info[player_id]

                del self.tcp_client_2_player_id[tcp_client]

        # 释放线程锁
        self.lock.release()

    def server_start(self):
        frame_update_template = {'command': CommandType.cmd_frame_update.value,
                                 'actions': {},
                                 'sync_time_stamp': 0}

        print('server tick 10FPS!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
        while True:
            old_time = time.time()
            self.lock.acquire()
            # 此处的逻辑是一个房间一个房间的发
            for key in list(self.room_info_map.keys()):
                room_info = self.room_info_map[key]
                frame_update_template['actions'] = room_info['actions']
                frame_update_template['sync_time_stamp'] = room_info['sync_time_stamp']
                for client in room_info['tcp_list']:
                    self.server.send(client,
                                     data=json.dumps(frame_update_template),
                                     pack_data=True,
                                     data_type=DataType.TypeString)
                room_info['sync_time_stamp'] += 1

            self.lock.release()

            # 保证服务器以 30FPS 的速度转播玩家操作
            self.clock.tick(10)

            # print('\rserver FPS: {}'.format(1/(time.time()-old_time + 1e-10)), end='')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fighting Aircraft Game Server')
    parser.add_argument('--room-max-player-number', default=1,
                        help='set the server room max player number')

    args = parser.parse_args()

    # if args.start_server:
    #     start_server()
    # elif args.other_command:
    #     process_other_command()
    # else:
    #     print('Invalid command. Use --start-server or --other-command.')
    server = FightingAircraftGameServer()
    server.room_max_player_number = int(args.room_max_player_number)
    server.room_max_player_number = 1
    server.server_start()

