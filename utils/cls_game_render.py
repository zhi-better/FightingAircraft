import base64
import struct
import xml.etree.ElementTree as ET
import zlib

import numpy as np
import pygame
import pygame as pg

from utils.cls_airplane import *
from utils.cls_game_data import GameMap


class GameRender:
    def __init__(self):
        self.map_info: GameMap = None
        # self.height = 0
        # self.width = 0
        # self.tile_width = 0
        # self.tile_height = 0
        # self.map_size = np.zeros((2,))
        # self.image_source = ''
        # self.tile_ids = []
        self.game_window_size = np.zeros((2,))
        # self.template_image = None
        self.x_load_block_count = 0
        self.y_load_block_count = 0
        self.view_position = np.zeros((2,))
        self.font = None
        self.screen = None
        self.draw_collision_box = False

    def set_map_info(self, map_info):
        # 设置地图的信息
        self.map_info = map_info
        self.x_load_block_count = int(
            np.ceil(self.game_window_size[0] * 0.5 / self.map_info.tile_width)) + 1
        self.y_load_block_count = int(
            np.ceil(self.game_window_size[1] * 0.5 / self.map_info.tile_height)) + 1

    def set_screen(self, screen):
        self.screen = screen

    def get_map_size(self):
        return self.map_info.map_size

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

    def render_explode(self, explode):
        """
        渲染建筑，建筑不会动
        :param explode:
        :return:
        """
        sprite = explode.get_sprite()
        plane_rect, should_render = (
            self.get_object_render_rect(sprite, explode.get_position()))
        if should_render:
            self.screen.blit(sprite, plane_rect)

        if self.draw_collision_box:
            # 创建一个充气的矩形，以便在原始矩形周围绘制边框
            inflated_rect = plane_rect.inflate(2, 2)  # 边框大小为4像素
            pygame.draw.rect(self.screen, (255, 0, 0), inflated_rect, 2)  # 绘制红色边框

    def render_building(self, building):
        """
        渲染建筑，建筑不会动
        :param building:
        :return:
        """
        sprite = building.get_sprite()
        plane_rect, should_render = (
            self.get_object_render_rect(sprite, building.get_position()))
        if should_render:
            self.screen.blit(sprite, plane_rect)

        if self.draw_collision_box:
            # 创建一个充气的矩形，以便在原始矩形周围绘制边框
            inflated_rect = plane_rect.inflate(2, 2)  # 边框大小为4像素
            pygame.draw.rect(self.screen, (255, 0, 0), inflated_rect, 2)  # 绘制红色边框

    def render_turret(self, turret, delta_time):
        """
        渲染炮台，炮台包含两个部位：
        基底和攻击的炮管
        :param turret:
        :return:
        """
        turret_carriage_sprite, rotated_cannon = turret.get_sprite()
        pos = turret.get_position()
        # 首先渲染底座
        plane_rect, should_render = (
            self.get_object_render_rect(turret_carriage_sprite, pos))
        if should_render:
            self.screen.blit(turret_carriage_sprite, plane_rect)
        # 然后渲染上面的内容
        if rotated_cannon is not None:
            plane_rect, should_render = (
                self.get_object_render_rect(rotated_cannon, pos))
            if should_render:
                self.screen.blit(rotated_cannon, plane_rect)

        if self.draw_collision_box:
            # 创建一个充气的矩形，以便在原始矩形周围绘制边框
            inflated_rect = plane_rect.inflate(2, 2)  # 边框大小为4像素
            pygame.draw.rect(self.screen, (255, 0, 0), inflated_rect, 2)  # 绘制红色边框

    def render_bullet(self, bullet, delta_time):
        """
        :param bullet:
        :return:
        """
        sprite = bullet.get_sprite()
        pos, dir_v = bullet.move(delta_time=delta_time)
        plane_rect, should_render = (
            self.get_object_render_rect(sprite, pos))
        if should_render:
            self.screen.blit(sprite, plane_rect)

        if self.draw_collision_box:
            # 创建一个充气的矩形，以便在原始矩形周围绘制边框
            inflated_rect = plane_rect.inflate(2, 2)  # 边框大小为4像素
            pygame.draw.rect(self.screen, (255, 0, 0), inflated_rect, 2)  # 绘制红色边框

    def render_box(self, target):
        sprite = target.get_sprite()
        pos = target.get_position()
        plane_rect, should_render = (
            self.get_object_render_rect(sprite, pos))
        if should_render:
            # 创建一个充气的矩形，以便在原始矩形周围绘制边框
            inflated_rect = plane_rect.inflate(2, 2)  # 边框大小为4像素
            pygame.draw.rect(self.screen, (255, 0, 0), inflated_rect, 2)  # 绘制红色边框

    def render_plane(self, plane, team_id, delta_time):
        """
        渲染飞机，实现不同角度射击
        :param plane:
        :param team_id:
        :return:
        """
        sprite = plane.get_sprite()
        pos, dir_v = plane.move(delta_time=delta_time)
        plane_rect, should_render = (
            self.get_object_render_rect(sprite, pos))
        if team_id == 1:
            font_color = (0, 255, 0)
        else:
            font_color = (255, 0, 0)
        if should_render:
            self.screen.blit(sprite, plane_rect)
            if self.font is None:
                self.font = pygame.font.Font(None, 24)  # 使用默认字体，大小36
            # 在飞机上方显示生命值文本
            # text = f'Health: {plane._air_plane_params.health_points}, pos_x: {np.round(pos[0], decimals=2)}, pos_y: {np.round(pos[1], decimals=2)}'
            text = 'Health: {}, score: {:.2f}'.format(
                plane.durability, plane.score
            )
            text_surface = self.font.render(
                text,
                True, font_color)  # 黑色文本
            text_rect = text_surface.get_rect(
                center=(plane_rect.centerx, plane_rect.centery - 0.6 * plane_rect.height))  # 设置文本位置
            self.screen.blit(text_surface, text_rect)

            if self.draw_collision_box:
                # 创建一个充气的矩形，以便在原始矩形周围绘制边框
                inflated_rect = plane_rect.inflate(2, 2)  # 边框大小为4像素
                pygame.draw.rect(self.screen, (255, 0, 0), inflated_rect, 2)  # 绘制红色边框

    def get_object_render_rect(self, sprite, position):
        """
        获取对应的元素在屏幕上渲染的范围和是否应该被渲染
        :param sprite:
        :param position:
        :return:
        """
        # position = np.array([rect.x, rect.y]) - 0.5*np.array([rect.width, rect.height])
        # 获取旋转后的矩形
        # sprite = pg.transform.rotate(sprite, angle)
        map_info = self.map_info
        # 此处有可能再地图边界由于分界线出现bug问题，需要额外处理
        right_down_threshold = map_info.map_size - 0.5 * self.game_window_size
        left_top_threshold = 0.5 * self.game_window_size
        if (position[0] > right_down_threshold[0]
                and self.view_position[0] < left_top_threshold[0]):
            position[0] -= map_info.map_size[0]
        elif (self.view_position[0] > right_down_threshold[0]
              and position[0] < left_top_threshold[0]):
            position[0] += map_info.map_size[0]
        if (position[1] > right_down_threshold[1]
                and self.view_position[1] < left_top_threshold[0]):
            position[1] -= map_info.map_size[1]
        elif (self.view_position[1] > right_down_threshold[1]
              and position[1] < left_top_threshold[0]):
            position[1] += map_info.map_size[1]
        a = np.floor(position[0] - self.view_position[0])
        # 好你个bug，老子找了半天才发现坐标系是反的
        b = np.floor(position[1] - self.view_position[1])
        # sprite = game_sprite.get_sprite()
        plane_rect = sprite.get_rect(
            center=(0.5 * self.game_window_size[0] + a,
                    0.5 * self.game_window_size[1] + b))

        # 返回渲染的区域和是否应该被渲染
        if plane_rect.x <= self.game_window_size[0] and plane_rect.y <= self.game_window_size[1]:
            return plane_rect, True
        else:
            return plane_rect, False

    def render_map(self, position, screen):
        """
        渲染地图以 x y 为中心, view_width和view_height为大小的图窗内容
        :param screen:
        :param position:
        :return:
        """
        map_info = self.map_info
        position[0] = position[0] % (map_info.width * map_info.tile_width)
        position[1] = position[1] % (map_info.height * map_info.tile_height)
        self.view_position = np.array([position[0], position[1]]).astype(int)
        x_diff = int(position[0] % map_info.tile_width)
        y_diff = int(position[1] % map_info.tile_height)
        # 开始加载图像并绘图
        x_tile_block = int(position[0] / map_info.tile_width)
        y_tile_block = int(position[1] / map_info.tile_height)
        for i in range(x_tile_block - self.x_load_block_count, x_tile_block + self.x_load_block_count):
            for j in range(y_tile_block - self.y_load_block_count, y_tile_block + self.y_load_block_count):
                # 首先判断出该位置对应的 id 是多少
                id = map_info.tile_ids[(j % map_info.height) * map_info.width + (i % map_info.width)]
                tile_rect = self.get_rect_from_tile_id(id, tile_width=map_info.tile_width, tile_height=map_info.tile_height)
                screen.blit(map_info.template_image,
                            (0.5 * self.game_window_size[0] + (i - x_tile_block) * map_info.tile_width - x_diff,
                             0.5 * self.game_window_size[1] + (j - y_tile_block) * map_info.tile_height - y_diff), tile_rect)

    # def load_map_xml(self, xml_file_path):
    #     # 读取XML文件
    #     tree = ET.parse(xml_file_path)
    #     root = tree.getroot()
    #     # 获取地图的宽度和高度
    #     self.width = int(root.attrib["width"])
    #     self.height = int(root.attrib["height"])
    #     # 获取瓦片宽度和高度
    #     self.tile_width = int(root.attrib["tilewidth"])
    #     self.tile_height = int(root.attrib["tileheight"])
    #     # # 设置缩放比例
    #     # scaled_tilewidth = int(tilewidth * scale_factor)
    #     # scaled_tileheight = int(tileheight * scale_factor)
    #
    #     # # 创建pg窗口
    #     # initial_window_size = (width * scaled_tilewidth, height * scaled_tileheight)
    #     # 解析图层数据
    #     data_element = root.find(".//layer/data")
    #     data_str = data_element.text.strip()
    #     data_bytes = base64.b64decode(data_str)
    #     data = zlib.decompress(data_bytes)
    #     # 将解压后的数据转换为列表
    #     self.tile_ids = list(struct.unpack("<" + "I" * (len(data) // 4), data))
    #     # 获取tileset中的tile元素，获取图像文件信息
    #     self.image_source = "map/" + root.find(".//tileset/image").get('source')
    #
    #     # 加载游戏图像资源
    #     self.template_image = pg.image.load(self.image_source)
    #     self.x_load_block_count = int(np.ceil(self.game_window_size[0] * 0.5 / self.tile_width)) + 1
    #     self.y_load_block_count = int(np.ceil(self.game_window_size[1] * 0.5 / self.tile_height)) + 1
    #
    #     self.map_size = np.array([self.width * self.tile_width, self.height * self.tile_height])





