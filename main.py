import base64
import json
import logging
import os
import random
import struct
import sys
import threading
import zlib
import asyncio
from typing import Dict
from typing import List
import pyautogui
import pygame as pg
import time
import xml.etree.ElementTree as ET

import pygame.sprite
from PIL import Image
import numpy as np

from utils.SocketTcpTools import *
from utils.cls_airplane import *
from utils.cls_building import *
from utils.cls_explode import Explode
from utils.cls_game_render import *

def setup_logging(log_file_path):
    """
    设置日志记录，将日志同时输出到控制台和文件中

    Parameters:
    - log_file_path (str): 日志文件路径

    Returns:
    - logging.Logger: 配置好的Logger对象
    """
    # 删除已存在的日志文件
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    # 创建Logger对象
    logger = logging.getLogger('my_logger')
    logger.setLevel(logging.DEBUG)

    # 创建文件处理器并设置级别为DEBUG
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)

    # 创建控制台处理器并设置级别为INFO
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # 将格式化器添加到处理器
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 将处理器添加到Logger对象
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

class CommandType(Enum):
    cmd_none = 0
    cmd_login = 1
    cmd_login_resp = 2
    cmd_matching_successful = 3
    cmd_player_action = 4
    cmd_frame_update = 5
    cmd_matching_state_change = 6


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
        scale_factor = 0.6
        # 如果找到点，并且点不在字符串的开头或结尾
        if last_dot_index != -1 and last_dot_index < len(file_name) - 1:
            # 获取扩展名前的部分
            file_base_name = file_name[:last_dot_index]
            # 将扩展名更改为 .png
            file_name_with_png = file_base_name + '.png'
            original_image = pygame.image.load(file_name_with_png)
            # 获取原始图像的宽度和高度
            original_width, original_height = original_image.get_size()
            # 计算缩放后的宽度和高度
            scaled_width = int(original_width * scale_factor)
            scaled_height = int(original_height * scale_factor)
            # 使用 pygame.transform.scale 缩放图像
            self.thumbnail_map_sprite = pygame.transform.scale(original_image, (scaled_width, scaled_height))

        return self.maps_map[map_index], self.thumbnail_map_sprite

    def get_bullet_sprite(self, bullet_key='bullet1'):
        """
        加载子弹的精灵，参数为子弹的键
        :param bullet_key: bullet1 - bullet6
        :return:
        """

        return self.temporary_sub_textures[bullet_key], self.temporary_sprite

    def get_turret_sprite(self, bullet_key='turret'):
        """
        加载炮管的精灵，参数为子弹的键
        :param bullet_key: turret -> turret0 -> turret4
        :return:
        """

        return self.temporary_sub_textures[bullet_key], self.temporary_sprite

    def get_building_sprite(self, building_key, state='body'):
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
        for sub_texture in root.findall('SubTexture'):
            name = sub_texture.attrib.get('name')
            x = int(sub_texture.attrib.get('x'))
            y = int(sub_texture.attrib.get('y'))
            width = int(sub_texture.attrib.get('width'))
            height = int(sub_texture.attrib.get('height'))

            # 判断是滚转还是俯仰
            parts = name.split('/')
            if parts[2].find('roll') != -1:
                roll_mapping[int(parts[2][4:])] = {'x': x, 'y': y, 'width': width, 'height': height}
            elif parts[2].find('pitch') != -1:
                pitch_mapping[int(parts[2][5:])] = {'x': x, 'y': y, 'width': width, 'height': height}

        # 返回图片路径和映射字典
        return 'objects/' + image_path, roll_mapping, pitch_mapping

    def get_plane(self, plane_name, list_explodes):
        param = self.airplane_info_map[plane_name]
        image_path, roll_mapping, pitch_mapping = self.load_plane_sprites(
            'objects/{}.xml'.format(plane_name))

        # 读取JSON文件
        with open('parameters.json', 'r') as file:
            data = json.load(file)
        plane_type = PlaneType(data['planes'][plane_name]['type'])

        if plane_type == PlaneType.Fighter:
            plane = FighterJet(list_explodes)
        elif plane_type == PlaneType.AttackAircraft:
            plane = AttackAircraft(list_explodes)
        elif plane_type == PlaneType.Bomber:
            plane = Bomber(list_explodes)
        else:
            plane = Bomber(list_explodes)

        plane.set_speed(param['speed'])
        plane.angular_speed = param['turnspeed']
        plane.health_points = param['lifevalue']
        params = plane.get_air_plane_params()
        params.name = plane_name
        params.primary_weapon_reload_time = 0.2
        params.secondary_weapon_reload_time = 0.1
        params.plane_width = roll_mapping[0]['width']
        params.plane_height = roll_mapping[0]['height']
        plane.set_air_plane_params(params)
        # plane.air_plane_params.primary_weapon_reload_time = 0
        # plane.air_plane_params.secondary_weapon_reload_time = 0
        plane.load_sprite('objects/{}.png'.format(plane_name))
        plane.air_plane_sprites.roll_mapping = roll_mapping
        plane.air_plane_sprites.pitch_mapping = pitch_mapping
        # 设置主武器和副武器的贴图资源
        sprite, rect = self.get_bullet_sprite('bullet' + str(param['mainweapon'] + 1))
        plane.air_plane_sprites.primary_bullet_sprite = get_rect_sprite(rect, sprite)
        # 注意此处获取的 sprite 应该旋转 90 度
        sprite, rect = self.get_bullet_sprite('bullet' + str(param['secondweapon']))
        plane.air_plane_sprites.secondary_bullet_sprite = get_rect_sprite(rect, sprite)

        explode_sub_textures, explode_sprite = self.get_explode_animation()
        plane.explode_sub_textures = explode_sub_textures
        plane.explode_sprite = explode_sprite
        # 刷新一下对应的 sprite, 防止出 bug
        plane.get_sprite()

        return plane


