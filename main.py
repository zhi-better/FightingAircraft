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

from utils.cls_airplane import AirPlane


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


def load_plane_xml_data(file_path):
    # 解析XML文件
    tree = ET.parse(file_path)
    root = tree.getroot()

    # 获取图片路径
    image_path = root.attrib.get('imagePath')

    # 初始化滚转和俯仰的映射字典
    roll_mapping = {}
    pitch_mapping = {}

    # 遍历SubTexture元素
    for subtexture in root.findall('SubTexture'):
        name = subtexture.attrib.get('name')
        x = int(subtexture.attrib.get('x'))
        y = int(subtexture.attrib.get('y'))
        width = int(subtexture.attrib.get('width'))
        height = int(subtexture.attrib.get('height'))

        # 判断是滚转还是俯仰
        parts = name.split('/')
        if parts[1] == 'roll':
            roll_mapping[int(parts[2][4:])] = {'x': x, 'y': y, 'width': width, 'height': height}
        elif parts[1] == 'pitch':
            pitch_mapping[int(parts[2][4:])] = {'x': x, 'y': y, 'width': width, 'height': height}

    # 返回图片路径和映射字典
    return 'objects/'+image_path, roll_mapping, pitch_mapping

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
    image_path, roll_mapping, pitch_mapping = load_plane_xml_data('objects/Ar234.xml')
    plane_sprite = pygame.image.load(image_path)
    plane = AirPlane()
    plane.set_speed(5)
    plane.load_sprite('objects/Ar234.png')
    plane.roll_mapping = roll_mapping
    plane.pitch_mapping = pitch_mapping

    tile_ids, image_source, width, height, tile_width, tile_height = load_map(xml_file_path="map/map0.xml")
    # 加载游戏图像资源
    template_image = pygame.image.load(image_source)
    start_point = plane.get_position()
    # start_point = np.array([0 * width * tile_width, 0 * height * tile_height])
    x_load_block_count = int(np.ceil(game_window_size[0] * 0.5 / tile_width)) + 1
    y_load_block_count = int(np.ceil(game_window_size[1] * 0.5 / tile_height)) + 1
    step = 5

    # 定义字体和字号
    font = pygame.font.Font(None, 36)

    # 初始化按键状态字典
    key_states = {pygame.K_UP: False,
                  pygame.K_DOWN: False,
                  pygame.K_LEFT: False,
                  pygame.K_RIGHT: False,
                  pygame.K_q: False,
                  pygame.K_e: False}



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

        # print(pygame.key.name(bools.index(1)))
        if key_states[pygame.K_UP]:
            # start_point[1] -= step
            plane.sppe_up()
        elif key_states[pygame.K_DOWN]:
            # start_point[1] += step
            plane.slow_down()
        if key_states[pygame.K_LEFT]:
            # start_point[0] -= step
            plane.turn_left()
        elif key_states[pygame.K_RIGHT]:
            # start_point[0] += step
            plane.turn_right()
        elif key_states[pygame.K_q]:
            # start_point[0] += step
            plane.sharply_turn_left()
        elif key_states[pygame.K_e]:
            # start_point[0] += step
            plane.sharply_turn_right()

        # 清屏
        screen.fill((255, 255, 255))
        plane.move()
        start_point = plane.get_position()
        start_point[0] = start_point[0] % (width * tile_width)
        start_point[1] = start_point[1] % (height * tile_height)
        x_diff = start_point[0] % tile_width
        y_diff = start_point[1] % tile_height
        # 开始加载图像并绘图
        x_tile_block = int(start_point[0] / tile_width)
        y_tile_block = int(start_point[1] / tile_height)
        for i in range(x_tile_block-x_load_block_count, x_tile_block+x_load_block_count):
            for j in range(y_tile_block-y_load_block_count, y_tile_block+y_load_block_count):
                # 首先判断出该位置对应的 id 是多少
                id = tile_ids[(j % height) * width + (i % width)]
                tile_rect = get_rect_from_tile_id(id, tile_width=tile_width, tile_height=tile_height)
                screen.blit(template_image,
                    (0.5*game_window_size[0]+(i-x_tile_block)*tile_width - x_diff,
                     0.5*game_window_size[1]+(j-y_tile_block)*tile_height - y_diff), tile_rect)

        rotated_plane_sprite = plane.get_sprite()

        # 渲染文本
        text = font.render('Engine temperature: {:.2f}, Speed: {:.2f}'.format(
            plane.get_engine_temperature(),plane.real_speed), True, (0, 0, 0))
        # 获取文本矩形
        text_rect = text.get_rect()
        # 将文本绘制到屏幕上
        screen.blit(text, (10, 10))

        # 获取旋转后的矩形
        plane_rect = rotated_plane_sprite.get_rect(
            center=(0.5 * game_window_size[0], 0.5 * game_window_size[1]))
        screen.blit(rotated_plane_sprite, plane_rect)

        pygame.display.flip()  # 更新全部显示
        # print('refresh all')


if __name__ == '__main__':
    run_game()

