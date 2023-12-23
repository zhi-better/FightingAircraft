import base64
import os
import struct
import sys
import threading
import zlib
import asyncio

import pyautogui
import pygame as pg
import time
import xml.etree.ElementTree as ET
from PIL import Image
import numpy as np

from utils.cls_airplane import *
from utils.cls_game_render import *


class GameResources:
    def __init__(self):
        self.airplane_info_map = {}
        self.maps_map = {}
        self.explode_sub_textures = {}
        self.explode_sprite = None
        self.temporary_sub_textures = {}
        self.temporary_sprite = None

        self.load_all()

    def load_all(self):
        self.load_explode()
        self.load_temporary()
        self.load_all_plane_parameters()
        self.load_all_maps()

    def load_temporary(self):
        """
        加载一个组合的2d精灵文件并按照分类将对应的内容提取出来
        :return:
        """
        # 解析XML文件
        tree = ET.parse('temporary.xml')
        root = tree.getroot()
        # sub_textures = {}

        # 遍历子元素
        for sub_texture in root.findall(".//SubTexture"):
            parts = sub_texture.get("name").split('/')
            type_name = parts[0]

            # 根据名字的不同将内容归类
            if len(parts) == 1:  # 炸弹
                self.temporary_sub_textures[type_name] = {'x': int(sub_texture.get("x")),
                                                          'y': int(sub_texture.get('y')),
                                                          'width': int(sub_texture.get('width')),
                                                          'height': int(sub_texture.get('height'))}
            else:  # 建筑
                if type_name not in self.temporary_sub_textures:
                    self.temporary_sub_textures[type_name] = {}

                self.temporary_sub_textures[type_name][parts[1]] = {'x': int(sub_texture.get("x")),
                                                                    'y': int(sub_texture.get('y')),
                                                                    'width': int(sub_texture.get('width')),
                                                                    'height': int(sub_texture.get('height'))}

        self.temporary_sprite = pg.image.load('temporary.png')

    def load_explode(self):
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
                self.explode_sub_textures[name] = explode_list.copy()
                explode_list.clear()
                name = type_name

            explode_list.append({'x': int(sub_texture.get("x")),
                                 'y': int(sub_texture.get('y')),
                                 'width': int(sub_texture.get('width')),
                                 'height': int(sub_texture.get('height'))})
        # 最后一个补上
        self.explode_sub_textures[name] = explode_list
        self.explode_sprite = pg.image.load('explode.png')

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

            '''
            speed=2 => 510km/h
            turnSpeed=3 => 385m
            '''
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

    def load_all_maps(self):
        # 首先加载都有哪些地图
        num_xml_file = 0
        for file in os.listdir('map'):
            if file.endswith(".xml"):
                self.maps_map[num_xml_file] = os.path.join('map', file)
                num_xml_file += 1

    def get_map(self, map_index=0):
        return self.maps_map[map_index]

    def get_bullet_sprite(self, bullet_key='bullet1'):
        """
        加载子弹的精灵，参数为子弹的键
        :param bullet_key: bullet1 - bullet6
        :return:
        """

        return self.temporary_sub_textures[bullet_key], self.temporary_sprite

    def get_building_sprite(self, building_key, state):
        """
        加载建筑的精灵
        :param building_key:
        building01-building15, flak1-flak2, tank1-tank3, tower2-tower3, truck1-truck2
        :param state: body or ruins
        :return:
        """

        return self.temporary_sub_textures[building_key][state], self.temporary_sprite

    def get_explode_animation(self, explode_key='explode01'):
        """
        获取爆炸的图像链表和精灵
        :param explode_key: explode01 - explode12
        :return:
        """
        return self.explode_sub_textures[explode_key], self.explode_sprite

    def get_fire_animation(self, fire_key):
        """
        获取开火的动画和对应的精灵链表
        :param fire_key: fire1 - fire3
        :return:
        """
        return self.explode_sub_textures[fire_key], self.explode_sprite

    def load_plane_sprites(self, file_path):
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
        return 'objects/' + image_path, roll_mapping, pitch_mapping

    def get_plane(self, plane_name, plane_type):
        param = self.airplane_info_map[plane_name]

        if plane_type == PlaneType.FighterJet:
            plane = FighterJet()
        elif plane_type == PlaneType.AttackAircraft:
            plane = FighterJet()
        elif plane_type == PlaneType.AttackAircraft:
            plane = FighterJet()
        else:
            raise ValueError('wrong plane type. ')

        plane.set_speed(param['speed'])
        plane.angular_speed = param['turnspeed']
        plane.health_points = param['lifevalue']
        plane.air_plane_params.primary_weapon_reload_time = 0.2
        plane.air_plane_params.secondary_weapon_reload_time = 0.1
        image_path, roll_mapping, pitch_mapping = self.load_plane_sprites('objects/{}.xml'.format(plane_name))
        plane.load_sprite('objects/{}.png'.format(plane_name))
        plane.air_plane_sprites.roll_mapping = roll_mapping
        plane.air_plane_sprites.pitch_mapping = pitch_mapping
        # 设置主武器和副武器的贴图资源
        sprite, rect = self.get_bullet_sprite('bullet' + str(param['mainweapon']+1))
        plane.air_plane_sprites.primary_bullet_sprite = get_sprite_rect(rect, sprite)
        sprite, rect = self.get_bullet_sprite('bullet' + str(param['secondweapon']))
        plane.air_plane_sprites.secondary_bullet_sprite = get_sprite_rect(rect, sprite)
        return plane


