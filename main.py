import base64
import json
import os
import random
import struct
import sys
import threading
import zlib
import asyncio
from typing import Dict

import pyautogui
import pygame as pg
import time
import xml.etree.ElementTree as ET

import pygame.sprite
from PIL import Image
import numpy as np

from utils.SocketTcpTools import *
from utils.cls_airplane import *
from utils.cls_game_render import *


class CommandType(Enum):
    cmd_none = 0
    cmd_login = 1
    cmd_login_resp = 2
    cmd_matching_successful = 3
    cmd_player_action = 4
    cmd_frame_update = 4


class GameSprite(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.test = 1


class GameResources:
    def __init__(self):
        self.airplane_info_map = {}
        self.maps_map = {}
        self.explode_sub_textures = {}
        self.explode_sprite = None
        self.temporary_sub_textures = {}
        self.temporary_sprite = None
        self.thumbnail_map_sprite = None

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
        file_name = self.maps_map[map_index]
        # 寻找最后一个点的位置，表示扩展名的开始
        last_dot_index = file_name.rfind('.')
        # 如果找到点，并且点不在字符串的开头或结尾
        if last_dot_index != -1 and last_dot_index < len(file_name) - 1:
            # 获取扩展名前的部分
            file_base_name = file_name[:last_dot_index]
            # 将扩展名更改为 .png
            file_name_with_png = file_base_name + '.png'

        self.thumbnail_map_sprite = pygame.image.load(file_name_with_png)
        return self.maps_map[map_index], self.thumbnail_map_sprite

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

        if pitch_mapping == {}:
            plane_type = PlaneType.Bomber
        else:
            plane_type = PlaneType.FighterJet

        # 返回图片路径和映射字典
        return 'objects/' + image_path, roll_mapping, pitch_mapping, plane_type

    def get_plane(self, plane_name):
        param = self.airplane_info_map[plane_name]
        image_path, roll_mapping, pitch_mapping, plane_type = self.load_plane_sprites(
            'objects/{}.xml'.format(plane_name))

        if plane_type == PlaneType.FighterJet:
            plane = FighterJet()
        elif plane_type == PlaneType.AttackAircraft:
            plane = AttackAircraft()
        elif plane_type == PlaneType.Bomber:
            plane = Bomber()
        else:
            raise ValueError('wrong plane type. ')

        plane.set_speed(param['speed'])
        plane.angular_speed = param['turnspeed']
        plane.health_points = param['lifevalue']
        plane.air_plane_params.name = plane_name
        plane.air_plane_params.primary_weapon_reload_time = 0.2
        plane.air_plane_params.secondary_weapon_reload_time = 0.1
        # plane.air_plane_params.primary_weapon_reload_time = 0
        # plane.air_plane_params.secondary_weapon_reload_time = 0
        plane.load_sprite('objects/{}.png'.format(plane_name))
        plane.air_plane_sprites.roll_mapping = roll_mapping
        plane.air_plane_sprites.pitch_mapping = pitch_mapping
        # 设置主武器和副武器的贴图资源
        sprite, rect = self.get_bullet_sprite('bullet' + str(param['mainweapon'] + 1))
        plane.air_plane_sprites.primary_bullet_sprite = get_rect_sprite(rect, sprite)
        sprite, rect = self.get_bullet_sprite('bullet' + str(param['secondweapon']))
        plane.air_plane_sprites.secondary_bullet_sprite = get_rect_sprite(rect, sprite)

        plane.get_sprite()
        return plane


class FightingAircraftGame:
    def __init__(self):
        self.exit_event = threading.Event()
        self.player_id = 0
        self.local_time_stamp = 0
        self.update_frames = []
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
        self.client = TcpClientTools()
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
                           pg.K_f: False,
                           pg.K_w: False,
                           pg.K_a: False,
                           pg.K_s: False,
                           pg.K_d: False}
        self.lock = threading.RLock()  # 线程锁，保证渲染和物理运算的顺序
        self.clock_render = pg.time.Clock()  # 渲染线程的时钟
        self.thread_render = threading.Thread(target=self.render, daemon=True)
        self.render_delta_time = 0
        self.recv_server_signal = False
        self.is_game_ready = False

        # 为了便于更新内容，创建了三个组，分别是：所有飞机，敌方飞机，我方飞机
        # self.all_planes_group = pygame.sprite.Group()
        self.id_plane_mapping: Dict[int, AirPlane] = {}
        self.team1_group = pygame.sprite.Group()
        self.team2_group = pygame.sprite.Group()

    def init_game(self):
        """
        初始化游戏的一些必要组件，例如网络和资源加载
        :return:
        """
        pg.init()  # 初始化pg
        self.screen = pg.display.set_mode(self.game_window_size)  # 显示窗口
        pg.display.set_caption(self.game_name)
        self.fps_render = 30
        # 解决输入法问题
        # 模拟按下 Shift 键
        pyautogui.keyDown('shift')
        # 松开 Shift 键
        pyautogui.keyUp('shift')

        # 连接网络并发送匹配请求
        self.client.set_callback_fun(self.callback_recv)
        self.recv_server_signal = True
        self.client.connect_to_server('172.21.152.184', 4444)
        data = {
            "command": CommandType.cmd_login.value,
            "player_id": self.player_id,
            "plane_name": random.choice(list(self.game_resources.airplane_info_map.keys()))
            # "plane_name": 'Bf110'
        }
        # random.choice(list(self.game_resources.airplane_info_map.keys()))
        self.client.send(json.dumps(data), pack_data=True, data_type=DataType.TypeString)
        # self.client.send(json.dumps({'command': CommandType.cmd_none.value}), pack_data=True, data_type=DataType.TypeString)

        # 设置渲染线程为子线程
        self.thread_render.start()
        clk = pg.time.Clock()
        while True:
            self.input_manager()  # 输入管理
            if self.is_game_ready:
                # 当接收到游戏开始的信息后进入到运行游戏的函数
                self.run_game()
            clk.tick(self.fps_physics)  # 获取时间差，控制帧率

    def run_game(self):
        """
        运行主游戏逻辑：
        针对网络发送的运行数据，本地接收时间是不固定的，但是必须要用固定的时间间隔去运行这些不固定间隔的数据
        :return:
        """
        delta_time = 1000 / self.fps_physics   # 物理运行的速度应该是固定的服务器的间隔

        # 此处只有物理运行，关于图形渲染是一个新的单独的线程
        while self.is_game_ready:
            self.lock.acquire()
            # 首先要刷新渲染的起始时间
            self.render_delta_time = 0
            # 运行完毕所有的在这段时间内接收到的数据帧
            for frame in self.update_frames:
                if frame['time_stamp'] >= self.local_time_stamp:
                    # 物理运算应该包含物理运算的帧内容和时间间隔
                    self.fixed_update(frame=frame, delta_time=delta_time)  # 物理运算
                self.update_frames.remove(frame)
            self.lock.release()
            self.input_manager()  # 输入管理
            self.clock.tick(self.fps_physics)  # 获取时间差，控制帧率

    def callback_recv(self, cmd, params):

        if cmd == CallbackCommand.RecvData:
            data = params['data']
            data = json.loads(data.decode())
            cmd = CommandType(data['command'])
            if cmd == CommandType.cmd_login_resp:
                self.player_id = data['player_id']
            elif cmd == CommandType.cmd_matching_successful:
                print('matching successfully. ')
                # 加载地图
                self.game_render.game_window_size = np.array(self.game_window_size).reshape((2,))
                map_xml_name, _ = self.game_resources.get_map(data['map_id'])
                self.game_render.load_map_xml(map_xml_name)
                self.map_size = self.game_render.get_map_size()

                planes = data['planes']
                for plane_info in planes:
                    if plane_info['player_id'] == self.player_id:
                        # 加载飞机
                        self.player_plane = self.game_resources.get_plane(plane_info['plane_name'])
                        self.player_plane.set_map_size(self.map_size)
                        self.player_plane.set_position(np.array([plane_info['position_x'], plane_info['position_y']]))
                        self.player_plane.team_number = 1
                        self.team1_group.add(self.player_plane)
                        self.id_plane_mapping[plane_info['player_id']] = self.player_plane
                    else:
                        new_plane = self.game_resources.get_plane(plane_info['plane_name'])
                        new_plane.set_map_size(self.map_size)
                        new_plane.set_position(np.array([plane_info['position_x'], plane_info['position_y']]))

                        new_plane.team_number = 2
                        self.team2_group.add(new_plane)
                        self.id_plane_mapping[plane_info['player_id']] = new_plane

                # self.all_planes_group.add(self.team1_group, self.team2_group)

                # 进行游戏必要的同步变量设置
                self.is_game_ready = True
            elif cmd == CommandType.cmd_frame_update:
                self.update_frames.append(data)
        elif cmd == CallbackCommand.SocketClose:
            print('closed')

    def input_manager(self):
        # 处理输入
        for event in pg.event.get():  # 遍历所有事件
            if event.type == pg.QUIT:  # 如果单击关闭窗口，则退出
                self.client.close_socket()
                self.exit_event.set()
                self.thread_render.join()
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
        if self.key_states[pg.K_UP] or self.key_states[pg.K_w]:
            # start_point[1] -= step
            self.player_plane.speed_up()
        elif self.key_states[pg.K_DOWN] or self.key_states[pg.K_s]:
            # start_point[1] += step
            self.player_plane.slow_down()
        if self.key_states[pg.K_LEFT] or self.key_states[pg.K_a]:
            # start_point[0] -= step
            self.player_plane.turn_left()
        elif self.key_states[pg.K_RIGHT] or self.key_states[pg.K_d]:
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

        if self.is_game_ready:
            data = {
                "command": CommandType.cmd_player_action.value,
                "match_id": 0,
                "player_id": self.player_id,
                "action": self.player_plane.input_state.value
            }
            self.player_plane.input_state = InputState.NoInput
            self.client.send(json.dumps(data), pack_data=True, data_type=DataType.TypeString)

    def fixed_update(self, frame, delta_time):
        """
        用于更新物理计算
        :param delta_time: ms
        :return:
        """
        # 先更新飞机的输入状态
        actions = frame['actions']
        for key in actions.keys():
            plane = self.id_plane_mapping[int(key)]
            plane.input_state = InputState(actions[key])

        # 然后遍历飞机的飞行状态
        for plane in self.id_plane_mapping.values():
            pos, _ = plane.fixed_update(delta_time=delta_time)
            plane.set_position(pos)
            # 所有发射的弹药也得 move
            for bullet in plane.bullet_group:
                pos, _ = bullet.move(delta_time=delta_time)
                bullet.set_position(pos)
                if bullet.time_passed >= bullet.life_time:
                    plane.bullet_group.remove(bullet)
            # 进行碰撞检测
            crashed = {}
            if plane.team_number == 1:
                crashed = pygame.sprite.groupcollide(
                    plane.bullet_group, self.team2_group, False, False)
            elif plane.team_number == 2:
                crashed = pygame.sprite.groupcollide(
                    plane.bullet_group, self.team1_group, False, False)
            else:
                print('unknown team_number: {}'.format(plane.team_number))

            if len(crashed):
                for bullet in crashed:
                    if crashed[bullet][0].take_damage(bullet.damage):
                        print('enemy eliminated. ')
                    plane.bullet_group.remove(bullet)

        self.local_time_stamp += 1

    def render(self):
        print('render thread started. ')
        delta_time = 1 / self.fps_render
        self.render_delta_time = 0
        font = pg.font.Font(None, 36)
        self.game_render.draw_collision_box = False
        self.game_render.set_screen(self.screen)

        while not self.exit_event.is_set():
            self.lock.acquire()
            if self.is_game_ready:
                self.render_delta_time += delta_time
                pos, dir_v = self.player_plane.move(delta_time=self.render_delta_time)
                self.game_render.render_map(pos, screen=self.screen)
                text = font.render(
                    'Engine temperature: {:.2f}, Speed: {:.2f}, position: [{:.2f}, {:.2f}]'.format(
                        self.player_plane.get_engine_temperature(), self.player_plane.velocity,
                        pos[0], pos[1]),
                    True, (0, 0, 0))
                for plane in self.team1_group:
                    self.game_render.render_plane(plane=plane, team_id=1, delta_time=delta_time)
                    # print('\r obj count: {}'.format(len(self.player_plane.bullet_list)), end='')
                    for bullet in plane.bullet_group:
                        self.game_render.render_bullet(bullet=bullet)
                for plane in self.team2_group:
                    # pos, dir_v = plane.move(delta_time=self.render_delta_time)
                    self.game_render.render_plane(plane=plane, team_id=2, delta_time=delta_time)
                    # print('\r obj count: {}'.format(len(self.player_plane.bullet_list)), end='')
                    for bullet in plane.bullet_group:
                        self.game_render.render_bullet(bullet=bullet)

                # 将文本绘制到屏幕上
                self.screen.blit(text, (10, 10))
                # 然后在右上角显示小地图
                thumbnail_map_sprite_rect = self.game_resources.thumbnail_map_sprite.get_rect()
                thumbnail_map_render_left = self.game_window_size[0] - thumbnail_map_sprite_rect.width
                self.screen.blit(
                    self.game_resources.thumbnail_map_sprite,
                    (thumbnail_map_render_left, 0))
                scale = thumbnail_map_sprite_rect.width / self.map_size[0]
                # 然后根据小地图的位置来显示不同的飞机在缩略图中的位置
                for plane in self.team1_group:
                    pos = plane.get_position()
                    pygame.draw.circle(
                        self.screen, (0, 255, 0),
                        (thumbnail_map_render_left + pos[0]*scale,
                         pos[1]*scale), 2)
                for plane in self.team2_group:
                    pos = plane.get_position()
                    pygame.draw.circle(
                        self.screen, (255, 0, 0),
                        (thumbnail_map_render_left + pos[0]*scale,
                         pos[1]*scale), 2)
                # 然后绘制框框
                pos = self.player_plane.get_position()
                pygame.draw.rect(
                    self.screen, (255, 0, 0),
                    (thumbnail_map_render_left + (pos[0]-0.5*self.game_window_size[0])*scale,
                         (pos[1]-0.5*self.game_window_size[1])*scale,
                     self.game_window_size[0]*scale,
                     self.game_window_size[1]*scale), 2)

            else:
                # 清屏
                self.screen.fill((255, 255, 255))
            pg.display.flip()  # 更新全部显示
            self.lock.release()
            delta_time = self.clock_render.tick(self.fps_render)
            # delta_time = 30


if __name__ == '__main__':
    game = FightingAircraftGame()
    game.init_game()
