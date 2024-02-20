import base64
import json
import logging
import os
import tkinter as tk
from collections import OrderedDict
from tkinter import messagebox
import torch
from memory_profiler import profile
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
from torch import nn

from server import FightingAircraftGameServer
from utils.SocketTcpTools import *
from utils.cls_airplane import *
from utils.cls_building import *
from utils.cls_explode import Explode
from utils.cls_game_data import *
from utils.cls_game_render import *
from utils.cls_genetic_algorithm import GeneticAlgorithm


class MenuItem:
    def __init__(self, name, action=None):
        self.name = name
        self.action = action
        self.rect = (0, 0, 0, 0)
        self.children = []

    def has_children(self):
        return len(self.children)

    def add_menu_item(self, menu_item):
        self.children.append(menu_item)


class GameMenu:
    def __init__(self, game_window_size):
        self.selected_menu = None
        self.game_window_size = game_window_size
        self.menu = MenuItem('主菜单')
        self.current_level = 0
        self.current_index = 0
        self.line_spacing = 10
        self.rect_width = 300
        self.mouse_pos = (0, 0)
        self.prev_mouse_buttons = (False, False, False)
        # 显示的参数
        self.font_size = 36
        self.font = pygame.font.Font(None, self.font_size)
        # 计算菜单总高度
        menu_height = len(self.menu.children) * (self.font_size + self.line_spacing) - self.line_spacing
        self.y_position = (self.game_window_size[1] - menu_height) // 2 + 100

    def update_menu_rect(self):
        # 更新菜单的位置
        for i, item in enumerate(self.menu.children):
            # 计算矩形位置和大小
            rect_x = (self.game_window_size[0] - self.rect_width) // 2  # 左侧边界
            rect_y = self.y_position + i * (self.font_size + self.line_spacing)  # 顶部边界
            rect_width = self.rect_width  # 矩形宽度，即菜单栏的宽度
            rect_height = self.font_size  # 矩形高度，即文字的高度

            item.rect = (rect_x, rect_y, rect_width, rect_height)

    def display_menu(self, screen):
        # 绘制菜单
        for i, item in enumerate(self.menu.children):
            # 计算文字居中位置
            text_width, text_height = self.font.size(item.name)
            text_x = self.game_window_size[0] // 4 + (self.game_window_size[0] // 2 - text_width) // 2
            text_y = self.y_position + i * (self.font_size + self.line_spacing) + (self.font_size - text_height) // 2

            # 检测鼠标位置是否在矩形范围内
            if item == self.selected_menu:
                # 高亮显示选中的菜单项
                pygame.draw.rect(
                    screen, (100, 100, 100), item.rect, 0)  # 填充矩形
            else:
                # 绘制普通矩形
                pygame.draw.rect(
                    screen, (0, 0, 0), item.rect, 3)  # 绘制矩形的宽度

            # 绘制文本
            text_surface = self.font.render(item.name, True, (0, 0, 0))
            screen.blit(text_surface, (text_x, text_y))

    def handle_input(self):
        """
        处理输入内容
        :return:
        """
        self.mouse_pos = pygame.mouse.get_pos()
        mouse_button_states = pygame.mouse.get_pressed()
        self.selected_menu: MenuItem = None
        for item in self.menu.children:
            if (item.rect[0] <= self.mouse_pos[0] <= item.rect[0] + item.rect[2]
                    and item.rect[1] <= self.mouse_pos[1] <= item.rect[1] + item.rect[3]):
                self.selected_menu = item

        if self.selected_menu is not None:
            # print(f'\rselected menu: {self.selected_menu.name}', end='')
            # 判断按键状态，确定是否点击了对应的菜单按钮
            if mouse_button_states[0] and not self.prev_mouse_buttons[0]:
                if self.selected_menu.action is not None:
                    # 如果该菜单有绑定的函数，那么执行绑定的函数
                    self.selected_menu.action()
                else:
                    print(f'menu click: {self.selected_menu.name}, no callback function!!!')

        self.prev_mouse_buttons = mouse_button_states


