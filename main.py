import base64
import struct
import sys
import zlib

import pygame
import time
import xml.etree.ElementTree as ET
from PIL import Image
import numpy as np

def load_map(xml_file_path):
    # 读取XML文件
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    # 获取地图的宽度和高度
    width = int(root.attrib["width"])
    height = int(root.attrib["height"])
    # 获取瓦片宽度和高度
    tilewidth = int(root.attrib["tilewidth"])
    tileheight = int(root.attrib["tileheight"])
    # # 设置缩放比例
    # scaled_tilewidth = int(tilewidth * scale_factor)
    # scaled_tileheight = int(tileheight * scale_factor)

    # # 创建Pygame窗口
    # initial_window_size = (width * scaled_tilewidth, height * scaled_tileheight)
    # pygame.init()
    # screen = pygame.display.set_mode(initial_window_size)
    # pygame.display.set_caption("Tiled Map")

    # 解析图层数据
    data_element = root.find(".//layer/data")
    data_str = data_element.text.strip()
    data_bytes = base64.b64decode(data_str)
    data = zlib.decompress(data_bytes)

    # 将解压后的数据转换为列表
    tile_ids = list(struct.unpack("<" + "I" * (len(data) // 4), data))

    # 获取tileset中的tile元素，获取图像文件信息
    image_elem = root.find(".//tileset/image")
    image_source = "map/" + image_elem.get('source')

    return tile_ids, image_source, width, height, tilewidth, tileheight


def run_game():
    pygame.init()  # 初始化pygame
    scene_image = np.zeros((10240, 10240))

    size = 640, 640  # 设置窗口大小
    screen = pygame.display.set_mode(size)  # 显示窗口
    pygame.display.set_caption("FightingAircraft")
    color = (0, 0, 0)  # 设置颜色


    while True:
        for event in pygame.event.get():  # 遍历所有事件
            if event.type == pygame.QUIT:  # 如果单击关闭窗口，则退出
                pygame.quit()  # 退出pygame
                sys.exit(0)

        pygame.display.flip()  # 更新全部显示




if __name__ == '__main__':
    load_map(xml_file_path="map/map0.xml")
    run_game()

