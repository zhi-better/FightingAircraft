import time

import pygame

from utils.SocketTcpTools import *
from utils.cls_airplane import *

global_data = InputState.NoInput.to_bytes(2, 'big')

def server_callback(data):
    """
    服务器的处理函数
    :param data:
    :return:
    """
    global global_data
    global_data = data
    # print(data)


if __name__ == '__main__':
    server = TcpSererTools('127.0.0.1', port=4444)
    server.start()
    server.set_callback_fun(server_callback)
    clock = pygame.time.Clock()


    while True:
        # 保证服务器以 30FPS 的速度转播玩家操作
        clock.tick(30)

        for client in server.tcp_clients:
            server.send(client, data=global_data, pack_data=True, data_type=DataType.TypeBinary)




