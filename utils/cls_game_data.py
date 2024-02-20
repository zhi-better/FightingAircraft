import base64
import struct
import zlib

import numpy as np
import pygame
import json
import logging
import os
from enum import Enum
import xml.etree.ElementTree as ET
from typing import Dict, List
from utils.cls_airplane import *
from utils.cls_building import *

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


class PlaneType(Enum):
    Simple = 0                      # 简单飞机
    Fighter = 1                     # 战斗机（空对空）
    AttackAircraft = 2              # 攻击机（空对地）
    Bomber = 3                      # 轰炸机（对地攻击）
    Reconnaissance = 4              # 侦察机（侦察视野）
    MultiRoleCombatAircraft = 5     # 多用途飞机

class CommandType(Enum):
    cmd_none = 0
    cmd_login = 1
    cmd_login_resp = 2
    cmd_matching_successful = 3
    cmd_player_action = 4
    cmd_frame_update = 5
    cmd_matching_state_change = 6
    cmd_game_over = 7

class PlaneName(Enum):
    Ar234 = 'Ar234'
    B17 = 'B17'
    B24 = 'B24'
    B25 = 'B25'
    Ba349 = 'Ba349'
    Bf109 = 'Bf109'
    Bf110 = 'Bf110'
    Bv138 = 'Bv138'
    C43 = 'C43'
    Cg4a = 'Cg4a'
    Do17 = 'Do17'
    Do24 = 'Do24'
    Do335 = 'Do335'
    F3F = 'F3F'
    F4F = 'F4F'
    F4U = 'F4U'
    F80 = 'F80'
    fokd = 'fokd'
    Fw189 = 'Fw189'
    Fw190 = 'Fw190'
    He111 = 'He111'
    He115 = 'He115'
    He162 = 'He162'
    Ho229 = 'Ho229'
    Hs123 = 'Hs123'
    Ju52 = 'Ju52'
    Ju87 = 'Ju87'
    Ju88 = 'Ju88'
    Ju188 = 'Ju188'
    lippisch = 'lippisch'
    Me163 = 'Me163'
    Me262 = 'Me262'
    P38 = 'P38'
    P39 = 'P39'
    P40 = 'P40'
    P47 = 'P47'
    P51 = 'P51'
    P61 = 'P61'
    SBD = 'SBD'


class FlakName(Enum):
    flak1 = 'flak1'
    flak2 = 'flak2'