class FightingAircraftGame:
    def __init__(self):
        self.game_name = "FightingAircraft"
        self.game_window_size = 1080, 720  # 设置窗口大小
        self.clock = pg.time.Clock()
        self.game_resources = GameResources()
        self.game_render = GameRender()
        self.player_plane = None
        self.screen = None
        self.map_size = np.zeros((2,))
        self.fps_render = 30
        self.fps_physics = 30
        self.key_states = {pg.K_UP: False,
                           pg.K_DOWN: False,
                           pg.K_LEFT: False,
                           pg.K_RIGHT: False,
                           pg.K_q: False,
                           pg.K_e: False,
                           pg.K_SPACE: False,
                           pg.K_LSHIFT: False,
                           pg.K_j: False,
                           pg.K_k: False,
                           pg.K_f: False}

        self.lock = threading.RLock()  # 线程锁，保证渲染和物理运算的顺序
        self.clock_render = pg.time.Clock()  # 渲染线程的时钟
        self.thread_render = threading.Thread(target=self.render, daemon=True)
        self.render_delta_time = 0

    def input_manager(self):
        # 处理输入
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

        # print(pg.key.name(bools.index(1)))
        if self.key_states[pg.K_UP]:
            # start_point[1] -= step
            self.player_plane.speed_up()
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
        elif self.key_states[pg.K_f]:
            # start_point[0] += step
            self.player_plane.roll()

        if self.key_states[pg.K_j]:
            # start_point[0] += step
            self.player_plane.primary_fire()
        elif self.key_states[pg.K_k]:
            # start_point[0] += step
            self.player_plane.secondary_fire()

    def fixed_update(self, delta_time):
        """
        用于更新物理计算
        :param delta_time: ms
        :return:
        """
        pos, _ = self.player_plane.fixed_update(delta_time=delta_time)
        pos[0] = pos[0] % self.map_size[0]
        pos[1] = pos[1] % self.map_size[1]
        self.player_plane.set_position(pos)
        # 所有发射的弹药也得 move
        for bullet in self.player_plane.bullet_list:
            pos = bullet.get_position()
            pos[0] = pos[0] % self.map_size[0]
            pos[1] = pos[1] % self.map_size[1]
            bullet.set_position(pos)
        # print('\rdelta time: {}, render pos: {}, {}'.format(
        #     delta_time, pos[0], pos[1]), end='')
        # self.player_plane.move(delta_time=delta_time)

    def render(self):
        print('render thread started. ')
        delta_time = 1 / self.fps_render
        self.render_delta_time = 0
        while True:
            self.lock.acquire()
            self.render_delta_time += delta_time
            # print(f'render delta time: {self.render_delta_time}')
            # 清屏
            self.screen.fill((255, 255, 255))
            pos, dir_v = self.player_plane.move(delta_time=self.render_delta_time)
            self.game_render.render_map(pos, screen=self.screen)
            # print('\rdelta time: {}, render pos: {}, {}'.format(self.render_delta_time, pos[0], pos[1]), end='')
            self.game_render.render_object(
                self.player_plane.get_sprite(), pos,
                angle=self.player_plane.get_angle(direction_vector=dir_v), screen=self.screen)
            print('\r obj count: {}'.format(len(self.player_plane.bullet_list)), end='')
            for bullet in self.player_plane.bullet_list:
                self.game_render.render_object(
                    bullet.get_sprite(), bullet.get_position(),
                    angle=bullet.get_angle(bullet.direction_vector), screen=self.screen)

            # 渲染文本
            # 定义字体和字号
            font = pg.font.Font(None, 36)
            text = font.render('Engine temperature: {:.2f}, Speed: {:.2f}, position: [{:.2f}, {:.2f}], dir_vector: [{:.2f}, {:.2f}]'.format(
                self.player_plane.get_engine_temperature(), self.player_plane.velocity,
                pos[0], pos[1], dir_v[0], dir_v[1]),
                True, (0, 0, 0))
            # 将文本绘制到屏幕上
            self.screen.blit(text, (10, 10))
            pg.display.flip()  # 更新全部显示
            self.lock.release()
            delta_time = self.clock_render.tick(self.fps_render)

    def run_game(self):
        pg.init()  # 初始化pg
        self.screen = pg.display.set_mode(self.game_window_size)  # 显示窗口
        pg.display.set_caption(self.game_name)
        self.fps_render = 30

        # 加载飞机
        self.player_plane = self.game_resources.get_plane('Bf109', plane_type=PlaneType.FighterJet)
        self.game_render.window_size = np.array(self.game_window_size).reshape((2,))

        self.game_render.load_map_xml(self.game_resources.get_map(5))
        self.map_size = self.game_render.get_map_size()
        # self.player_plane.set_speed(0)

        # 解决输入法问题
        # 模拟按下 Shift 键
        pyautogui.keyDown('shift')
        # 在这里可以添加一些程序逻辑，模拟按下 Shift 键后的操作
        # time.sleep(1)  # 为了演示，这里等待1秒
        # 松开 Shift 键
        pyautogui.keyUp('shift')

        # 设置渲染线程为子线程
        self.thread_render.start()

        delta_time = 1 / self.fps_physics
        # 此处只有物理运行，关于图形渲染是一个新的单独的线程
        while True:
            self.lock.acquire()
            self.render_delta_time = 0
            self.input_manager()  # 输入管理
            self.fixed_update(delta_time=delta_time)  # 物理运算
            self.lock.release()
            delta_time = self.clock.tick(self.fps_physics)  # 获取时间差，控制帧率
            # delta_time = 0


if __name__ == '__main__':
    game = FightingAircraftGame()
    game.run_game()
