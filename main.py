import base64
import json
import logging
import os
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

from utils.SocketTcpTools import *
from utils.cls_airplane import *
from utils.cls_building import *
from utils.cls_explode import Explode
from utils.cls_game_data import *
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
                server_id = data['planes'][0]['player_id']
                data = {
                    "command": 3,
                    "sync_time_stamp": 0,
                    "map_id": 17,
                    "planes": [
                        {"player_id": server_id, "position_x": 2000, "position_y": 2000, "plane_name": "Bf110"},
                        {"player_id": 2, "position_x": 2200, "position_y": 2000, "plane_name": "Bf110"}
                    ]
                }
                self.player_id = server_id
                print('matching successfully. ')
                self.lock.acquire()
                # 加载地图
                self.game_render.game_window_size = np.array(self.game_window_size).reshape((2,))
                # map_xml_name, _ = self.game_resources.get_map(data['map_id'])
                map_xml_name, _ = self.game_resources.get_map(37)
                self.game_render.load_map_xml(map_xml_name)
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
                for plane_info in planes:
                    new_plane = self.game_resources.get_plane(
                        plane_info['plane_name'], plane_info['player_id'], self.game_data)
                    new_plane.set_map_size(self.map_size)
                    new_plane.set_position(np.array([plane_info['position_x'], plane_info['position_y']]))
                    new_plane.get_air_plane_params().id = plane_info['player_id']
                    self.game_data.id_plane_mapping[plane_info['player_id']] = new_plane
                    if plane_info['player_id'] == self.player_id:
                        # 加载飞机
                        self.player_plane = new_plane
                        self.player_plane.team_number = 1
                        self.game_data.team1_airplanes.append(new_plane)
                        self.game_data.team1_air_collision_group.add(new_plane)
                    else:
                        new_plane.team_number = 2
                        self.game_data.team2_airplanes.append(new_plane)
                        self.game_data.team2_air_collision_group.add(new_plane)

                # ----------------------------------------------------------------
                # 防空炮构造
                # new_flak = self.game_resources.get_flak(
                #     self.game_data.team2_turrets, self.game_data.list_explodes)
                # new_flak.set_map_size(self.map_size)
                # new_flak.set_position(np.array([2200, 2200]))
                # new_flak.target_obj = self.player_plane
                # new_flak.team_number = 2
                # new_flak.all_planes = self.game_data.id_plane_mapping.values()
                # self.game_data.team2_turrets.append(new_flak)
                # self.game_data.team2_ground_collision_group.add(new_flak)
                # # ---------------------------------------------------------------
                # # 房屋构建
                # new_building = Building(
                #     self.game_data.team2_buildings, self.game_data.list_explodes)
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
                # new_building.team_number = 2
                # self.game_data.team2_buildings.append(new_building)
                # self.game_data.team2_ground_collision_group.add(new_building)

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
        for key, value in self.game_data.id_plane_mapping.items():
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
                plane.bullet_group, self.game_data.team2_air_collision_group, False, False)
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
                            self.game_data.team2_air_collision_group.remove(sprite)
        elif plane.team_number == 2:
            crashed = pygame.sprite.groupcollide(
                plane.bullet_group, self.game_data.team1_air_collision_group, False, False)
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
                            self.game_data.team1_air_collision_group.remove(sprite)
        else:
            print('unknown team_number: {}'.format(plane.team_number))
        # return crashed

    def update_plane_physics(self, delta_time):
        """
        更新飞机的物理状态
        """
        # ----------------------------------------------------------------
        # 飞机飞行状态的更新
        for plane in self.game_data.id_plane_mapping.values():
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
                    for plane in self.game_data.id_plane_mapping.values():
                        self.game_render.render_plane(plane=plane, team_id=plane.team_number,
                                                      delta_time=delta_time)
                        # print('\r obj count: {}'.format(len(self.player_plane.bullet_list)), end='')
                        for bullet in plane.bullet_group:
                            self.game_render.render_bullet(bullet=bullet, delta_time=delta_time)

                    for explode in self.game_data.list_explodes:
                        self.game_render.render_explode(explode=explode)

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
                    for plane in self.game_data.id_plane_mapping.values():
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

            pg.display.flip()  # 更新全部显示
            self.lock.release()
            self.clock_render.tick(self.fps_render)
            # delta_time = 1000 / self.fps_render


# @profile
def main():
    game = FightingAircraftGame()
    game.init_game()


if __name__ == '__main__':
    main()
