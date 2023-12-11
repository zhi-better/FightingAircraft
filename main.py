import base64
import os
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

def get_rect_from_tile_id(tile_id, tile_width, tile_height):
    if tile_id != 0:
        rec_x = tile_id % 8 - 1
        if rec_x < 0:
            rec_x = 7
            rec_y = tile_id // 8 - 1
        else:
            rec_y = tile_id // 8
        tile_rect = pygame.Rect(rec_x * tile_width, rec_y * tile_height,
                                tile_width, tile_height)

    return tile_rect

def run_game():
    # # 首先加载都有哪些地图
    # num_xml_file = 0
    # for file in os.listdir('map'):
    #     if file.endswith(".xml"):
    #         num_xml_file += 1
    # for i in range(num_xml_file):
    #     print(f'{i}: map{i}.xml')
    #
    # idx = int(input('please select map to load: '))
    # select_map_name = f'map{idx}.xml'
    # print(select_map_name)
    # =========================================================================

    pygame.init()  # 初始化pygame
    game_window_size = 1080, 720  # 设置窗口大小
    screen = pygame.display.set_mode(game_window_size)  # 显示窗口
    pygame.display.set_caption("FightingAircraft")
    clock = pygame.time.Clock()
    color = (0, 0, 0)  # 设置颜色

    # 加载飞机


    # tile_ids, image_source, width, height, tile_width, tile_height = load_map(xml_file_path="map/map0.xml")
    # # 加载游戏图像资源
    # template_image = pygame.image.load(image_source)
    # start_point = np.array([0 * width * tile_width, 0 * height * tile_height])
    # x_load_block_count = int(np.ceil(game_window_size[0] * 0.5 / tile_width)) + 1
    # y_load_block_count = int(np.ceil(game_window_size[1] * 0.5 / tile_height)) + 1
    # step = 5

    # 初始化按键状态字典
    key_states = {pygame.K_UP: False, pygame.K_DOWN: False, pygame.K_LEFT: False, pygame.K_RIGHT: False}

    while True:
        clock.tick(30)
        for event in pygame.event.get():  # 遍历所有事件
            if event.type == pygame.QUIT:  # 如果单击关闭窗口，则退出
                pygame.quit()  # 退出pygame
                sys.exit(0)

            # 处理键盘按下和释放事件
            if event.type == pygame.KEYDOWN:
                if event.key in key_states:
                    key_states[event.key] = True
            elif event.type == pygame.KEYUP:
                if event.key in key_states:
                    key_states[event.key] = False

        # # print(pygame.key.name(bools.index(1)))
        # if key_states[pygame.K_UP]:
        #     start_point[1] -= step
        # elif key_states[pygame.K_DOWN]:
        #     start_point[1] += step
        # elif key_states[pygame.K_LEFT]:
        #     start_point[0] -= step
        # elif key_states[pygame.K_RIGHT]:
        #     start_point[0] += step
        #
        # # 清屏
        # screen.fill((255, 255, 255))
        # start_point[0] = start_point[0] % (width * tile_width)
        # start_point[1] = start_point[1] % (height * tile_height)
        # x_diff = start_point[0] % tile_width
        # y_diff = start_point[1] % tile_height
        # # 开始加载图像并绘图
        # x_tile_block = int(start_point[0] / tile_width)
        # y_tile_block = int(start_point[1] / tile_height)
        # for i in range(x_tile_block-x_load_block_count, x_tile_block+x_load_block_count):
        #     for j in range(y_tile_block-y_load_block_count, y_tile_block+y_load_block_count):
        #         # 首先判断出该位置对应的 id 是多少
        #         id = tile_ids[(j % height) * width + (i % width)]
        #         tile_rect = get_rect_from_tile_id(id, tile_width=tile_width, tile_height=tile_height)
        #         screen.blit(template_image,
        #             (0.5*game_window_size[0]+(i-x_tile_block)*tile_width - x_diff,
        #              0.5*game_window_size[1]+(j-y_tile_block)*tile_height - y_diff), tile_rect)

        pygame.display.flip()  # 更新全部显示
        # print('refresh all')


if __name__ == '__main__':
    run_game()