class GameResources:
    def __init__(self):
        self.cross_hair_image = None  # 瞄准准星
        self.airplane_info_map = {}  #
        self.maps_map = {}
        self.explode_sub_textures = {}
        self.explode_sprite = None
        self.temporary_sub_textures = {}
        self.temporary_sprite = None
        self.thumbnail_map_sprite = None
        self.cross_hair_sprite = None

        self.load_all()

    def load_all(self):
        self.load_explode()
        self.load_temporary()
        self.load_all_plane_parameters()
        self.check_all_maps()

        original_cross_hair_sprite = pygame.image.load('guideDest.png')
        # 进行2倍缩放
        scale = 0.1
        self.cross_hair_sprite = pygame.transform.scale(
            original_cross_hair_sprite,
            (original_cross_hair_sprite.get_width() * scale, original_cross_hair_sprite.get_height() * scale))

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

        self.temporary_sprite = pygame.image.load('temporary.png')

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
        self.explode_sprite = pygame.image.load('explode.png')

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

    def check_all_maps(self):
        # 加载所有的地图文件保存对应的名称以及对应的文件名
        num_xml_file = 0
        for file in os.listdir('map'):
            if file.endswith(".xml"):
                # 判断是否有对应的缩略图，如果没有的话跳过
                file_name = os.path.splitext(file)[0]
                if os.path.exists('map/' + file_name + '.png'):
                    self.maps_map[num_xml_file] = os.path.join('map', file)
                    num_xml_file += 1

        # ----------------------------------------------
        # # 首先加载都有哪些地图
        # num_xml_file = 0
        # for file in os.listdir('map'):
        #     if file.endswith(".xml"):
        #         self.maps_map[num_xml_file] = os.path.join('map', file)
        #         num_xml_file += 1

    def get_map(self, map_index=0):
        """
        1. 获取到对应的地图的图像和缩略图
        2. 获取到对应地图解压后的地图数据格式
        :param map_index:
        :return:
        """
        if len(self.maps_map) <= map_index:
            print('not a valid map index. ')

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

        # 接下来读取并计算地图的相关数据信息
        game_map_info = GameMap(file_name)

        return self.maps_map[map_index], self.thumbnail_map_sprite, game_map_info

    def get_bullet_sprite(self, bullet_key='bullet1'):
        """
        加载子弹的精灵，参数为子弹的键
        :param bullet_key: bullet1 - bullet6, bomb1 - bomb5
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
        return (self.explode_sub_textures[explode_key], self.explode_sprite)

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

        # 返回图片路径和映射字典，读取对应的数据
        sprites = pygame.image.load('objects/' + image_path)

        return sprites, roll_mapping, pitch_mapping

    def get_plane(self, plane_name):
        """
        仅仅获取飞机的属性信息以及对应的图片资源和共有的部分，不在此处直接实例化飞机
        飞机待设定参数：
        1. 飞机自身属性，俯仰和滚转渲染的区域及图片
        :param plane_name:
        :param team_number:
        :param game_data:
        :return:
        """
        param = self.airplane_info_map[plane_name]
        sprites, roll_mapping, pitch_mapping = self.load_plane_sprites(
            'objects/{}.xml'.format(plane_name))

        # 读取JSON文件
        with open('parameters.json', 'r') as file:
            data = json.load(file)

        plane_type = PlaneType(data['planes'][plane_name]['type'])
        # if plane_type == PlaneType.Fighter:
        #     plane = FighterJet(team_number, game_data)
        # elif plane_type == PlaneType.AttackAircraft:
        #     plane = AttackAircraft(team_number, game_data)
        # elif plane_type == PlaneType.Bomber:
        #     plane = Bomber(team_number, game_data)
        # else:
        #     plane = Bomber(team_number, game_data)
        #
        # plane.set_speed(param['speed'])
        # plane.angular_speed = param['turnspeed']
        # plane.health_points = param['lifevalue']
        # params = plane.get_air_plane_params()
        # params.name = plane_name
        # params.primary_weapon_reload_time = 0.2
        # params.secondary_weapon_reload_time = 0.1
        # params.plane_width = roll_mapping[0]['width']
        # params.plane_height = roll_mapping[0]['height']
        # plane.set_air_plane_params(params)
        # # plane.air_plane_params.primary_weapon_reload_time = 0
        # # plane.air_plane_params.secondary_weapon_reload_time = 0
        # plane.load_sprite('objects/{}.png'.format(plane_name))
        # plane.air_plane_sprites.roll_mapping = roll_mapping
        # plane.air_plane_sprites.pitch_mapping = pitch_mapping
        # # 设置主武器和副武器的贴图资源
        # plane.air_plane_sprites.primary_bullet_sprite = get_rect_sprite(
        #     self.get_bullet_sprite('bomb' + str(param['mainweapon'] + 1)))
        # # 注意此处获取的 sprite 应该旋转 90 度
        # plane.air_plane_sprites.secondary_bullet_sprite = get_rect_sprite(
        #     self.get_bullet_sprite('bullet' + str(param['secondweapon'])))
        #
        # plane.explode_sub_textures = explode_sub_textures
        # plane.explode_sprite = explode_sprite
        # # 刷新一下对应的 sprite, 防止出 bug
        # plane.get_sprite()

        # explode_sub_textures, explode_sprite = self.get_explode_animation()
        explode_animation = self.get_explode_animation()

        return plane_type, param, sprites, roll_mapping, pitch_mapping, explode_animation

    def get_flak(self, team_number, game_data):
        new_flak = Flak(team_number, game_data)

        new_flak.set_turret_sprites(
            get_rect_sprite(self.get_turret_sprite('turret0')),
            get_rect_sprite(self.get_building_sprite('flak1', 'body')),
            get_rect_sprite(self.get_building_sprite('flak1', 'body'))
        )
        new_flak.set_bullet_sprite(
            get_rect_sprite(self.get_bullet_sprite('bullet2')))
        # explode_sub_textures, explode_sprite = self.get_explode_animation('explode05')
        explode_animation = self.get_explode_animation('explode05')
        new_flak.explode_sub_textures = explode_animation[0]
        new_flak.explode_sprite = explode_animation[1]

        return new_flak

class GameMap:
    def __init__(self, xml_file_name):
        self.width = 0
        self.height = 0
        self.tile_width = 0
        self.tile_height = 0
        self.tile_ids = []
        self.template_image = None
        self.map_size = np.zeros((2,))

        self.load_map_xml(xml_file_name)

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
        self.template_image = pygame.image.load(self.image_source)
        # self.x_load_block_count = int(np.ceil(self.game_window_size[0] * 0.5 / self.tile_width)) + 1
        # self.y_load_block_count = int(np.ceil(self.game_window_size[1] * 0.5 / self.tile_height)) + 1

        self.map_size = np.array([self.width * self.tile_width, self.height * self.tile_height])


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
        # 这个内容不能删，需要在最后游戏解算用到
        # new_map = {}
        # for key, plane in self.id_plane_mapping.items():
        #     if plane != airplane:
        #         new_map[key] = plane
        # self.id_plane_mapping = new_map

        team_airplanes = self.get_team_airplanes(airplane.team_number)
        # 有可能同时许多子弹把它杀了
        if airplane in team_airplanes:
            team_airplanes.remove(airplane)
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
