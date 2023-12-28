import socket
import struct
import sys
import threading
import time
from enum import Enum

import numpy as np

from PyQt5.QtWidgets import QApplication


class DataType(Enum):
    TypeNone = b'\0'
    TypeInteger = b'\1'
    TypeFloat = b'\2'
    TypeString = b'\3'
    TypeBinary = b'\4'

class FrameInfo:
    def __init__(self):
        self.data_type = None
        self.data_all_length = 0
        self.data_recv_length = 0
        self.data_buffer = b''

    def set_buffer_data(self, data):
        self.data_buffer = data

    def set(self, data_type, data_all_length):
        self.data_type = data_type
        self.data_all_length = data_all_length
        self.data_recv_length = 0

    def reset(self):
        self.data_type = None
        self.data_all_length = 0
        self.data_recv_length = 0
        self.data_buffer = b''


class TcpBaseTools:
    def __init__(self):
        self.callback_fun = None
        self.start_thread = None
        self.buffer_size = 1024
        # 表示对应协议头的协议类型为：
        # byte(frame header 1)+byte(frame header 2)+byte(cmd)+int(data length)
        self.header_bytes = b'\x0a\x0b'  # 占用两个字节
        self.header_format = "2ssi"
        self.header_length = 8
        self.tcp_socket = None
        self.connect_state = False
        self.frame_info = FrameInfo()
        self.tcp_clients = []

        # 先创建一个socket
        self.socket_init()

    def socket_init(self):
        """
        初始化创建一个socket
        :return:
        """
        # 1 创建服务端套接字对象
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def set_callback_fun(self, func):
        """
        设置程序的回调函数，主要用于主程序处理经过解码后的原始数据
        :param func: 回调函数地址
        :return:
        """
        self.callback_fun = func


    def process_protocol(self, header):
        """
        处理数据包的头部数据，返回值的第二个内容为解码后的结构体
        :param header: 头部原始数据
        :return:
        """
        header_unpack = struct.unpack(self.header_format, header)
        if header_unpack[0] == self.header_bytes:
            return True, header_unpack
        else:
            return False, None

    def process_raw_data(self, recv_data, tcp_client):
        """
        处理接收到的原始数据，核心代码
        :param recv_data:
        :return:
        """
        '''
        关于操作：
            本函数应该具有递归功能，否则无法处理复杂任务
        关于消息接收的逻辑处理：
        1. 首先判断当前是否已经接收过帧头 (self.frame_info.data_type is not None)
            接收过：
                根据帧头的数据长度接收对应的数据体内容
            没接收过：
            判断当前接收的数据长度是否满足帧头的长度
                满足：尝试解析
                    解析失败：正常传输数据
                    解析成功：如果有其他的数据，继续接收处理后续的数据
                不满足：将本次数据输出，丢弃此次的数据 !!!
        '''
        # 如果已经接收过数据头，直接继续接收内容
        if self.frame_info.data_type is not None:
            # 首先计算剩余的数据包长度
            recv_len_left = self.frame_info.data_all_length - self.frame_info.data_recv_length
            # 然后计算本次可以接收的数据长度，选取数据长度和剩余接收长度的最小值
            recv_len_real = min(recv_len_left, len(recv_data))
            self.frame_info.data_buffer += recv_data[:recv_len_real]
            # 更新对应的接收的数据长度
            self.frame_info.data_recv_length = len(self.frame_info.data_buffer)
            # 判断当前是否已经接受完本帧的内容
            if self.frame_info.data_recv_length >= self.frame_info.data_all_length:
                # 根据回调函数返回对应的内容
                if self.callback_fun is not None:
                    self.callback_fun(self.frame_info.data_buffer, tcp_client)
                else:
                    print('no callback function, recv data: {}'.format(self.frame_info.data_buffer))
                # 从剩余的数据中尝试检索出对应的数据头
                # 首先更新 recv_data 的数据的内容
                # print(self.frame_info.data_buffer)
                self.frame_info.reset()
                recv_data = recv_data[recv_len_real:len(recv_data)]
                if len(recv_data) != 0:
                    self.process_raw_data(recv_data, tcp_client)
            else:
                return
            # 从剩余的数据中尝试解析数据头
        else:
            if len(recv_data) >= self.header_length:
                ret = self.process_protocol(recv_data[:self.header_length])
                if ret[0]:
                    # 打印出协议对应的内容
                    # print(ret[1])
                    self.frame_info.set(ret[1][1], ret[1][2])
                    # 此处还得继续判断当前是否转换完了，如果没有的话需要继续转换接收到的内容
                    recv_data = recv_data[self.header_length:len(recv_data)]
                    if len(recv_data) != 0:
                        self.process_raw_data(recv_data, tcp_client)
                else:
                    print(recv_data)
            else:
                print(recv_data)

    def pack_data(self, data, data_type=DataType.TypeNone):
        """
        对发送数据进行打包，打包数据包括
        :param data: 打包原始数据
        :param data_type: 数据类型: DataType.xxx
        :return:
        """
        if data_type == DataType.TypeString:
            data = data.encode()
        data_pack = struct.pack(self.header_format, self.header_bytes, data_type.value, len(data))
        # print("datalen:{}".format(len(data)))
        return data_pack + data


    def client_process(self, tcp_client, tcp_client_address):
        """
        主要用于接受 socket 的消息线程
        :param tcp_client: tcp 连接
        :param tcp_client_address:  tcp 地址，包含 ip 和 port
        :return:
        """
        # 5 循环接收和发送数据
        while True:
            try:
                recv_data = tcp_client.recv(self.buffer_size)
            except ConnectionResetError:
                print("socket: {} has closed, it has been remove from the connection pool. ".format(
                    tcp_client_address))
                tcp_client.close()
                self.connect_state = False
                if tcp_client in self.tcp_clients:
                    self.tcp_clients.remove(tcp_client)
                return
            except ConnectionAbortedError:
                print("socket: {} has closed, it has been remove from the connection pool. ".format(
                    tcp_client_address))
                tcp_client.close()
                self.connect_state = False
                if tcp_client in self.tcp_clients:
                    self.tcp_clients.remove(tcp_client)
                return

            # 另外编写函数处理对应的内容
            self.process_raw_data(recv_data, tcp_client)


