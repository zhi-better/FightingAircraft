import base64
import struct
import xml.etree.ElementTree as ET
import zlib

import numpy as np
import pygame
import pygame as pg


class GameRender:
    def __init__(self):
        self.height = 0
        self.width = 0
        self.tile_width = 0
        self.tile_height = 0
        self.map_size = np.zeros((2,))
        self.image_source = ''
        self.tile_ids = []
        self.window_size = np.zeros((2,))
        self.template_image = None
        self.x_load_block_count = 0
        self.y_load_block_count = 0
        self.view_position = np.zeros((2,))

    def get_map_size(self):
        return self.map_size

    def get_rect_from_tile_id(self, tile_id, tile_width, tile_height):
        if tile_id != 0:
            rec_x = tile_id % 8 - 1
            if rec_x < 0:
                rec_x = 7
                rec_y = tile_id // 8 - 1
            else:
                rec_y = tile_id // 8
            tile_rect = pg.Rect(rec_x * tile_width, rec_y * tile_height,
                                    tile_width, tile_height)
        else:
            print('wrong tile id: {}'.format(tile_id))
            tile_rect = pg.Rect(0, 0, 0, 0)
        return tile_rect

    def render_object(self, sprite, position, angle, screen):
        """
        渲染大地图中 x y 位置的目标物体
        :param x:
        :param y:
        :return:
        """
        # position = np.array([rect.x, rect.y]) - 0.5*np.array([rect.width, rect.height])
        # 获取旋转后的矩形
        sprite = pg.transform.rotate(sprite, angle)
        # 此处有可能再地图边界由于分界线出现bug问题，需要额外处理
        right_down_threshold = self.map_size - 0.5 * self.window_size
        left_top_threshold = 0.5 * self.window_size
        if (position[0] > right_down_threshold[0]
                and self.view_position[0] < left_top_threshold[0]):
            position[0] -= self.map_size[0]
        elif (self.view_position[0] > right_down_threshold[0]
                and position[0] < left_top_threshold[0]):
            position[0] += self.map_size[0]
        elif (position[1] > right_down_threshold[1]
                and self.view_position[1] < left_top_threshold[0]):
            position[1] -= self.map_size[1]
        elif (self.view_position[1] > right_down_threshold[1]
                and position[1] < left_top_threshold[0]):
            position[1] += self.map_size[1]
        a = np.floor(position[0] - self.view_position[0])
        # 好你个bug，老子找了半天才发现坐标系是反的
        b = np.floor(position[1] - self.view_position[1])
        plane_rect = sprite.get_rect(
            center=(0.5 * self.window_size[0] + a,
                    0.5 * self.window_size[1] + b))
        # print('\r {}, {}'.format(a, b), end='')
        screen.blit(sprite, plane_rect)

        # 创建一个充气的矩形，以便在原始矩形周围绘制边框
        inflated_rect = plane_rect.inflate(4, 4)  # 边框大小为4像素
        pygame.draw.rect(screen, (255, 0, 0), inflated_rect, 2)  # 绘制红色边框

    def render_map(self, position, screen):
        """
        渲染地图以 x y 为中心, view_width和view_height为大小的图窗内容
        :param x:
        :param y:
        :return:
        """
        position[0] = position[0] % (self.width * self.tile_width)
        position[1] = position[1] % (self.height * self.tile_height)
        self.view_position = np.array([position[0], position[1]]).astype(int)
        x_diff = position[0] % self.tile_width
        y_diff = position[1] % self.tile_height
        # 开始加载图像并绘图
        x_tile_block = int(position[0] / self.tile_width)
        y_tile_block = int(position[1] / self.tile_height)
        for i in range(x_tile_block - self.x_load_block_count, x_tile_block + self.x_load_block_count):
            for j in range(y_tile_block - self.y_load_block_count, y_tile_block + self.y_load_block_count):
                # 首先判断出该位置对应的 id 是多少
                id = self.tile_ids[(j % self.height) * self.width + (i % self.width)]
                tile_rect = self.get_rect_from_tile_id(id, tile_width=self.tile_width, tile_height=self.tile_height)
                screen.blit(self.template_image,
                            (0.5 * self.window_size[0] + (i - x_tile_block) * self.tile_width - x_diff,
                             0.5 * self.window_size[1] + (j - y_tile_block) * self.tile_height - y_diff), tile_rect)

    def load_map_xml(self, xml_file_path):
        # 读取XML文件
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        # 获取地图的宽度和高度
        self.width = int(root.attrib["width"])
        self.height = int(root.attrib["height"])
        # 获取瓦片宽度和高度
        self.tile_width = int(root.attrib["tilewidth"])
        self.tile_height = int(root.attrib["tileheight"])
        # # 设置缩放比例
        # scaled_tilewidth = int(tilewidth * scale_factor)
        # scaled_tileheight = int(tileheight * scale_factor)

        # # 创建pg窗口
        # initial_window_size = (width * scaled_tilewidth, height * scaled_tileheight)
        # 解析图层数据
        data_element = root.find(".//layer/data")
        data_str = data_element.text.strip()
        data_bytes = base64.b64decode(data_str)
        data = zlib.decompress(data_bytes)
        # 将解压后的数据转换为列表
        self.tile_ids = list(struct.unpack("<" + "I" * (len(data) // 4), data))
        # 获取tileset中的tile元素，获取图像文件信息
        self.image_source = "map/" + root.find(".//tileset/image").get('source')

        # 加载游戏图像资源
        self.template_image = pg.image.load(self.image_source)
        self.x_load_block_count = int(np.ceil(self.window_size[0] * 0.5 / self.tile_width)) + 1
        self.y_load_block_count = int(np.ceil(self.window_size[1] * 0.5 / self.tile_height)) + 1

        self.map_size = np.array([self.width * self.tile_width, self.height * self.tile_height])





