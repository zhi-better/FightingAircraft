import time

from utils.SocketTcpTools import TcpClientTools


def callback_recv(data):
    print(data)


if __name__ == '__main__':
    # server = TcpSererTools('127.0.0.1', port=4444)
    # server.start()
    client = TcpClientTools()
    client.set_callback_fun(callback_recv)
    client.connect_to_server('127.0.0.1', 4444)