class TcpSererTools(TcpBaseTools):
    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.max_connections = 128

    # 开始的线程函数，外部最好调用 start() 函数，不要调用此函数
    # 否则会阻塞
    def bind_and_listen(self):
        """
        服务器进行绑定和监听的函数
        :return:
        """
        host = self.host
        port = self.port
        # signal_update.emit(0.2, 1, 1, 'socket object created...')
        # 设置端口复用，使程序退出后端口马上释放
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        # 2 绑定端口
        self.tcp_socket.bind((host, port))
        # signal_update.emit(0.7, 1, 1, "socket bind successfully...")
        print('server port bind successfully, server host: {}, server port: {}...'.format(
            host, port))

        print("server_thread started. ")
        # 3 设置监听
        self.tcp_socket.listen(self.max_connections)
        print('start to listen connections from client, max client count: {}'.format(
            self.max_connections))
        # 4 循环等待客户端连接请求（也就是最多可以同时有128个用户连接到服务器进行通信）
        while True:
            tcp_client_1, tcp_client_address = self.tcp_socket.accept()
            self.tcp_clients.append(tcp_client_1)
            # 创建多线程对象
            thd = threading.Thread(target=self.client_process,
                                   args=(tcp_client_1, tcp_client_address), daemon=True)
            # 设置守护主线程  即如果主线程结束了 那子线程中也都销毁了  防止主线程无法退出
            thd.setDaemon(True)
            # 启动子线程对象
            thd.start()
            print("new client connected, client address: {}, total client count: {}".format(tcp_client_address, 1))

    # 启动服务器
    def start(self):
        """
        服务器的启动线程，由于服务器监听线程阻塞，此函数单独创建一个线程用于接收客户端的连接
        :return:
        """
        self.start_thread = threading.Thread(target=self.bind_and_listen, daemon=True)
        self.start_thread.start()
        print("starting server_thread...")

    def get_client(self, client_idx):
        """
        获取服务器的某一个 client 的 socket 连接
        :param client_idx:
        :return:
        """
        if client_idx >= len(self.tcp_clients):
            print('unavailable client_idx, client_count: {}'.format(len(self.tcp_clients)))
            return None
        else:
            return self.tcp_clients[client_idx]

    def send(self, tcp_socket, data, pack_data=False, data_type=DataType.TypeNone):
        """
        向客户端发送数据
        :param data_type:
        :param pack_data:
        :param tcp_socket:
        :param data:
        :return:
        """
        if pack_data:
            data = self.pack_data(data=data, data_type=data_type)
        try:
            if tcp_socket:
                tcp_socket.send(data)
        except Exception as e:
            self.tcp_clients.remove(tcp_socket)
            tcp_socket.close()
            # self.tcp_socket = None
            print(e)

class TcpClientTools(TcpBaseTools):
    def __init__(self):
        super().__init__()

    def connect_to_server(self, host, port):
        """
        连接到 tcp 服务器
        :param host:
        :param port:
        :return:
        """
        try:
            print("connecting to server")
            self.tcp_socket.connect((host, port))
        except ConnectionRefusedError as e:
            print(e)
            return False
        self.connect_state = True
        print("connected to server successfully. ")
        self.start_thread = threading.Thread(
            target=self.client_process, args=(self.tcp_socket, f'{host}:{port}'), daemon=True)
        self.start_thread.start()

        return True

    def send(self, data, pack_data=False, data_type=DataType.TypeNone):
        """
        向客户端发送数据
        :param pack_data:
        :param tcp_socket:
        :param data:
        :return:
        """
        if pack_data:
            data = self.pack_data(data=data, data_type=data_type)
        try:
            if self.connect_state:
                self.tcp_socket.send(data)
        except OSError as e:
            self.tcp_socket.close()
            self.tcp_socket = None
            self.connect_state = False
            print(e)


if __name__ == '__main__':
    server = TcpSererTools('127.0.0.1', port=4444)
    server.start()

    # client = TcpClientTools()
    # client.connect_to_server('127.0.0.1', 4444)

    time.sleep(100)
