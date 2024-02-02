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
        self.team1_airplanes: List[AirPlane] = []       # 飞机
        # self.team1_air_bullets: List[Bullet] = []       # 空中的子弹
        # self.team1_ground_bullets: List[Bullet] = []    # 地面的子弹
        self.team1_buildings: List[Building] = []       # 地面建筑
        self.team1_turrets: List[Turret] = []           # 地面可以发射攻击子弹的建筑
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

    def get_team_airplanes(self, team_number):
        if team_number == 1:
            return self.team1_airplanes
        elif team_number == 2:
            return self.team2_airplanes
        else:
            print('wrong team number')
            return None

    def get_team_buildings(self, team_number):
        if team_number == 1:
            return self.team1_buildings
        elif team_number == 2:
            return self.team2_buildings
        else:
            print('wrong team number')
            return None


    def get_team_turrets(self, team_number):
        if team_number == 1:
            return self.team1_turrets
        elif team_number == 2:
            return self.team2_turrets
        else:
            print('wrong team number')
            return None

    def reset_game_data(self):
        self.__init__()


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

    def get_plane(self, plane_name, team_number, game_data):
        param = self.airplane_info_map[plane_name]
        image_path, roll_mapping, pitch_mapping = self.load_plane_sprites(
            'objects/{}.xml'.format(plane_name))

        # 读取JSON文件
        with open('parameters.json', 'r') as file:
            data = json.load(file)
        plane_type = PlaneType(data['planes'][plane_name]['type'])
        if plane_type == PlaneType.Fighter:
            plane = FighterJet(team_number, game_data)
        elif plane_type == PlaneType.AttackAircraft:
            plane = AttackAircraft(team_number, game_data)
        elif plane_type == PlaneType.Bomber:
            plane = Bomber(team_number, game_data)
        else:
            plane = Bomber(team_number, game_data)

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
        plane.air_plane_sprites.primary_bullet_sprite = get_rect_sprite(
            self.get_bullet_sprite('bullet' + str(param['mainweapon'] + 1)))
        # 注意此处获取的 sprite 应该旋转 90 度
        plane.air_plane_sprites.secondary_bullet_sprite = get_rect_sprite(
            self.get_bullet_sprite('bullet' + str(param['secondweapon'])))

        explode_sub_textures, explode_sprite = self.get_explode_animation()
        plane.explode_sub_textures = explode_sub_textures
        plane.explode_sprite = explode_sprite
        # 刷新一下对应的 sprite, 防止出 bug
        plane.get_sprite()

        return plane

    def get_flak(self, list_turrets, list_explodes):
        new_flak = Flak(render_list=list_turrets, list_explodes=list_explodes)

        new_flak.set_turret_sprites(
            get_rect_sprite(self.get_turret_sprite('turret0')),
            get_rect_sprite(self.get_building_sprite('flak1', 'body')),
            get_rect_sprite(self.get_building_sprite('flak1', 'body'))
        )
        new_flak.set_bullet_sprite(
            get_rect_sprite(self.get_bullet_sprite('bullet2')))
        explode_sub_textures, explode_sprite = self.get_explode_animation('explode05')
        new_flak.explode_sub_textures = explode_sub_textures
        new_flak.explode_sprite = explode_sprite

        return new_flak



