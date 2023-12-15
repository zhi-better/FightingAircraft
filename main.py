import base64
import os
import struct
import sys
import zlib
import asyncio
import pygame as pg
import time
import xml.etree.ElementTree as ET
from PIL import Image
import numpy as np

from utils.cls_airplane import *
from utils.cls_map import Map


class FightingAircraftGame:
    def __init__(self):
        self.game_name = "FightingAircraft"
        self.game_window_size = 1080, 720  # 设置窗口大小
        self.clock = pg.time.Clock()
        self.airplane_info_map = {}
        self.maps_map = {}
        self.explode_map = {}
        self.map = Map()
        self.player_plane = None
        self.key_states = {pg.K_UP: False,
                           pg.K_DOWN: False,
                           pg.K_LEFT: False,
                           pg.K_RIGHT: False,
                           pg.K_q: False,
                           pg.K_e: False,
                           pg.K_SPACE: False,
                           pg.K_LSHIFT: False,
                           pg.K_j: False,
                           pg.K_k: False}

    def input_manager(self):
        # print(pg.key.name(bools.index(1)))
        if self.key_states[pg.K_UP]:
            # start_point[1] -= step
            self.player_plane.sppe_up()
        elif self.key_states[pg.K_DOWN]:
            # start_point[1] += step
            self.player_plane.slow_down()
        if self.key_states[pg.K_LEFT]:
            # start_point[0] -= step
            self.player_plane.turn_left()
        elif self.key_states[pg.K_RIGHT]:
            # start_point[0] += step
            self.player_plane.turn_right()
        elif self.key_states[pg.K_q]:
            # start_point[0] += step
            self.player_plane.sharply_turn_left()
        elif self.key_states[pg.K_e]:
            # start_point[0] += step
            self.player_plane.sharply_turn_right()
        elif self.key_states[pg.K_SPACE]:
            # start_point[0] += step
            self.player_plane.pitch()
        elif self.key_states[pg.K_LSHIFT]:
            # start_point[0] += step
            self.player_plane.roll()
        elif self.key_states[pg.K_j]:
            # start_point[0] += step
            self.player_plane.primary_weapon_attack()
        elif self.key_states[pg.K_k]:
            # start_point[0] += step
            self.player_plane.secondary_weapon_attack()

    def load_all_plane_parameters(self):
        # 解析XML文件
        tree = ET.parse('parameters.xml')
        root = tree.getroot()

        # 遍历子元素
        for sub_texture in root.findall(".//SubTexture"):
            airplane_name = sub_texture.get("name")
            lifevalue = int(sub_texture.get("lifevalue"))
            speed = float(sub_texture.get("speed"))
            mainweapon = int(sub_texture.get("mainweapon"))
            secondweapon = int(sub_texture.get("secondweapon"))
            attackpower = int(sub_texture.get("attackpower"))
            turnspeed = float(sub_texture.get("turnspeed"))
            reloadtime = int(sub_texture.get("reloadtime"))
            ammo = int(sub_texture.get("ammo"))

            # 将飞机信息存储到映射中
            self.airplane_info_map[airplane_name] = {
                "lifevalue": lifevalue,
                "speed": speed,
                "mainweapon": mainweapon,
                "secondweapon": secondweapon,
                "attackpower": attackpower,
                "turnspeed": turnspeed,
                "reloadtime": reloadtime,
                "ammo": ammo
            }

        return self.airplane_info_map

    def load_all_explodes(self):
        # 解析XML文件
        tree = ET.parse('explode.xml')
        root = tree.getroot()

        # 遍历子元素
        name = 'cloud1'
        explode_list = []
        for sub_texture in root.findall(".//SubTexture"):
            parts = sub_texture.get("name").split('/')
            type_name = parts[0]
            if name != type_name:
                self.explode_map[name] = explode_list.copy()
                explode_list.clear()
                name = type_name

            explode_list.append({'x': int(sub_texture.get("x")),
                                 'y': int(sub_texture.get('y')),
                                 'width': int(sub_texture.get('width')),
                                 'height': int(sub_texture.get('height'))})
        # 最后一个补上
        self.explode_map[name] = explode_list

        return self.explode_map

    def load_all_maps(self):
        # 首先加载都有哪些地图
        num_xml_file = 0
        for file in os.listdir('map'):
            if file.endswith(".xml"):
                self.maps_map[num_xml_file] = os.path.join('map', file)
                num_xml_file += 1

    def load_plane(self, plane_name):
        param = self.airplane_info_map[plane_name]

        self.player_plane = FighterJet()
        self.player_plane.set_speed(param['speed'])
        self.player_plane.angular_speed = param['turnspeed']
        self.player_plane.health_points = param['lifevalue']

        image_path, roll_mapping, pitch_mapping = self.load_plane_xml_data('objects/{}.xml'.format(plane_name))
        self.plane_sprite = pg.image.load(image_path)
        self.player_plane = FighterJet()
        self.player_plane.set_speed(5)
        self.player_plane.load_sprite('objects/{}.png'.format(plane_name))
        self.player_plane.roll_mapping = roll_mapping
        self.player_plane.pitch_mapping = pitch_mapping

    def load_plane_xml_data(self, file_path):
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
            if parts[2].find('roll') != -1:
                roll_mapping[int(parts[2][4:])] = {'x': x, 'y': y, 'width': width, 'height': height}
            elif parts[2].find('pitch') != -1:
                pitch_mapping[int(parts[2][5:])] = {'x': x, 'y': y, 'width': width, 'height': height}

        # 返回图片路径和映射字典
        return 'objects/'+image_path, roll_mapping, pitch_mapping

    def run_game(self):
        pg.init()  # 初始化pg
        screen = pg.display.set_mode(self.game_window_size)  # 显示窗口
        pg.display.set_caption(self.game_name)

        # 初始化
        self.load_all_maps()
        self.load_all_plane_parameters()
        self.load_all_explodes()
        self.ammunition_sprite = pg.image.load('explode.png')

        # 加载飞机
        self.load_plane('Bf109')
        self.player_plane.ammunition_sprite = self.ammunition_sprite
        self.player_plane.primary_weapon_animation_list = self.explode_map['fire1']
        self.map.window_size = self.game_window_size
        self.map.load_map_xml(self.maps_map[0])

        # 定义字体和字号
        font = pg.font.Font(None, 36)

        while True:
            self.clock.tick(30)
            for event in pg.event.get():  # 遍历所有事件
                if event.type == pg.QUIT:  # 如果单击关闭窗口，则退出
                    pg.quit()  # 退出pg
                    sys.exit(0)

                # 处理键盘按下和释放事件
                if event.type == pg.KEYDOWN:
                    if event.key in self.key_states:
                        self.key_states[event.key] = True
                elif event.type == pg.KEYUP:
                    if event.key in self.key_states:
                        self.key_states[event.key] = False

            self.input_manager()

            # 清屏
            screen.fill((255, 255, 255))
            self.player_plane.move()
            self.map.render_map(self.player_plane.get_position(), screen=screen)
            self.map.render_object(
                self.player_plane.get_sprite(), self.player_plane.get_position(),
                angle=self.player_plane.get_angle(), screen=screen)
            for ammu in self.player_plane.ammunition_list:
                self.map.render_object(
                    ammu.get_sprite(), self.player_plane.get_position(),
                angle=self.player_plane.get_angle(), screen=screen)

            # 渲染文本
            text = font.render('Engine temperature: {:.2f}, Speed: {:.2f}'.format(
                self.player_plane.get_engine_temperature(),self.player_plane.velocity), True, (0, 0, 0))
            # 获取文本矩形
            text_rect = text.get_rect()
            # 将文本绘制到屏幕上
            screen.blit(text, (10, 10))

            pg.display.flip()  # 更新全部显示


if __name__ == '__main__':
    game = FightingAircraftGame()
    game.run_game()
