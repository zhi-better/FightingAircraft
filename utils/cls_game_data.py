import json
import os
from enum import Enum
import xml.etree.ElementTree as ET
from typing import Dict, List
import pygame
from utils.cls_airplane import *
from utils.cls_building import *


class CommandType(Enum):
    cmd_none = 0
    cmd_login = 1
    cmd_login_resp = 2
    cmd_matching_successful = 3
    cmd_player_action = 4
    cmd_frame_update = 5
    cmd_matching_state_change = 6


class GameData:
    def __init__(self):
        """
        主要内容为游戏的总数据，便于不同飞机内部进行访问
        """
        # 关于游戏元素的分组
        self.team1_airplanes: List[AirPlane] = []  # 飞机
        # self.team1_air_bullets: List[Bullet] = []       # 空中的子弹
        # self.team1_ground_bullets: List[Bullet] = []    # 地面的子弹
        self.team1_buildings: List[Building] = []  # 地面建筑
        self.team1_turrets: List[Turret] = []  # 地面可以发射攻击子弹的建筑
        self.team2_airplanes: List[AirPlane] = []
        # self.team2_air_bullets: List[Bullet] = []
        # self.team2_ground_bullets: List[Bullet] = []
        self.team2_buildings: List[Building] = []
        self.team2_turrets: List[Turret] = []
        # 关于碰撞的相关分组
        # 因为部分建筑被摧毁后还有剩余的渲染任务，还在游戏元素分组，但是已经不是碰撞分组了，所以单列出来
        self.team1_air_collision_group = pygame.sprite.Group()
        self.team1_ground_collision_group = pygame.sprite.Group()
        self.team2_air_collision_group = pygame.sprite.Group()
        self.team2_ground_collision_group = pygame.sprite.Group()
        # 为了便于更新内容，创建了三个组，分别是：所有飞机，敌方飞机，我方飞机
        self.id_plane_mapping: Dict[int, AirPlane] = {}
        # 渲染变量，爆炸无队伍区分
        self.list_explodes = []

    def add_team_airplanes(self, team_number, airplane):
        airplane.team_number = team_number
        self.get_team_airplanes(team_number).append(airplane)
        self.get_air_obj_collision_group(team_number).add(airplane)

    def remove_team_airplanes(self, airplane):
        new_map = {}
        for key, plane in self.id_plane_mapping.items():
            if plane != airplane:
                new_map[key] = plane
        self.id_plane_mapping = new_map
        self.get_team_airplanes(airplane.team_number).remove(airplane)
        self.get_air_obj_collision_group(airplane.team_number).remove(airplane)

    def get_team_airplanes(self, team_number):
        if team_number == 1:
            return self.team1_airplanes
        elif team_number == 2:
            return self.team2_airplanes
        else:
            print('wrong team number')
            return None

    def add_team_buildings(self, team_number, building):
        building.team_number = team_number
        self.get_team_buildings(team_number).append(building)
        self.get_ground_obj_collision_group(team_number).add(building)

    def remove_team_buildings(self, building):
        # 有摧毁状态，只能移除碰撞检测
        # self.get_team_buildings(building.team_number).remove(building)
        self.get_ground_obj_collision_group(building.team_number).remove(building)

    def get_team_buildings(self, team_number):
        if team_number == 1:
            return self.team1_buildings
        elif team_number == 2:
            return self.team2_buildings
        else:
            print('wrong team number')
            return None

    def add_team_turrets(self, team_number, turret):
        turret.team_number = team_number
        self.get_team_turrets(team_number).append(turret)
        self.get_ground_obj_collision_group(team_number).add(turret)

    def remove_team_turrets(self, turret):
        # self.get_team_turrets(turret.team_number).remove(turret)
        self.get_ground_obj_collision_group(turret.team_number).remove(turret)

    def get_team_turrets(self, team_number):
        if team_number == 1:
            return self.team1_turrets
        elif team_number == 2:
            return self.team2_turrets
        else:
            print('wrong team number')
            return None

    def get_ground_obj_collision_group(self, team_number):
        """
        设置地面碰撞的 group
        :param team_number:
        :param obj:
        :return:
        """
        if team_number == 1:
            return self.team1_ground_collision_group
        elif team_number == 2:
            return self.team2_ground_collision_group
        else:
            print('wrong team number! ')

    def get_air_obj_collision_group(self, team_number):
        """
        设置空中碰撞的 group
        :param team_number:
        :param obj:
        :return:
        """
        if team_number == 1:
            return self.team1_air_collision_group
        elif team_number == 2:
            return self.team2_air_collision_group
        else:
            print('wrong team number! ')

    def get_air_crashed_group(self, bullet_group, team_number):
        """
        计算对应的碰撞分组
        :param bullet_group:
        :param team_number:
        :return:
        """
        crashed = {}
        if team_number == 1:
            crashed = pygame.sprite.groupcollide(
                bullet_group, self.team2_air_collision_group, False, False)
        elif team_number == 2:
            crashed = pygame.sprite.groupcollide(
                bullet_group, self.team1_air_collision_group, False, False)
        else:
            print('wrong team number! ')

        return crashed

    def get_ground_crashed_group(self, bullet_group, team_number):
        """
        计算对应的碰撞分组
        :param bullet_group:
        :param team_number:
        :return:
        """
        crashed = {}
        if team_number == 1:
            crashed = pygame.sprite.groupcollide(
                bullet_group, self.team2_ground_collision_group, False, False)
        elif team_number == 2:
            crashed = pygame.sprite.groupcollide(
                bullet_group, self.team1_ground_collision_group, False, False)
        else:
            print('wrong team number! ')

        return crashed

    def reset_game_data(self):
        self.__init__()