class FightingAircraftGame:
    def __init__(self):
        self.player_plane_index = 0
        self.main_game: MainGame = None
        # 游戏
        self.genetic_manager: GeneticAlgorithm = None
        # 游戏必要的参数配置
        self.queue_current_players = 0
        self.room_max_player_number = 0
        # self.server_port = 4444
        # self.server_address = '127.0.0.1'
        self.player_id = 0
        # self.game_name = "FightingAircraft"
        self.game_window_size = 1080, 720  # 设置窗口大小
        self.map_size = np.zeros((2,))
        # 游戏的资源加载
        self.game_resources = GameResources()
        self.game_render = GameRender()
        self.player_plane: AirPlane = None
        # 游戏的渲染
        self.screen = None
        # 游戏网络连接
        # self.onlineNodeEnabled = True
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
        # # 游戏运行的帧率和时钟控制
        self.fps_render = 30  # 渲染帧
        self.fps_physics = 30  # 逻辑帧
        self.fps_sync = 15  # 同步帧
        # self.clock_render = pg.time.Clock()  # 渲染线程的时钟
        # self.clock_sync = pg.time.Clock()
        # self.clock_fixed_update = pg.time.Clock()
        # 游戏多线程创建及同步控制
        self.render_frame_idx = 0  # 从目前逻辑帧开始到当前应该运行的渲染帧下标
        self.local_physic_time_stamp = 0  # 物理运行的帧率计数
        self.local_render_time_stamp = 0  # 渲染运行的帧率计数
        self.local_sync_time_stamp = 0  # 同步帧的帧数计数
        self.sync_frames_cache = []  # 从服务器同步的渲染帧缓存数组
        self.history_frames = []  # 整局游戏的所有运行的历史逻辑帧记录，用于历史记录回放等操作

        self.is_game_ready = False  # 游戏是否开始
        self.exit_event = threading.Event()  # 游戏是否结束的退出事件
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
        self.game_data = GameData()
        # 每次跑两分钟
        # self.game_time_max_stamp = 3600
        self.game_time_max_stamp = 999999
        # 游戏运行日志
        self.is_use_logger = False
        self.logger_file_name = 'run_physic.log'
        self.logger = None


    def init_game(self, main_game):
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
        if self.is_game_ready is False:
            self.main_game = main_game
            self.screen = main_game.screen
            self.genetic_manager = main_game.genetic_manager

            # 和网络连接相关的内容
            # 连接网络并发送匹配请求
            # self.client.socket_init()
            self.client.set_callback_fun(self.callback_recv)
            # config_data = json.load(open('config.json', 'r'))
            # # 设置连接信息
            # self.server_address = config_data.get('server_address', '172.21.174.158')
            # self.server_port = config_data.get('server_port', 4444)
            self.client.connect_to_server(main_game.server_address, main_game.server_port)

        data = {
            "command": CommandType.cmd_login.value,
            "player_id": self.player_id,
            # "plane_name": random.choice(list(self.game_resources.airplane_info_map.keys()))
            "plane_name": 'Bf110'
        }
        # random.choice(list(self.game_resources.airplane_info_map.keys()))
        self.client.send(json.dumps(data), pack_data=True, data_type=DataType.TypeString)
        # self.client.send(json.dumps({'command': CommandType.cmd_none.value}), pack_data=True, data_type=DataType.TypeString)


    def game_over(self):
        print('game over, new game starting...')

        data = {
            "command": CommandType.cmd_game_over.value,
            "player_id": self.player_id
        }
        # random.choice(list(self.game_resources.airplane_info_map.keys()))
        self.client.send(json.dumps(data), pack_data=True, data_type=DataType.TypeString)
        # 然后进行优化处理并进行下一轮的游戏训练
        max_score = self.genetic_manager.selection(list(self.game_data.id_plane_mapping.values()))

        # self.client.close_socket()
        # 初始化游戏
        self.init_game(self.main_game)
        self.is_game_ready = False
        self.local_physic_time_stamp = 0
        self.local_sync_time_stamp = 0

    def create_new_game(self, data):
        """
        根据 data 的 map 内容创建一个新的游戏
        :param data:
        :return:
        """
        # self.player_id = data['planes'][0]['player_id']
        print('matching successfully. ')
        self.lock.acquire()
        # 加载地图
        self.game_render.game_window_size = np.array(self.game_window_size).reshape((2,))
        # map_xml_name, _ = self.game_resources.get_map(data['map_id'])
        map_xml_name, _, map_info = self.game_resources.get_map(37)
        # self.game_render.load_map_xml(map_xml_name)
        self.game_render.set_map_info(map_info)
        # ----------------------------------------------------------------
        # print('start print tiles: ')
        # for i in range(self.game_render.height):
        #     for j in range(self.game_render.width):
        #         print(tiles[i * self.game_render.height + j], end='\t')
        #     print('\n')
        # print('tiles print done!')
        # ----------------------------------------------------------------
        self.map_size = self.game_render.get_map_size()
        planes = data['planes']

        # 如果已经有人口了，那么只需要设置参数即可
        if len(self.genetic_manager.population):
            id_mapping = self.game_data.id_plane_mapping
            # 重置对应的飞机数据内容
            self.game_data.reset_game_data()
            self.game_data.id_plane_mapping = id_mapping
            for plane, agent, plane_info in zip(id_mapping.values(), self.genetic_manager.population, planes):
                plane.agent_network = agent
                plane.durability = 200
                plane.score = 0
                plane.set_position(np.array([plane_info['position_x'], plane_info['position_y']]))
                if plane_info['player_id'] < self.genetic_manager.pop_size * 0.5:
                    # 加载飞机
                    # self.game_data.add_team_airplanes(1, new_plane)
                    plane.set_direction_vector(np.array([-1, 0]).reshape((2, 1)))
                else:
                    # self.game_data.add_team_airplanes(2, new_plane)
                    # new_plane.set_direction_vector(np.random.rand(2, 1))
                    plane.set_direction_vector(np.array([1, 0]).reshape((2, 1)))
                self.game_data.add_team_airplanes(plane.team_number, plane)
        else:
            # 重置对应的飞机数据内容
            self.game_data.reset_game_data()
            for plane_info in planes:
                plane_type, param, sprites, roll_mapping, pitch_mapping, explode_animation = (
                    self.game_resources.get_plane(plane_info['plane_name']))
                team_number = plane_info['player_id']
                if plane_type == PlaneType.Fighter:
                    new_plane = FighterJet(team_number, self.game_data)
                elif plane_type == PlaneType.AttackAircraft:
                    new_plane = AttackAircraft(team_number, self.game_data)
                elif plane_type == PlaneType.Bomber:
                    new_plane = Bomber(team_number, self.game_data)
                else:
                    new_plane = Bomber(team_number, self.game_data)

                new_plane.set_plane_params(
                    plane_info['plane_name'], param, sprites, roll_mapping, pitch_mapping, explode_animation)

                new_plane.durability = 200

                new_plane.set_map_size(self.map_size)
                new_plane.set_position(np.array([plane_info['position_x'], plane_info['position_y']]))
                new_plane.get_air_plane_params().id = plane_info['player_id']
                # 设置主武器和副武器的贴图资源
                new_plane.air_plane_sprites.primary_bullet_sprite = get_rect_sprite(
                    self.game_resources.get_bullet_sprite('bullet' + str(param['mainweapon'] + 1)))
                # 注意此处获取的 sprite 应该旋转 90 度
                new_plane.air_plane_sprites.secondary_bullet_sprite = get_rect_sprite(
                    self.game_resources.get_bullet_sprite('bullet' + str(param['secondweapon'])))
                self.game_data.id_plane_mapping[plane_info['player_id']] = new_plane
                # if plane_info['player_id'] == self.player_id:
                #     # 加载飞机
                #     self.player_plane = new_plane
                #     self.player_plane.durability = 9999999
                #     self.game_data.add_team_airplanes(1, new_plane)
                # else:
                #     self.game_data.add_team_airplanes(2, new_plane)
                #     # new_plane.set_direction_vector(np.random.rand(2, 1))
                #     new_plane.set_direction_vector(np.array([1, 0]).reshape((2, 1)))

                if self.player_plane is None:
                    self.player_plane = new_plane

                # 所有飞机都加载这个模型
                new_plane.load_agent_pth('pth/gen_46_score_-87.65.pth')

                # ----------------------------------------------------------------
                # 遗传算法
                if plane_info['player_id'] < self.genetic_manager.pop_size * 0.5:
                    # 加载飞机
                    self.game_data.add_team_airplanes(1, new_plane)
                    new_plane.set_direction_vector(np.array([-1, 0]).reshape((2, 1)))
                else:
                    self.game_data.add_team_airplanes(2, new_plane)
                    # new_plane.set_direction_vector(np.random.rand(2, 1))
                    new_plane.set_direction_vector(np.array([1, 0]).reshape((2, 1)))
                # 开始为遗传算法增加种群内容
                self.genetic_manager.population.append(new_plane.agent_network)

        # # ----------------------------------------------------------------
        # # 防空炮构造
        # new_flak = self.game_resources.get_flak(
        #     2, self.game_data
        # )
        # new_flak.set_map_size(self.map_size)
        # new_flak.set_position(np.array([2200, 2200]))
        # new_flak.all_planes = self.game_data.id_plane_mapping.values()
        # self.game_data.add_team_turrets(2, new_flak)
        #
        # new_flak_1 = self.game_resources.get_flak(
        #     2, self.game_data
        # )
        # new_flak_1.set_map_size(self.map_size)
        # new_flak_1.set_position(np.array([2200, 2400]))
        # new_flak_1.all_planes = self.game_data.id_plane_mapping.values()
        # self.game_data.add_team_turrets(2, new_flak_1)
        # # ---------------------------------------------------------------
        # # 房屋构建
        # new_building = Building(
        #     2, self.game_data)
        # new_building.set_map_size(self.map_size)
        # new_building.body_sprite = get_rect_sprite(
        #     self.game_resources.get_building_sprite('building01', state='body'))
        # new_building.ruin_sprite = get_rect_sprite(
        #     self.game_resources.get_building_sprite('building01', state='ruins'))
        # new_building.set_sprite(new_building.body_sprite)
        # new_building.set_position(np.array([2500, 2200]))
        # explode_sub_textures, explode_sprite = self.game_resources.get_explode_animation()
        # new_building.explode_sub_textures = explode_sub_textures
        # new_building.explode_sprite = explode_sprite
        # self.game_data.add_team_buildings(2, new_building)

        self.local_physic_time_stamp = 0
        # self.local_render_time_stamp = 0
        # 进行游戏必要的同步变量设置
        self.is_game_ready = True
        self.lock.release()

    def callback_recv(self, cmd, params):
        if cmd == CallbackCommand.RecvData:
            data = params['data']
            data = json.loads(data.decode())
            cmd = CommandType(data['command'])
            if cmd == CommandType.cmd_login_resp:
                self.player_id = data['player_id']
                # self.room_max_player_number = data['room_max_player_number']
            elif cmd == CommandType.cmd_matching_successful:
                # self.player_id = data['planes'][0]['player_id']
                # data = {
                #     "command": 3,
                #     "sync_time_stamp": 0,
                #     "map_id": 17,
                #     "planes": [
                #         {"player_id": 1, "position_x": 2000, "position_y": 2000, "plane_name": "Bf110"},
                #         {"player_id": 2, "position_x": 2200, "position_y": 2000, "plane_name": "Bf110"},
                #         {"player_id": 3, "position_x": 2200, "position_y": 2400, "plane_name": "Bf110"}
                #     ]
                # }
                data = {
                    "command": 3,
                    "sync_time_stamp": 0,
                    "map_id": 17
                }
                planes = []
                half_pop_size = int(self.genetic_manager.pop_size * 0.5)
                map_size = np.array([10240, 10240])
                for i in range(half_pop_size):
                    planes.append(
                        {"player_id": i,
                         "position_x": np.random.rand()*map_size[0],
                         "position_y": np.random.rand()*map_size[1],
                         "plane_name": "Bf110"})

                for i in range(half_pop_size):
                    planes.append(
                        {"player_id": i + half_pop_size,
                         "position_x": np.random.rand()*map_size[0],
                         "position_y": np.random.rand()*map_size[1],
                         "plane_name": "Bf110"})
                data["planes"] = planes
                # self.lock.acquire()
                self.create_new_game(data=data)

                # self.game_over()
                # self.lock.release()
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

    def input_manager(self, event):
        # # 处理输入
        # for event in pg.event.get():  # 遍历所有事件
        #     if event.type == pg.QUIT:  # 如果单击关闭窗口，则退出
        #         self.client.close_socket()
        #         self.exit_event.set()
        #         self.thread_render.join()
        #         pg.quit()  # 退出pg
        #         sys.exit(0)

        preview_key_states = self.key_states.copy()
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

            # # 注意同步数据
            self.lock.acquire()
            if (self.key_states[pg.K_SPACE] is True) and (preview_key_states[pg.K_SPACE] is False):
                all_valid_plane_list = self.game_data.team1_airplanes + self.game_data.team2_airplanes
                if self.player_plane_index < len(all_valid_plane_list) - 1:
                    self.player_plane_index += 1
                else:
                    self.player_plane_index = 0
                self.player_plane = all_valid_plane_list[self.player_plane_index]

            self.client.send(json.dumps(data), pack_data=True, data_type=DataType.TypeString)
            self.lock.release()

    def update_plane_input_state(self, actions):
        """
        更新飞机的输入状态
        """
        # 控制飞机根据当前状态自行控制，所有都是
        for plane in self.game_data.team1_airplanes:
            if plane != self.player_plane:
                plane.ai_control(
                    self.player_plane.get_plane_states(self.game_data.team2_airplanes))

        for plane in self.game_data.team2_airplanes:
            if plane != self.player_plane:
                plane.ai_control(
                    self.player_plane.get_plane_states(self.game_data.team1_airplanes))

        # ----------------------------------------------------------------
        # 如果是玩家，可以控制当前飞机
        key = str(self.player_id)
        if key in actions.keys():
            self.player_plane.input_state = InputState(actions[key])
        else:
            self.player_plane.input_state = InputState.NoInput

        # for key, value in self.game_data.id_plane_mapping.items():
        #     key = str(key)
        #     if key in actions.keys():
        #         value.input_state = InputState(actions[key])
        #     else:
        #         value.input_state = InputState.NoInput



    def check_bullet_collision(self, plane):
        """
        执行碰撞检测
        """
        # 空中检测
        crashed = self.game_data.get_air_crashed_group(
            plane.bullet_group, plane.team_number
        )
        if crashed:
            for bullet in crashed:
                # --------------------------------
                # 首先利用精确检测看两者是否真正相交
                if pygame.sprite.collide_mask(bullet, crashed[bullet][0]) is not None:
                    # 然后尝试给飞机对应的伤害
                    sprite = crashed[bullet][0]
                    bullet.parent.score += 1.5
                    if bullet.explode(sprite):
                        print('enemy eliminated. ')
        # 地面检测
        crashed = self.game_data.get_ground_crashed_group(
            plane.bullet_group, plane.team_number
        )
        if crashed:
            for bullet in crashed:
                # --------------------------------
                # 首先利用精确检测看两者是否真正相交
                if pygame.sprite.collide_mask(bullet, crashed[bullet][0]) is not None:
                    # 然后尝试给飞机对应的伤害
                    sprite = crashed[bullet][0]
                    if bullet.explode(sprite):
                        print('enemy eliminated. ')

    def update_plane_physics(self, delta_time):
        """
        更新飞机的物理状态
        """
        # ----------------------------------------------------------------
        # 飞机飞行状态的更新
        for plane in self.game_data.team1_airplanes + self.game_data.team2_airplanes:
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
        for turret in self.game_data.team1_turrets + self.game_data.team2_turrets:
            turret.fixed_update(delta_time=delta_time)
            for bullet in turret.bullet_group:
                bullet.fixed_update(delta_time=delta_time)
            # 碰撞检测
            self.check_bullet_collision(turret)

        # ----------------------------------------------------------------
        # 爆炸效果的更新
        for explode in self.game_data.list_explodes:
            explode.fixed_update(delta_time=delta_time)

    def fixed_update(self):
        """
        运行主游戏逻辑：
        针对网络发送的运行数据，本地接收时间是不固定的，但是必须要用固定的时间间隔去运行这些不固定间隔的数据
        :return:
        """
        delta_time = np.round(1000 / self.fps_physics, decimals=2)  # 物理运行的速度应该是固定的服务器的间隔，为了保证统一，保留两位小数
        # print(f'\r local stamp: {self.local_physic_time_stamp}', end='')
        # time_start = time.time()
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
                while (sync_frame[
                           'sync_time_stamp'] - 1) * frame_step < self.local_physic_time_stamp <= sync_2_physic_frame:
                    # 先更新飞机的输入状态
                    self.update_plane_input_state(sync_frame['actions'])
                    # 物理运算
                    self.update_plane_physics(delta_time=delta_time)
                    self.local_physic_time_stamp += 1

                # 删除目前已经运行的逻辑帧
                if self.is_use_logger:
                    self.logger.debug(
                        json.dumps(
                            {'physic_frame': self.local_physic_time_stamp, 'actions': sync_frame['actions']}))
                self.sync_frames_cache.remove(sync_frame)
                self.local_sync_time_stamp += 1
                if self.local_physic_time_stamp > self.game_time_max_stamp:
                    # 游戏结束
                    self.game_over()
                else:
                    print(f'\r local stamp: {self.local_physic_time_stamp}', end='')

            # 此处只剩一个同步帧，可以慢慢的运行物理逻辑等待服务器下一个同步帧的到来
            if (len(self.sync_frames_cache) == 1 and
                    self.sync_frames_cache[0]['sync_time_stamp'] * frame_step >= self.local_physic_time_stamp):
                # 先更新飞机的输入状态
                self.update_plane_input_state(self.sync_frames_cache[0]['actions'])
                # 物理运算
                self.update_plane_physics(delta_time=delta_time)
                self.local_physic_time_stamp += 1
                if self.local_physic_time_stamp > self.game_time_max_stamp:
                    # 游戏结束
                    self.game_over()
                else:
                    print(f'\r local stamp: {self.local_physic_time_stamp}', end='')
                # print('\rserver sync t_s: {}, local sync t_s: {}, difference: {}'.format(
                #     self.sync_frames_cache[0]['sync_time_stamp'],
                #     self.local_sync_time_stamp,
                #     self.sync_frames_cache[0]['sync_time_stamp'] - self.local_sync_time_stamp), end='')
            self.lock.release()

        # print(f'\rtime cost: {time.time() - time_start}', end='')
        # ----------------------------------------------------------------
        # delta_time = np.round(1000 / self.fps_physics, decimals=2)  # 物理运行的速度应该是固定的服务器的间隔，为了保证统一，保留两位小数
        #
        # # 此处只有物理运行，关于图形渲染是一个新的单独的线程
        # while not self.exit_event.is_set():
        #     if self.is_game_ready:
        #         self.lock.acquire()
        #         # 首先要刷新渲染的起始时间
        #         self.render_frame_idx = 0
        #         '''
        #         此处的逻辑应该是首先检查服务器那边发过来同步帧的缓存数量是否大于1，如果大于1的话就得尽快运行到缓存还剩1的那个状态，
        #         假如同步帧和逻辑帧之间的倍数为3，那么缓存为1表示还有5个逻辑帧的时间接收下一个同步帧
        #         处理方式：
        #         如果此时缓存帧有1个，那么运行速度按照客户端正常的逻辑渲染速度
        #         # --------------------------------
        #         self.sync_frames_cache:
        #         {"command": CommandType.cmd_frame_update.value,
        #           'sync_time_stamp': 0,
        #           "actions": [
        #                 "player_id": action
        #                 ...
        #           ]}
        #         '''
        #         frame_step = self.fps_physics / self.fps_sync
        #
        #         # 此处处理的是快进环节，可以在数据包堆积的时候快进处理没跟上的同步帧数据
        #         for sync_frame in self.sync_frames_cache[:-1]:
        #             # 如果需要同步用户输入，就同步用户输入
        #             sync_2_physic_frame = sync_frame['sync_time_stamp'] * frame_step
        #             # if (self.local_physic_time_stamp % frame_step == 0
        #             #         and self.local_physic_time_stamp == sync_2_physic_frame):
        #             while (sync_frame[
        #                        'sync_time_stamp'] - 1) * frame_step < self.local_physic_time_stamp <= sync_2_physic_frame:
        #                 # 先更新飞机的输入状态
        #                 self.update_plane_input_state(sync_frame['actions'])
        #                 # 物理运算
        #                 self.update_plane_physics(delta_time=delta_time)
        #                 self.local_physic_time_stamp += 1
        #
        #             # 删除目前已经运行的逻辑帧
        #             if self.is_use_logger:
        #                 self.logger.debug(
        #                     json.dumps(
        #                         {'physic_frame': self.local_physic_time_stamp, 'actions': sync_frame['actions']}))
        #             self.sync_frames_cache.remove(sync_frame)
        #             self.local_sync_time_stamp += 1
        #
        #         # 此处只剩一个同步帧，可以慢慢的运行物理逻辑等待服务器下一个同步帧的到来
        #         if (len(self.sync_frames_cache) == 1 and
        #                 self.sync_frames_cache[0]['sync_time_stamp'] * frame_step >= self.local_physic_time_stamp):
        #             # 先更新飞机的输入状态
        #             self.update_plane_input_state(self.sync_frames_cache[0]['actions'])
        #             # 物理运算
        #             self.update_plane_physics(delta_time=delta_time)
        #             self.local_physic_time_stamp += 1
        #
        #             # print('\rserver sync t_s: {}, local sync t_s: {}, difference: {}'.format(
        #             #     self.sync_frames_cache[0]['sync_time_stamp'],
        #             #     self.local_sync_time_stamp,
        #             #     self.sync_frames_cache[0]['sync_time_stamp'] - self.local_sync_time_stamp), end='')
        #         self.lock.release()
        #
        #     # self.input_manager()  # 输入管理
        #     self.clock_fixed_update.tick(self.fps_physics)  # 获取时间差，控制帧率

    def render(self):
        # print('render thread started. ')
        render_frame_time_diff = np.round(1000 / self.fps_render, decimals=2)
        self.render_frame_idx = 0
        font = pg.font.Font(None, 36)
        self.game_render.draw_collision_box = False
        self.game_render.set_screen(self.screen)
        render_frame_count = self.fps_render / self.fps_physics

        self.lock.acquire()
        if self.is_game_ready:
            # 首先判断程序目前渲染帧数，拒绝提前渲染，不然会出现不必要的抖动
            if self.render_frame_idx < render_frame_count:
                # self.render_frame_idx += delta_time
                delta_time = self.render_frame_idx * render_frame_time_diff
                pos, dir_v = self.player_plane.move(delta_time=delta_time)
                if self.player_plane.durability <= 0:
                    all_valid_plane_list = self.game_data.team1_airplanes + self.game_data.team2_airplanes
                    if len(all_valid_plane_list) > 0:
                        self.player_plane = all_valid_plane_list[0]
                self.game_render.render_map(pos, screen=self.screen)

                # ----------------------------------------------------------------
                # 地面内容更新
                # 进行防空炮的更新
                for turret in self.game_data.team1_turrets + self.game_data.team2_turrets:
                    self.game_render.render_turret(turret=turret, delta_time=delta_time)
                    for bullet in turret.bullet_group:
                        self.game_render.render_bullet(bullet=bullet, delta_time=delta_time)

                # 进行建筑的更新
                for building in self.game_data.team1_buildings + self.game_data.team2_buildings:
                    self.game_render.render_building(building=building)

                # -----------------------------------------------------------------
                # 空中物体更新
                text = font.render(
                    'Engine temperature: {:.2f}, Speed: {:.2f}, position: [{:.2f}, {:.2f}]'.format(
                        self.player_plane.get_engine_temperature(), self.player_plane.velocity,
                        pos[0][0], pos[1][0]),
                    True, (0, 0, 0))
                # 将文本绘制到屏幕上
                self.screen.blit(text, (10, 10))

                for plane in self.game_data.team1_airplanes + self.game_data.team2_airplanes:
                    self.game_render.render_plane(plane=plane, team_id=plane.team_number,
                                                  delta_time=delta_time)
                    # 渲染对应的子弹
                    for bullet in plane.bullet_group:
                        self.game_render.render_bullet(bullet=bullet, delta_time=delta_time)
                for explode in self.game_data.list_explodes:
                    self.game_render.render_explode(explode=explode)

                # --------------- 玩家游戏提醒 -----------------
                # 如果主控飞机有效的话，可以绘制对应的瞄准图标和对应的检测到的目标飞机
                if self.player_plane is not None:
                    player_plane_vector = self.player_plane.get_direction_vector()
                    # 绘制准星
                    player_plane_vector = player_plane_vector * 250
                    cross_position = (
                        0.5 * self.game_window_size[0] + player_plane_vector[0][0],
                        0.5 * self.game_window_size[1] - player_plane_vector[1][0]
                    )
                    sprite_position = self.game_resources.cross_hair_sprite.get_rect(
                        center=cross_position
                    )
                    self.screen.blit(
                        self.game_resources.cross_hair_sprite, sprite_position)

                    # 目标飞机检测并标记
                    if self.player_plane.detected_AAM_targets is not None:
                        self.game_render.render_box(self.player_plane.detected_AAM_targets)

                # 然后在右上角显示小地图
                thumbnail_map_sprite_rect = self.game_resources.thumbnail_map_sprite.get_rect()
                thumbnail_map_render_left = self.game_window_size[0] - thumbnail_map_sprite_rect.width
                self.screen.blit(
                    self.game_resources.thumbnail_map_sprite,
                    (thumbnail_map_render_left, 0))
                scale = thumbnail_map_sprite_rect.width / self.map_size[0]
                # 然后根据小地图的位置来显示不同的飞机在缩略图中的位置
                for plane in self.game_data.team1_airplanes + self.game_data.team2_airplanes:
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

                for turret in self.game_data.team1_turrets + self.game_data.team2_turrets:
                    pos = turret.get_position()
                    pygame.draw.circle(
                        self.screen, (0, 0, 255),
                        (thumbnail_map_render_left + pos[0][0] * scale,
                         pos[1][0] * scale), 2)

                for building in self.game_data.team1_buildings + self.game_data.team2_buildings:
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

        # pg.display.flip()  # 更新全部显示
        self.lock.release()
        # --------------------------------------------------------
        # print('render thread started. ')
        # render_frame_time_diff = np.round(1000 / self.fps_render, decimals=2)
        # self.render_frame_idx = 0
        # font = pg.font.Font(None, 36)
        # self.game_render.draw_collision_box = False
        # self.game_render.set_screen(self.screen)
        # render_frame_count = self.fps_render / self.fps_physics
        #
        # while not self.exit_event.is_set():
        #     self.lock.acquire()
        #     if self.is_game_ready:
        #         # 首先判断程序目前渲染帧数，拒绝提前渲染，不然会出现不必要的抖动
        #         if self.render_frame_idx < render_frame_count:
        #             # self.render_frame_idx += delta_time
        #             delta_time = self.render_frame_idx * render_frame_time_diff
        #             pos, dir_v = self.player_plane.move(delta_time=delta_time)
        #             self.game_render.render_map(pos, screen=self.screen)
        #
        #             # ----------------------------------------------------------------
        #             # 地面内容更新
        #             # 进行防空炮的更新
        #             for turret in self.game_data.team1_turrets + self.game_data.team2_turrets:
        #                 self.game_render.render_turret(turret=turret, delta_time=delta_time)
        #                 for bullet in turret.bullet_group:
        #                     self.game_render.render_bullet(bullet=bullet, delta_time=delta_time)
        #
        #             # 进行建筑的更新
        #             for building in self.game_data.team1_buildings + self.game_data.team2_buildings:
        #                 self.game_render.render_building(building=building)
        #
        #             # -----------------------------------------------------------------
        #             # 空中物体更新
        #             text = font.render(
        #                 'Engine temperature: {:.2f}, Speed: {:.2f}, position: [{:.2f}, {:.2f}]'.format(
        #                     self.player_plane.get_engine_temperature(), self.player_plane.velocity,
        #                     pos[0][0], pos[1][0]),
        #                 True, (0, 0, 0))
        #             # 将文本绘制到屏幕上
        #             self.screen.blit(text, (10, 10))
        #
        #             for plane in self.game_data.id_plane_mapping.values():
        #                 self.game_render.render_plane(plane=plane, team_id=plane.team_number,
        #                                               delta_time=delta_time)
        #                 # 渲染对应的子弹
        #                 for bullet in plane.bullet_group:
        #                     self.game_render.render_bullet(bullet=bullet, delta_time=delta_time)
        #             for explode in self.game_data.list_explodes:
        #                 self.game_render.render_explode(explode=explode)
        #
        #             # --------------- 玩家游戏提醒 -----------------
        #             # 如果主控飞机有效的话，可以绘制对应的瞄准图标和对应的检测到的目标飞机
        #             if self.player_plane is not None:
        #                 player_plane_vector = self.player_plane.get_direction_vector()
        #                 # 绘制准星
        #                 player_plane_vector = player_plane_vector * 250
        #                 cross_position = (
        #                     0.5 * self.game_window_size[0] + player_plane_vector[0][0],
        #                     0.5 * self.game_window_size[1] - player_plane_vector[1][0]
        #                 )
        #                 sprite_position = self.game_resources.cross_hair_sprite.get_rect(
        #                     center=cross_position
        #                 )
        #                 self.screen.blit(
        #                     self.game_resources.cross_hair_sprite, sprite_position)
        #
        #                 # 目标飞机检测并标记
        #                 if self.player_plane.detected_AAM_targets is not None:
        #                     self.game_render.render_box(self.player_plane.detected_AAM_targets)
        #
        #             # 然后在右上角显示小地图
        #             thumbnail_map_sprite_rect = self.game_resources.thumbnail_map_sprite.get_rect()
        #             thumbnail_map_render_left = self.game_window_size[0] - thumbnail_map_sprite_rect.width
        #             self.screen.blit(
        #                 self.game_resources.thumbnail_map_sprite,
        #                 (thumbnail_map_render_left, 0))
        #             scale = thumbnail_map_sprite_rect.width / self.map_size[0]
        #             # 然后根据小地图的位置来显示不同的飞机在缩略图中的位置
        #             for plane in self.game_data.team1_airplanes + self.game_data.team2_airplanes:
        #                 pos = plane.get_position()
        #                 if plane.team_number == 1:
        #                     pygame.draw.circle(
        #                         self.screen, (0, 255, 0),
        #                         (thumbnail_map_render_left + pos[0][0] * scale,
        #                          pos[1][0] * scale), 2)
        #                 else:
        #                     pygame.draw.circle(
        #                         self.screen, (255, 0, 0),
        #                         (thumbnail_map_render_left + pos[0][0] * scale,
        #                          pos[1][0] * scale), 2)
        #
        #             for turret in self.game_data.team1_turrets + self.game_data.team2_turrets:
        #                 pos = turret.get_position()
        #                 pygame.draw.circle(
        #                     self.screen, (0, 0, 255),
        #                     (thumbnail_map_render_left + pos[0][0] * scale,
        #                      pos[1][0] * scale), 2)
        #
        #             for building in self.game_data.team1_buildings + self.game_data.team2_buildings:
        #                 pos = building.get_position()
        #                 pygame.draw.circle(
        #                     self.screen, (0, 125, 125),
        #                     (thumbnail_map_render_left + pos[0][0] * scale,
        #                      pos[1][0] * scale), 2)
        #
        #             # 然后绘制框框
        #             pos = self.player_plane.get_position()
        #             pygame.draw.rect(
        #                 self.screen, (255, 0, 0),
        #                 (thumbnail_map_render_left + (pos[0][0] - 0.5 * self.game_window_size[0]) * scale,
        #                  (pos[1][0] - 0.5 * self.game_window_size[1]) * scale,
        #                  self.game_window_size[0] * scale,
        #                  self.game_window_size[1] * scale), 2)
        #
        #             self.render_frame_idx += 1
        #     else:
        #         # 清屏
        #         self.screen.fill((255, 255, 255))
        #         # 此处需要显示提示信息，等待另外的玩家进入游戏
        #         text = font.render(
        #             f"Waiting for {self.room_max_player_number} players. Currently in queue: {self.queue_current_players}...",
        #             True, (0, 0, 0))
        #         text_rect = text.get_rect(center=(self.game_window_size[0] // 2, self.game_window_size[1] // 2))
        #         self.screen.blit(text, text_rect.topleft)
        #
        #     pg.display.flip()  # 更新全部显示
        #     self.lock.release()
        #     self.clock_render.tick(self.fps_render)
        #     # delta_time = 1000 / self.fps_render