class FightingAircraftGame:
    def __init__(self):
        # 游戏必要的参数配置
        self.queue_current_players = 0
        self.room_max_player_number = 0
        self.server_port = 4444
        self.server_address = '127.0.0.1'
        self.player_id = 0
        self.game_name = "FightingAircraft"
        self.game_window_size = 1080, 720  # 设置窗口大小
        self.map_size = np.zeros((2,))
        # 游戏的资源加载
        self.game_resources = GameResources()
        self.game_render = GameRender()
        self.player_plane = None
        # 游戏的渲染
        self.screen = None
        # 游戏网络连接
        self.client = TcpClientTools()
        # 游戏的用户输入
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
        # 游戏运行的帧率和时钟控制
        self.fps_render = 60  # 渲染帧
        self.fps_physics = 30  # 逻辑帧
        self.fps_sync = 15  # 同步帧
        self.clock_render = pg.time.Clock()  # 渲染线程的时钟
        self.clock_sync = pg.time.Clock()
        self.clock_fixed_update = pg.time.Clock()
        # 游戏多线程创建及同步控制
        self.render_frame_idx = 0  # 从目前逻辑帧开始到当前应该运行的渲染帧下标
        self.local_physic_time_stamp = 0  # 物理运行的帧率计数
        self.local_render_time_stamp = 0  # 渲染运行的帧率计数
        self.local_sync_time_stamp = 0  # 同步帧的帧数计数
        self.sync_frames_cache = []     # 从服务器同步的渲染帧缓存数组
        self.history_frames = []        # 整局游戏的所有运行的历史逻辑帧记录，用于历史记录回放等操作

        self.is_game_ready = False      # 游戏是否开始
        self.exit_event = threading.Event() # 游戏是否结束的退出事件
        self.lock = threading.RLock()  # 线程锁，保证渲染和物理运算的顺序
        self.thread_render = None  # 渲染线程
        self.thread_fixed_update = None  # 逻辑运算线程

        # ----------------------------------------------------------------
        '''
        关于此处游戏总体设计方案的修改更新：
        1. 飞机管理采用一个统一的飞机链表
        2. 关于碰撞检测采用两个Group, 分别用来存储对应的 team1 和 team2 的碰撞单位
        3. 炮台由于本身有两个部分：底座和可旋转的炮管，需要单独一个list进行渲染
        4. 对于房屋，有两个不同的状态：完好和摧毁，需要单独一个list进行渲染
        '''
        # 为了便于更新内容，创建了三个组，分别是：所有飞机，敌方飞机，我方飞机
        self.id_plane_mapping: Dict[int, AirPlane] = {}
        # 便于碰撞检测
        self.team1_group = pygame.sprite.Group()
        self.team2_group = pygame.sprite.Group()
        # 制作一个list保存所有游戏里面需要物理更新的内容
        # 采用一个 objects 的 map 保存所有的物品及对应的内容，不用整其他花里胡哨的内容
        self.game_objects = {}
        self.list_turrets: List[Turret] = []
        self.list_buildings: List[Building] = []
        self.list_explodes: List[Explode] = []
        # # 将所有的物体全部包含在 map 中
        # self.game_objects['turrets'] = self.list_turrets
        # self.game_objects['buildings'] = self.list_buildings
        # self.game_objects['explodes'] = self.list_explodes

        # 游戏运行日志
        self.is_use_logger = False
        self.logger_file_name = 'run_physic.log'
        self.logger = None

    def init_game(self):
        """
        初始化游戏的一些必要组件，例如网络和资源加载
        :return:
        """
        '''
        游戏整体设计：
        1. 同步帧：
        逻辑帧整体处理用户输入及服务器同步
        2. 逻辑帧
        逻辑帧整体处理在指定用户输入下的逻辑运算
        3. 渲染帧
        渲染帧整体处理在指定的逻辑运算情境下渲染的精细程度
        主函数步骤设计：
        '''
        if self.is_use_logger:
            self.logger = setup_logging(self.logger_file_name)

        pg.init()  # 初始化pg
        self.screen = pg.display.set_mode(self.game_window_size)  # 显示窗口
        pg.display.set_caption(self.game_name)
        # 解决输入法问题
        # 模拟按下 Shift 键
        pyautogui.keyDown('shift')
        # 暂停 0.01s
        pyautogui.sleep(0.01)
        # 松开 Shift 键
        pyautogui.keyUp('shift')

        # 连接网络并发送匹配请求
        self.client.set_callback_fun(self.callback_recv)

        config_data = json.load(open('config.json', 'r'))
        # 设置连接信息
        self.server_address = config_data.get('server_address', '172.21.174.158')
        self.server_port = config_data.get('server_port', 4444)
        self.client.connect_to_server(self.server_address, self.server_port)
        data = {
            "command": CommandType.cmd_login.value,
            "player_id": self.player_id,
            # "plane_name": random.choice(list(self.game_resources.airplane_info_map.keys()))
            "plane_name": 'Bf110'
        }
        # random.choice(list(self.game_resources.airplane_info_map.keys()))
        self.client.send(json.dumps(data), pack_data=True, data_type=DataType.TypeString)
        # self.client.send(json.dumps({'command': CommandType.cmd_none.value}), pack_data=True, data_type=DataType.TypeString)

        # 设置渲染线程为子线程
        self.thread_render = threading.Thread(target=self.render, daemon=True)
        self.thread_fixed_update = threading.Thread(target=self.fixed_update, daemon=True)
        self.thread_render.start()
        self.thread_fixed_update.start()

        while True:
            # 游戏没开始的话就处理输入内容，防止程序假死
            self.input_manager()  # 输入管理
            self.clock_sync.tick(self.fps_sync)  # 获取时间差，控制帧率

    def callback_recv(self, cmd, params):
        if cmd == CallbackCommand.RecvData:
            data = params['data']
            data = json.loads(data.decode())
            cmd = CommandType(data['command'])
            if cmd == CommandType.cmd_login_resp:
                self.player_id = data['player_id']
                # self.room_max_player_number = data['room_max_player_number']
            elif cmd == CommandType.cmd_matching_successful:
                print('matching successfully. ')
                self.lock.acquire()
                # 加载地图
                self.game_render.game_window_size = np.array(self.game_window_size).reshape((2,))
                map_xml_name, _ = self.game_resources.get_map(data['map_id'])
                self.game_render.load_map_xml(map_xml_name)
                self.map_size = self.game_render.get_map_size()

                planes = data['planes']
                for plane_info in planes:
                    new_plane = self.game_resources.get_plane(plane_info['plane_name'], self.list_explodes)
                    new_plane.set_map_size(self.map_size)
                    new_plane.set_position(np.array([plane_info['position_x'], plane_info['position_y']]))
                    new_plane.get_air_plane_params().id = plane_info['player_id']
                    self.id_plane_mapping[plane_info['player_id']] = new_plane
                    if plane_info['player_id'] == self.player_id:
                        # 加载飞机
                        self.player_plane = new_plane
                        self.player_plane.team_number = 1
                        self.team1_group.add(new_plane)
                    else:
                        new_plane.team_number = 2
                        self.team2_group.add(new_plane)

                # ----------------------------------------------------------------
                # 防空炮构造
                # new_flak = Flak()
                # new_flak.set_map_size(self.map_size)
                # new_flak.set_position(np.array([2200, 2200]))
                # new_flak.target_obj = self.player_plane
                # sprite, rect = self.game_resources.get_turret_sprite('turret')
                # new_flak.set_sprite(get_rect_sprite(rect, sprite))
                # sprite, rect = self.game_resources.get_bullet_sprite('bullet2')
                # new_flak.set_bullet_sprite(get_rect_sprite(rect, sprite))
                # new_flak.team_number = 2
                #
                # self.list_turrets.append(new_flak)
                # self.team2_group.add((new_flak))
                # ---------------------------------------------------------------
                # 房屋构建
                new_building = Building(render_list=self.list_buildings, list_explodes=self.list_explodes)
                new_building.set_map_size(self.map_size)
                sprite, rect = self.game_resources.get_building_sprite('building01', state='body')
                new_building.body_sprite = get_rect_sprite(rect, sprite)
                sprite, rect = self.game_resources.get_building_sprite('building01', state='ruins')
                new_building.ruin_sprite = get_rect_sprite(rect, sprite)
                new_building.set_sprite(new_building.body_sprite)
                new_building.set_position(np.array([2500, 2200]))
                explode_sub_textures, explode_sprite = self.game_resources.get_explode_animation()
                new_building.explode_sub_textures = explode_sub_textures
                new_building.explode_sprite = explode_sprite
                new_building.team_number = 2
                self.list_buildings.append(new_building)
                self.team2_group.add((new_building))

                self.local_physic_time_stamp = 0
                # self.local_render_time_stamp = 0
                # 进行游戏必要的同步变量设置
                self.is_game_ready = True
                self.lock.release()
            elif cmd == CommandType.cmd_frame_update:
                self.lock.acquire()
                self.sync_frames_cache.append(data)
                self.history_frames.append(data)
                self.lock.release()
            elif cmd == CommandType.cmd_matching_state_change:
                self.room_max_player_number = data['room_max_player_number']
                self.queue_current_players = data['queue_current_players']
        elif cmd == CallbackCommand.SocketClose:
            print('socket closed. ')

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

        # 定义一个输入状态量
        input_state = InputState.NoInput
        if self.key_states[pg.K_UP] or self.key_states[pg.K_w]:
            input_state = input_state | InputState.SpeedUp
            # self.player_plane.speed_up()
        elif self.key_states[pg.K_DOWN] or self.key_states[pg.K_s]:
            input_state = input_state | InputState.SlowDown
            # self.player_plane.slow_down()
        if self.key_states[pg.K_LEFT] or self.key_states[pg.K_a]:
            input_state = input_state | InputState.TurnLeft
            # self.player_plane.turn_left()
        elif self.key_states[pg.K_RIGHT] or self.key_states[pg.K_d]:
            input_state = input_state | InputState.TurnRight
            # self.player_plane.turn_right()
        elif self.key_states[pg.K_q]:
            input_state = input_state | InputState.SharpTurnLeft
            # self.player_plane.sharply_turn_left()
        elif self.key_states[pg.K_e]:
            input_state = input_state | InputState.SharpTurnRight
            # self.player_plane.sharply_turn_right()
        elif self.key_states[pg.K_SPACE]:
            if self.player_plane.plane_type != PlaneType.Bomber:
                input_state = input_state | InputState.Pitch
            # self.player_plane.pitch()
        elif self.key_states[pg.K_f]:
            input_state = input_state | InputState.Roll
            # self.player_plane.roll()

        if self.key_states[pg.K_j]:
            input_state = input_state | InputState.PrimaryWeaponAttack
            # self.player_plane.primary_fire()
        elif self.key_states[pg.K_k]:
            input_state = input_state | InputState.SecondaryWeaponAttack
            # self.player_plane.secondary_fire()

        if self.is_game_ready:
            data = {
                "command": CommandType.cmd_player_action.value,
                "match_id": 0,
                "player_id": self.player_id,
                "action": input_state.value
            }

            # 注意同步数据
            self.lock.acquire()
            self.client.send(json.dumps(data), pack_data=True, data_type=DataType.TypeString)
            self.lock.release()

    def update_plane_input_state(self, actions):
        """
        更新飞机的输入状态
        """
        for key, value in self.id_plane_mapping.items():
            key = str(key)
            if key in actions.keys():
                value.input_state = InputState(actions[key])
            else:
                value.input_state = InputState.NoInput

    def check_bullet_collision(self, plane):
        """
        执行碰撞检测
        """
        crashed = {}
        if plane.team_number == 1:
            crashed = pygame.sprite.groupcollide(
                plane.bullet_group, self.team2_group, False, False)
            if crashed:
                for bullet in crashed:
                    # --------------------------------
                    # 首先利用精确检测看两者是否真正相交
                    if pygame.sprite.collide_mask(bullet, crashed[bullet][0]) is not None:
                        # 然后尝试给飞机对应的伤害
                        sprite = crashed[bullet][0]
                        if bullet.explode(sprite):
                            print('enemy eliminated. ')
                            sprite.on_death()
                            self.team2_group.remove(sprite)
        elif plane.team_number == 2:
            crashed = pygame.sprite.groupcollide(
                plane.bullet_group, self.team1_group, False, False)
            if crashed:
                for bullet in crashed:
                    # --------------------------------
                    # 首先利用精确检测看两者是否真正相交
                    if pygame.sprite.collide_mask(bullet, crashed[bullet][0]) is not None:
                        # 然后尝试给飞机对应的伤害
                        sprite = crashed[bullet][0]
                        if bullet.explode(sprite):
                            print('enemy eliminated. ')
                            sprite.on_death()
            self.team2_group.remove(sprite)
        else:
            print('unknown team_number: {}'.format(plane.team_number))
        # return crashed

    def update_plane_physics(self, delta_time):
        """
        更新飞机的物理状态
        """
        # ----------------------------------------------------------------
        # 飞机飞行状态的更新
        for plane in self.id_plane_mapping.values():
            plane.fixed_update(delta_time=delta_time)
            if self.is_use_logger:
                self.logger.debug(
                    json.dumps({'physic_frame': self.local_physic_time_stamp, 'input': plane.input_state,
                                'id': plane.get_air_plane_params().id}))
            for bullet in plane.bullet_group:
                bullet.fixed_update(delta_time=delta_time)
                # ----------------------------------------------------------------
            # 碰撞检测
            self.check_bullet_collision(plane)

        # ----------------------------------------------------------------
        # 防空炮姿态更新
        for turret in self.list_turrets:
            turret.fixed_update(delta_time=delta_time)
            for bullet in turret.bullet_group:
                bullet.fixed_update(delta_time=delta_time)
            # 碰撞检测
            self.check_bullet_collision(turret)

        # ----------------------------------------------------------------
        # 爆炸效果的更新
        for explode in self.list_explodes:
            explode.fixed_update(delta_time=delta_time)


    def fixed_update(self):
        """
        运行主游戏逻辑：
        针对网络发送的运行数据，本地接收时间是不固定的，但是必须要用固定的时间间隔去运行这些不固定间隔的数据
        :return:
        """
        delta_time = np.round(1000 / self.fps_physics, decimals=2)  # 物理运行的速度应该是固定的服务器的间隔，为了保证统一，保留两位小数

        # 此处只有物理运行，关于图形渲染是一个新的单独的线程
        while not self.exit_event.is_set():
            if self.is_game_ready:
                self.lock.acquire()
                # 首先要刷新渲染的起始时间
                self.render_frame_idx = 0
                '''
                此处的逻辑应该是首先检查服务器那边发过来同步帧的缓存数量是否大于1，如果大于1的话就得尽快运行到缓存还剩1的那个状态，
                假如同步帧和逻辑帧之间的倍数为3，那么缓存为1表示还有5个逻辑帧的时间接收下一个同步帧
                处理方式：
                如果此时缓存帧有1个，那么运行速度按照客户端正常的逻辑渲染速度
                # --------------------------------
                self.sync_frames_cache:
                {"command": CommandType.cmd_frame_update.value,
                  'sync_time_stamp': 0,
                  "actions": [
                        "player_id": action
                        ...
                  ]}
                '''
                frame_step = self.fps_physics / self.fps_sync

                # 此处处理的是快进环节，可以在数据包堆积的时候快进处理没跟上的同步帧数据
                for sync_frame in self.sync_frames_cache[:-1]:
                    # 如果需要同步用户输入，就同步用户输入
                    sync_2_physic_frame = sync_frame['sync_time_stamp'] * frame_step
                    # if (self.local_physic_time_stamp % frame_step == 0
                    #         and self.local_physic_time_stamp == sync_2_physic_frame):
                    while (sync_frame['sync_time_stamp'] - 1) * frame_step < self.local_physic_time_stamp <= sync_2_physic_frame:
                        # 先更新飞机的输入状态
                        self.update_plane_input_state(sync_frame['actions'])
                        # 物理运算
                        self.update_plane_physics(delta_time=delta_time)
                        self.local_physic_time_stamp += 1

                    # 删除目前已经运行的逻辑帧
                    if self.is_use_logger:
                        self.logger.debug(
                            json.dumps({'physic_frame': self.local_physic_time_stamp, 'actions': sync_frame['actions']}))
                    self.sync_frames_cache.remove(sync_frame)
                    self.local_sync_time_stamp += 1

                # 此处只剩一个同步帧，可以慢慢的运行物理逻辑等待服务器下一个同步帧的到来
                if (len(self.sync_frames_cache) == 1 and
                        self.sync_frames_cache[0]['sync_time_stamp'] * frame_step >= self.local_physic_time_stamp):
                    # 先更新飞机的输入状态
                    self.update_plane_input_state(self.sync_frames_cache[0]['actions'])
                    # 物理运算
                    self.update_plane_physics(delta_time=delta_time)
                    self.local_physic_time_stamp += 1

                    # print('\rserver sync t_s: {}, local sync t_s: {}, difference: {}'.format(
                    #     self.sync_frames_cache[0]['sync_time_stamp'],
                    #     self.local_sync_time_stamp,
                    #     self.sync_frames_cache[0]['sync_time_stamp'] - self.local_sync_time_stamp), end='')
                self.lock.release()

            # self.input_manager()  # 输入管理
            self.clock_fixed_update.tick(self.fps_physics)  # 获取时间差，控制帧率


    def render(self):
        print('render thread started. ')
        render_frame_time_diff = np.round(1000 / self.fps_render, decimals=2)
        self.render_frame_idx = 0
        font = pg.font.Font(None, 36)
        self.game_render.draw_collision_box = False
        self.game_render.set_screen(self.screen)
        render_frame_count = self.fps_render / self.fps_physics

        while not self.exit_event.is_set():
            self.lock.acquire()
            if self.is_game_ready:
                # 首先判断程序目前渲染帧数，拒绝提前渲染，不然会出现不必要的抖动
                if self.render_frame_idx < render_frame_count:
                    # self.render_frame_idx += delta_time
                    delta_time = self.render_frame_idx * render_frame_time_diff
                    pos, dir_v = self.player_plane.move(delta_time=delta_time)
                    self.game_render.render_map(pos, screen=self.screen)

                    # ----------------------------------------------------------------
                    # 地面内容更新
                    # 进行防空炮的更新
                    for turret in self.list_turrets:
                        self.game_render.render_turret(turret=turret, delta_time=delta_time)
                        for bullet in turret.bullet_group:
                            self.game_render.render_bullet(bullet=bullet, delta_time=delta_time)

                    # 进行建筑的更新
                    for building in self.list_buildings:
                        self.game_render.render_building(building=building)

                    # -----------------------------------------------------------------
                    # 空中物体更新
                    text = font.render(
                        'Engine temperature: {:.2f}, Speed: {:.2f}, position: [{:.2f}, {:.2f}]'.format(
                            self.player_plane.get_engine_temperature(), self.player_plane.velocity,
                            pos[0][0], pos[1][0]),
                        True, (0, 0, 0))
                    for plane in self.id_plane_mapping.values():
                        self.game_render.render_plane(plane=plane, team_id=plane.team_number,
                                                      delta_time=delta_time)
                        # print('\r obj count: {}'.format(len(self.player_plane.bullet_list)), end='')
                        for bullet in plane.bullet_group:
                            self.game_render.render_bullet(bullet=bullet, delta_time=delta_time)

                    for explode in self.list_explodes:
                        self.game_render.render_building(building=explode)

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
                    for plane in self.id_plane_mapping.values():
                        pos = plane.get_position()
                        if plane.team_number == 1:
                            pygame.draw.circle(
                                self.screen, (0, 255, 0),
                                (thumbnail_map_render_left + pos[0][0] * scale,
                                 pos[1][0] * scale), 2)
                        else:
                            pygame.draw.circle(
                                    self.screen, (255, 0, 0),
                                    (thumbnail_map_render_left + pos[0][0] * scale,
                                     pos[1][0] * scale), 2)

                    for turret in self.list_turrets:
                        pos = turret.get_position()
                        pygame.draw.circle(
                            self.screen, (0, 0, 255),
                            (thumbnail_map_render_left + pos[0][0] * scale,
                             pos[1][0] * scale), 2)

                    for building in self.list_buildings:
                        pos = building.get_position()
                        pygame.draw.circle(
                            self.screen, (0, 125, 125),
                            (thumbnail_map_render_left + pos[0][0] * scale,
                             pos[1][0] * scale), 2)

                    # 然后绘制框框
                    pos = self.player_plane.get_position()
                    pygame.draw.rect(
                        self.screen, (255, 0, 0),
                        (thumbnail_map_render_left + (pos[0][0] - 0.5 * self.game_window_size[0]) * scale,
                         (pos[1][0] - 0.5 * self.game_window_size[1]) * scale,
                         self.game_window_size[0] * scale,
                         self.game_window_size[1] * scale), 2)

                    self.render_frame_idx += 1
            else:
                # 清屏
                self.screen.fill((255, 255, 255))
                # 此处需要显示提示信息，等待另外的玩家进入游戏
                text = font.render(
                    f"Waiting for {self.room_max_player_number} players. Currently in queue: {self.queue_current_players}...",
                    True, (0, 0, 0))
                text_rect = text.get_rect(center=(self.game_window_size[0] // 2, self.game_window_size[1] // 2))
                self.screen.blit(text, text_rect.topleft)

            pg.display.flip()  # 更新全部显示
            self.lock.release()
            self.clock_render.tick(self.fps_render)
            # delta_time = 1000 / self.fps_render


if __name__ == '__main__':
    game = FightingAircraftGame()
    game.init_game()