class MainGame:
    def __init__(self):
        """
        初始化函数，主要内容为初始化游戏资源，功能包括：
        1. 加载所有游戏资源并尽量保证游戏资源均没有问题
        2. 显示游戏主菜单并保证用户交互逻辑正确
        3. 增加游戏联机对战和本地对战模式和局域网对战模式，丰富游戏玩法
        4. 设置游戏的初始相关参数
        """
        # 遗传算法参数
        self.genetic_manager: GeneticAlgorithm = None
        # 游戏必要的参数配置
        self.local_game_server_thread = None
        self.local_game_server = None   # 如果跑本地的游戏，需要在本地设置一个服务器保证游戏大框架不发生变动
        # 网络连接参数
        self.server_port = 4444  # 服务器的端口信息
        self.server_address = '127.0.0.1'  # 服务器的 ip 地址
        self.player_id = 0  # 本地用户的 id
        self.game_name = "FightingAircraft"  # 游戏的名字
        self.game_window_size = 1080, 720  # 游戏窗口大小
        self.map_size = np.zeros((2,))  # 游戏的地图大小，应该是在游戏的 class 里面
        # 游戏运行的帧率和时钟控制
        self.fps_render = 60  # 渲染帧
        self.fps_physics = 30  # 逻辑帧
        self.fps_sync = 15  # 同步帧
        self.clock_render = pg.time.Clock()  # 渲染线程的时钟
        self.clock_sync = pg.time.Clock()
        self.clock_fixed_update = pg.time.Clock()
        # 游戏的资源加载
        self.game_resources = GameResources()
        # 游戏的渲染
        self.screen = None
        # 游戏运行日志
        self.is_use_logger = False
        self.logger_file_name = 'run_physic.log'
        self.logger = None

        # 关于游戏菜单
        self.game_menu: GameMenu = None
        self.is_game_ready = False  # 游戏是否开始
        self.exit_event = threading.Event()  # 游戏是否结束的退出事件
        self.lock = threading.RLock()  # 线程锁，保证渲染和物理运算的顺序
        self.thread_render = None  # 渲染线程
        self.thread_fixed_update = None  # 逻辑运算线程

        self.game_data = GameData()
        self.game = FightingAircraftGame()
        self.init_game()

        # self.game.init_game()

    def init_game(self):
        # # 创建 Tkinter 根窗口
        # root = tk.Tk()
        # root.withdraw()  # 隐藏根窗口

        self.genetic_manager = GeneticAlgorithm()

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
        self.game_menu = GameMenu(self.game_window_size)
        self.game_menu.menu.add_menu_item(MenuItem('Single Player', action=self.single_player_menu))
        self.game_menu.menu.add_menu_item(MenuItem('Multi Player', action=self.multi_player_menu))
        self.game_menu.menu.add_menu_item(MenuItem('Settings', action=self.settings_menu))
        self.game_menu.menu.add_menu_item(MenuItem('Exit Game', action=self.exit_menu))
        self.game_menu.update_menu_rect()

        # 和网络连接相关的内容
        config_data = json.load(open('config.json', 'r'))
        # 设置连接信息
        self.server_address = config_data.get('server_address', '172.21.174.158')
        self.server_port = config_data.get('server_port', 4444)

        # 设置渲染线程为子线程
        self.thread_render = threading.Thread(target=self.render, daemon=True)
        self.thread_fixed_update = threading.Thread(target=self.fixed_update, daemon=True)
        self.thread_render.start()
        self.thread_fixed_update.start()

        while True:
            # 游戏没开始的话就处理输入内容，防止程序假死
            self.handle_input()  # 输入管理
            self.clock_sync.tick(self.fps_physics)  # 获取物理帧的时间差，控制帧率

    def single_player_menu(self):
        """
        单个玩家的菜单的回调函数内容
        :return:
        """
        print('single_player_menu')
        # 在本地开启一个服务器
        self.local_game_server = FightingAircraftGameServer()
        self.local_game_server.room_max_player_number = 1
        # 启动服务器线程为主程序服务防止主程序卡死
        self.local_game_server_thread = threading.Thread(
            target=self.local_game_server.server_start, daemon=True)
        self.local_game_server_thread.start()
        # self.local_game_server.server_start()
        # 直接开始游戏
        self.game.init_game(self)
        self.is_game_ready = True

    def multi_player_menu(self):
        """
        多个玩家联机游戏的菜单回调函数
        :return:
        """
        print('multi_player_menu')

    def settings_menu(self):
        """
        菜单
        :return:
        """

    def exit_menu(self):
        """
        退出
        :return:
        """
        # 弹出退出确认消息框
        pyautogui.sleep(0.2)    # 可以防止程序退出过快，鼠标抬起事件干扰其他程序
        self.exit()

    def handle_input(self):
        # 处理输入
        for event in pg.event.get():  # 遍历所有事件
            if event.type == pg.QUIT:  # 如果单击关闭窗口，则退出
                self.exit()

            if self.is_game_ready is False:
                self.game_menu.handle_input()
            else:
                self.game.input_manager(event)

    def fixed_update(self):
        """
        运行主游戏逻辑：
        针对网络发送的运行数据，本地接收时间是不固定的，但是必须要用固定的时间间隔去运行这些不固定间隔的数据
        :return:
        """
        # delta_time = np.round(1000 / self.fps_physics, decimals=2)  # 物理运行的速度应该是固定的服务器的间隔，为了保证统一，保留两位小数

        # 此处只有物理运行，关于图形渲染是一个新的单独的线程
        while not self.exit_event.is_set():
            self.lock.acquire()
            if self.is_game_ready:
                self.game.fixed_update()

            self.lock.release()
            self.clock_fixed_update.tick(self.fps_physics)  # 获取时间差，控制帧率


    def render(self):
        print('render thread started. ')
        while not self.exit_event.is_set():
            self.lock.acquire()
            # 清屏
            self.screen.fill((255, 255, 255))
            if self.is_game_ready is False:
                self.game_menu.display_menu(self.screen)
            else:
                self.game.render()

            pg.display.flip()  # 更新全部显示
            self.lock.release()
            self.clock_render.tick(self.fps_render)
            # delta_time = 1000 / self.fps_render

    def exit(self):
        # self.client.close_socket()
        self.exit_event.set()
        self.thread_render.join()
        pg.quit()  # 退出pg
        sys.exit(0)


# @profile
def main():
    # game = FightingAircraftGame()
    # game.init_game()
    game = MainGame()


if __name__ == '__main__':
    main()
