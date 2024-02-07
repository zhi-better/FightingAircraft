from enum import Enum, IntFlag

import numpy as np
import pygame
from overrides import overrides

from utils.cls_building import Building
from utils.cls_bullets import *
from utils.cls_dqn_agent import AIAircraftNet
from utils.cls_explode import Explode
from utils.cls_obj import *
from abc import ABCMeta, abstractmethod


class AttitudeType(Enum):
    NoneAttitude = 0
    RollAttitude = 1
    PitchAttitude = 2


class PlaneType(Enum):
    Simple = 0                      # 简单飞机
    Fighter = 1                     # 战斗机（空对空）
    AttackAircraft = 2              # 攻击机（空对地）
    Bomber = 3                      # 轰炸机（对地攻击）
    Reconnaissance = 4              # 侦察机（侦察视野）
    MultiRoleCombatAircraft = 5     # 多用途飞机


class InputState(IntFlag):
    NoInput = 0b0000000000
    SharpTurnLeft = 0b0000010000
    SharpTurnRight = 0b0000100000
    Roll = 0b0001000000
    Pitch = 0b0010000000
    SpeedUp = 0b0100000000
    SlowDown = 0b1000000000
    TurnLeft = 0b0000000100
    TurnRight = 0b0000001000
    PrimaryWeaponAttack = 0b0000000010
    SecondaryWeaponAttack = 0b0000000001


class WeaponType(Enum):
    Weapon_None = 0     # 无武装飞机
    MG_762_4x = 1       # 7.62mm机枪*4
    MG_762_2x = 2       # 7.62mm机枪*2
    MG_127_4x = 3       # 12.7mm机枪*4
    MG_127_2x = 4       # 12.7mm机枪*2
    AC_20_2x = 5        # 20mm机炮*2
    AC_20_4x = 6        # 20mm机炮*4
    AC_37_1x = 7        # 37mm机炮*1
    AC_37_2x = 8        # 37mm机炮*2
    AC_40_1x = 9        # 40mm机炮*1
    AC_40_2x = 10       # 40mm机炮*2
    RKT_2x = 11         # 火箭弹*2
    AAM_2x = 12         # 追踪导弹*2
    MC_100_x = 13       # MC100通用炸弹
    MC500_x = 14        # MC500通用炸弹
    SD_2_x = 15         # SD2穿甲炸弹
    SD_4_x = 16         # SD4穿甲炸弹
    TOR_2x = 15         # 鱼雷*2

def detect_airplane_target_obj(airplane_obj, target_objs, distance_threshold, angle_threshold):
    """
    根据自身位置和物体的位置来寻找到自身的攻击目标
    :param objs:
    :return:
    """
    most_valuable_target = None
    min_cross = np.sin(np.deg2rad(angle_threshold))
    for target_obj in target_objs:
        if target_obj.team_number != airplane_obj.team_number:
            lead_positions = target_obj.get_position() - airplane_obj.get_position()
            distances = np.linalg.norm(lead_positions)
            norm_target_vec = lead_positions / distances
            if distances < distance_threshold:
                # 判断角度是否达到了要求
                cross_value = np.abs(
                    np.cross(norm_target_vec.T,
                             (airplane_obj.get_direction_vector() * np.array([1, -1]).reshape((2, 1))).T))
                if cross_value < min_cross:
                    min_cross = cross_value
                    most_valuable_target = target_obj

    return most_valuable_target


class AirPlaneSprites:
    def __init__(self):
        self.ammunition_list = []  # 飞机的开火动画配置 list
        self.ammunition_sprite = None  # 飞机开火精灵模板
        self.primary_bullet_sprite = None  # 飞机主武器子弹的精灵
        self.secondary_bullet_sprite = None  # 飞机副武器子弹的精灵
        self.roll_mapping = {}
        self.pitch_mapping = {}


class AirPlaneParams:
    def __init__(self):
        self.id = 0
        self.name = 'AirPlane'
        # self.health_points = 1000  # 生命值
        self.angular_speed = 0.8  # 转向速度
        self.speed = 0  # 正常运行速度
        self.max_speed = 0  # 最大速度
        self.min_speed = 3  # 最小速度
        self.engine_heat_rate = 0  # 引擎温度升高速率
        self.overheat_duration = 60  # 引擎过热保护时间
        self.plane_width = 0
        self.plane_height = 0
        self.primary_weapon_reload_time = 0.5
        self.secondary_weapon_reload_time = 0.5


class AirPlane(DynamicObject, Building):
    def __init__(self, team_number, game_data):
        self.detected_AAM_targets = None
        DynamicObject.__init__(self, team_number, game_data)
        Building.__init__(self, team_number, game_data)
        self.plane_type = PlaneType.Simple
        self.image_template = None
        self.air_plane_sprites = AirPlaneSprites()
        self._air_plane_params = AirPlaneParams()
        self._velocity_modulation_factor = 0
        self._engine_temperature = 0
        self.heat_counter = 60          # 表示引擎过热后经过多久后会开始自动降温
        self.roll_attitude = 0.0
        self.pitch_attitude = 0.0
        self.input_state = InputState.NoInput
        self.primary_weapon_reload_counter = 0
        self.secondary_weapon_reload_counter = 0
        self.bullet_group = pygame.sprite.Group()
        self.timer_counter = 0
        self.switch_direction = False
        self.agent_network = AIAircraftNet()

    def get_plane_states(self, planes_list):
        """
        获取此时 planes 相对于自身的位置参数，并将其整理为一个对应的 ndarray
        :return:
        """
        states = []
        vec_self = self.get_direction_vector()
        for plane in planes_list:
            pos = plane.get_position() - self.get_position()
            vec_1 = plane.get_direction_vector()
            # 计算两个向量的夹角
            cosine_angle = np.dot(vec_self.T, vec_1) / (np.linalg.norm(vec_self) * np.linalg.norm(vec_1))
            angle = np.arccos(cosine_angle)[0]
            # 以向量夹角构造一个新的向量
            new_vector = np.array([np.cos(angle), np.sin(angle)])
            velocity = plane.velocity
            angular_velocity = plane.angular_velocity
            states.append(
                np.hstack((pos.reshape((-1)), new_vector.reshape((-1)),
                           np.array([velocity]), np.array([angular_velocity]),
                           np.array([self._engine_temperature]))))

        return np.array(states)

    def take_damage(self, damage):
        self.durability -= damage
        if self.durability <= 0:
            self.game_data.remove_team_airplanes(self)
            self.on_death()
            return True
        else:
            return False

    def load_sprite(self, img_file_name):
        self.image_template = pygame.image.load(img_file_name)

        return self.image_template

    def get_air_plane_params(self):
        return self._air_plane_params

    def set_air_plane_params(self, params):
        self._air_plane_params = params

    def get_engine_temperature(self):
        return self._engine_temperature

    @overrides
    def get_sprite(self):
        """
        此处一定要实现逻辑和渲染分离，不然多方同步的时候数据会出现问题
        :return:
        """
        # 水平回归原位是优先级较高的操作
        if self.roll_attitude != 0:
            rect_dic = self.air_plane_sprites.roll_mapping[int(self.roll_attitude)]
        elif self.pitch_attitude != 0:
            rect_dic = self.air_plane_sprites.pitch_mapping[int(self.pitch_attitude)]
        else:
            rect_dic = self.air_plane_sprites.roll_mapping[int(0)]

        self.image = get_rect_sprite((rect_dic, self.image_template))
        self.image = pygame.transform.rotate(
            self.image, vector_2_angle(self.get_direction_vector()))
        # 在飞行姿势大于30度的时候不可被击中
        if 0 <= self.pitch_attitude <= 3 or 33 <= self.pitch_attitude <= 36:
            rect = self.image.get_rect()
            self.rect.width = rect.width
            self.rect.height = rect.height
            self.mask = pygame.mask.from_surface(self.image)
        else:
            # 此处设置为 1 主要为了和没设置时的 0 区分
            self.rect.width = 1
            self.rect.height = 1
        return self.image


    def set_speed(self, speed):
        """
        设置飞机的速度参数，实际速度为 velocity
        :param speed:
        :return:
        """
        self.speed = speed
        self.velocity = speed

    def update_roll_attitude(self, target_roll_attitude):
        if self.timer_counter % 2 == 0 and self.pitch_attitude == 0:
            self.timer_counter = 0
            if np.abs(self.roll_attitude - target_roll_attitude) <= 1:
                self.roll_attitude = target_roll_attitude
            else:
                # 判断从哪个方向归位
                tmp = target_roll_attitude - self.roll_attitude
                # 问题解决
                if tmp > 18 or -18 < tmp < 0:
                    self.roll_attitude -= 1
                else:
                    self.roll_attitude += 1

            if self.roll_attitude >= 36:
                self.roll_attitude -= 36
            elif self.roll_attitude < 0:
                self.roll_attitude += 36

    def update_pitch_attitude(self, target_pitch_attitude):
        """
        更新对应的pitch姿态
        :param target_pitch_attitude:
        :return:
        """
        '''
        此处的逻辑内容：
        1. 当pitch上拉的时候整体的速度会降低，当pitch下拉的时候整体的速度会增加
        2. 当pitch接近9的时候应该直接以9进行旋转，此时的旋转速度由于角度不同应该要小于急转时刻的转弯半径
        '''
        if self.timer_counter % 3 == 0 and self.roll_attitude == 0:
            self.timer_counter = 0
            if self.switch_direction:
                target_pitch_attitude = 18
            if np.abs(self.pitch_attitude - target_pitch_attitude) <= 1:
                self.pitch_attitude = target_pitch_attitude
            else:
                # 判断从哪个方向归位
                tmp = target_pitch_attitude - self.pitch_attitude
                # 问题解决
                if tmp > 18 or -18 < tmp < 0:
                    self.pitch_attitude -= 1
                else:
                    self.pitch_attitude += 1
            # 更新对应的内容到合理范围内
            if self.pitch_attitude >= 36:
                self.pitch_attitude -= 36
            elif self.pitch_attitude < 0:
                self.pitch_attitude += 36
            # 控制战机转向
            if self.pitch_attitude == 9:
                self.switch_direction = True
            elif self.pitch_attitude == 18:
                self.switch_direction = False
                if bool(self.input_state & InputState.Pitch) is False:
                    self.set_direction_vector(self.get_direction_vector() * -1)
                    self.roll_attitude = 18
                    self.pitch_attitude = 0

    def fixed_update(self, delta_time):
        """
        飞机逻辑数据的更新
        :param delta_time:
        :return:
        """
        self.timer_counter += 1
        '''
        新的横滚逻辑：
        
        '''
        # 首先重置对应的转向速度
        self.angular_velocity = 0
        if self.input_state & InputState.Roll:
            self.update_roll_attitude(target_roll_attitude=self.roll_attitude + 1)
        elif self.input_state & InputState.TurnLeft:
            self.update_roll_attitude(target_roll_attitude=3)
            self.angular_velocity = self._air_plane_params.angular_speed
        elif self.input_state & InputState.TurnRight:
            self.update_roll_attitude(target_roll_attitude=33)
            self.angular_velocity = -self._air_plane_params.angular_speed
        elif self.input_state & InputState.SharpTurnLeft:
            if self._engine_temperature >= 100:
                self.heat_counter = 0
                self.update_roll_attitude(target_roll_attitude=3)
                self.angular_velocity = self._air_plane_params.angular_speed
            else:
                self._air_plane_params.engine_heat_rate += 0.5
                self.update_roll_attitude(target_roll_attitude=8)
                self.angular_velocity = self._air_plane_params.angular_speed * 2
        elif self.input_state & InputState.SharpTurnRight:
            if self._engine_temperature >= 100:
                self.heat_counter = 0
                self.update_roll_attitude(target_roll_attitude=33)
                self.angular_velocity = -self._air_plane_params.angular_speed
            else:
                self._air_plane_params.engine_heat_rate += 0.5
                self.update_roll_attitude(target_roll_attitude=28)
                self.angular_velocity = self._air_plane_params.angular_speed * -2
        else:
            self.update_roll_attitude(target_roll_attitude=0)
        # 根据目前的姿态来重新调整对应的转向速度，优化控制手感
        if self.angular_velocity != 0:
            # 此处设置一个原则，如果是在翻转情境下无法左右转向，否则不太合理
            if 0 < self.roll_attitude <= 9:
                self.angular_velocity = self.roll_attitude / 9 * self.angular_speed
            elif 27 <= self.roll_attitude < 36:
                self.angular_velocity = (self.roll_attitude - 36) / 9 * self.angular_speed
            else:
                self.angular_velocity = 0
        # print(f'\rself.angular_velocity: {self.angular_velocity}, self.angular_speed: {self.angular_speed}', end='')

        # ---------------------------------------------
        # 俯仰
        if self.input_state & InputState.Pitch:
            if self._engine_temperature < 100:
                # 俯仰
                self.update_pitch_attitude(target_pitch_attitude=self.pitch_attitude + 1)
                self._air_plane_params.engine_heat_rate += 0.5
            else:
                self.heat_counter = 0
        else:
            self.update_pitch_attitude(target_pitch_attitude=0)

        # ---------------------------------------------
        # 加减速
        if self.input_state & InputState.SpeedUp:
            if self._engine_temperature < 100:
                self._air_plane_params.engine_heat_rate += 0.3
                # 速度插值，为了恢复常规的运行速度
                self.velocity = np.minimum(self.velocity + 0.07, self.speed * 1.5)
            else:
                # 速度插值，为了恢复常规的运行速度
                self.velocity += np.sign(self.speed - self.velocity) * 0.03
                if np.abs(self.velocity - self.speed) < 0.2:
                    self.velocity = self.speed
                self.heat_counter = 0
        elif self.input_state & InputState.SlowDown:
            self.velocity = np.maximum(self.velocity - 0.3, self.speed * 0.7)
        else:
            # 速度插值，为了恢复常规的运行速度
            self.velocity += np.sign(self.speed - self.velocity) * 0.03
            if np.abs(self.velocity - self.speed) < 0.2:
                self.velocity = self.speed

        # ---------------------------------------------
        # 发动机温度
        if self._air_plane_params.engine_heat_rate == 0:
            # 如果发动机温度过高，持续一段时间后再降温
            if self._engine_temperature >= 100:
                if self.heat_counter >= self._air_plane_params.overheat_duration:
                    self._air_plane_params.engine_heat_rate = -0.3
            else:
                self._air_plane_params.engine_heat_rate = -0.3
        # self._engine_temperature = np.minimum(
        #     100, np.maximum(0, self._engine_temperature + self.air_plane_params.engine_heat_rate * delta_time * 0))
        self._engine_temperature = np.minimum(
            100, np.maximum(0, self._engine_temperature + self._air_plane_params.engine_heat_rate * delta_time * 0.01))
        self.heat_counter += 1
        self._air_plane_params.engine_heat_rate = 0

        # ---------------------------------------------
        # 主武器攻击
        if self.input_state & InputState.PrimaryWeaponAttack and self.pitch_attitude == 0:
            if self.primary_weapon_reload_counter <= 0:
                self.primary_weapon_attack()
                self.primary_weapon_reload_counter += self._air_plane_params.primary_weapon_reload_time
            else:
                self.primary_weapon_reload_counter -= delta_time * 0.001
        else:
            if self.primary_weapon_reload_counter <= 0:
                self.primary_weapon_reload_counter = 0
            else:
                self.primary_weapon_reload_counter -= delta_time * 0.001
        # ---------------------------------------------
        # 副武器攻击
        if self.input_state & InputState.SecondaryWeaponAttack and self.pitch_attitude == 0:
            if self.secondary_weapon_reload_counter <= 0:
                self.secondary_weapon_attack()
                self.secondary_weapon_reload_counter += self._air_plane_params.secondary_weapon_reload_time
            else:
                self.secondary_weapon_reload_counter -= delta_time * 0.001
        else:
            if self.secondary_weapon_reload_counter <= 0:
                self.secondary_weapon_reload_counter = 0
            else:
                self.secondary_weapon_reload_counter -= delta_time * 0.001

        # 获取到敌人的飞机坐标
        target_team_number = 0
        if self.team_number == 1:
            target_team_number = 2
        elif self.team_number == 2:
            target_team_number = 1
        else:
            print('wrong team number')
        self.detected_AAM_targets = detect_airplane_target_obj(
            self, self.game_data.get_team_airplanes(target_team_number),
            800, 30)

        # --------------------------------------------------------------------
        # 重置飞行状态
        self.input_state = InputState.NoInput
        # 需要来一个偷梁换柱
        real_velocity = self.velocity
        self.velocity *= np.cos(np.radians(self.pitch_attitude * 10))
        pos, direction_vector = self.move(delta_time=delta_time)
        self.velocity = real_velocity
        # 物理更新直接改变数值内容
        self.set_direction_vector(direction_vector)
        self.set_position(pos)

    def take_damage(self, damage):
        health = self.durability
        health -= damage
        # print(f'take_damage: {damage}')
        self.durability = health
        if health <= 0:
            # health = 1000
            # self._air_plane_params.health_points = health
            self.create_explode()
            self.on_death()
            return True
        else:
            return False

    def create_bullet(self, bullet_sprite, local_position, direction):
        # direction = np.array([-direction[1], direction[0]])
        new_bullet = Bullet(self.team_number, self.game_data)
        new_bullet.set_map_size(self.get_map_size())
        new_bullet.set_sprite(pygame.transform.rotate(
            bullet_sprite, vector_2_angle(self.get_direction_vector())))
        local_position[1] = np.cos(np.radians(self.roll_attitude * 10)) * local_position[1]
        new_bullet.set_position(local_to_world(
            self.get_position(), direction, local_point=local_position))
        new_bullet.set_speed(self.velocity + 5)
        new_bullet.set_direction_vector(direction)
        new_bullet._damage = 10
        new_bullet.set_parent(parent=self)
        self.bullet_group.add(new_bullet)

    def create_bomb(self, bomb_sprite, local_position, direction):
        # direction = np.array([-direction[1], direction[0]])
        new_bullet = Bullet(self.team_number, self.game_data)
        new_bullet.set_map_size(self.get_map_size())
        new_bullet.set_sprite(pygame.transform.rotate(
            bomb_sprite, vector_2_angle(self.get_direction_vector())))
        local_position[1] = np.cos(np.radians(self.roll_attitude * 10)) * local_position[1]
        new_bullet.set_position(local_to_world(
            self.get_position(), direction, local_point=local_position))
        new_bullet.set_speed(self.velocity + 2)
        new_bullet.set_direction_vector(direction)
        new_bullet._damage = 10
        new_bullet.set_parent(self)
        self.bullet_group.add(new_bullet)

    def create_RKT(self, RKT_sprite, local_position, direction):
        # direction = np.array([-direction[1], direction[0]])
        new_bullet = Bullet(self.team_number, self.game_data)
        new_bullet.set_map_size(self.get_map_size())
        new_bullet.set_sprite(pygame.transform.rotate(
            RKT_sprite, vector_2_angle(self.get_direction_vector())))
        local_position[1] = np.cos(np.radians(self.roll_attitude * 10)) * local_position[1]
        new_bullet.set_position(local_to_world(
            self.get_position(), direction, local_point=local_position))
        new_bullet.set_speed(self.velocity + 4)
        new_bullet.set_direction_vector(direction)
        new_bullet._damage = 300
        new_bullet.set_parent(self)
        self.bullet_group.add(new_bullet)

    def create_AAM(self, aam_sprite, local_position, direction, target):
        # direction = np.array([-direction[1], direction[0]])
        new_aam = AAM(self.team_number, self.game_data)
        new_aam.set_map_size(self.get_map_size())
        # 由于此处的sprite会自己变化，所以应该给的是初始的姿态的 sprite
        new_aam.set_sprite(aam_sprite)
        local_position[1] = np.cos(np.radians(self.roll_attitude * 10)) * local_position[1]
        new_aam.set_position(local_to_world(
            self.get_position(), direction, local_point=local_position))
        new_aam.set_speed(self.velocity + 4)
        new_aam.angular_speed = 1.5
        new_aam.set_direction_vector(direction)
        new_aam._damage = 300
        new_aam.target_object = target
        new_aam.set_parent(self)
        self.bullet_group.add(new_aam)

    def on_death(self):
        """
        死亡前做点事情吧
        :return:
        """
        self.create_explode()
        # 然后将飞机从对应的渲染链表中移除
        self.game_data.remove_team_airplanes(self)
        self.kill()

    @abstractmethod
    def primary_weapon_attack(self):
        self.on_death()
        pass

    @abstractmethod
    def secondary_weapon_attack(self):
        pass


class FighterJet(AirPlane):
    def __init__(self, team_number, game_data):
        AirPlane.__init__(self, team_number, game_data)
        self.plane_type = PlaneType.Fighter
        self.primary_weapon_type = WeaponType.Weapon_None
        self.secondary_weapon_type = WeaponType.Weapon_None
        self.reload_counter = 0
        self.reload_time = 20

    def primary_weapon_attack(self):
        # 都会发射，不过如果锁定后可以锁定目标
        self.create_RKT(
            self.air_plane_sprites.primary_bullet_sprite,
            np.array([self._air_plane_params.plane_height * 0.4, 0]),
            self.get_direction_vector()
        )
        # height_start = self._air_plane_params.plane_height * 0.4
        # position_list = [[height_start, self._air_plane_params.plane_height * 0.3],
        #                  [height_start, self._air_plane_params.plane_height * 0.1],
        #                  [height_start, -self._air_plane_params.plane_height * 0.1],
        #                  [height_start, -self._air_plane_params.plane_height * 0.3]]
        #
        # for pos in position_list:
        #     self.create_bullet(
        #         self.air_plane_sprites.primary_bullet_sprite, np.array(pos),
        #         self.get_direction_vector())

    def secondary_weapon_attack(self):
        position_list = [[self._air_plane_params.plane_height * 0.4, 0]]

        for pos in position_list:
            self.create_bullet(self.air_plane_sprites.secondary_bullet_sprite, np.array(pos),
                               self.get_direction_vector())


class AttackAircraft(AirPlane):
    def __init__(self, team_number, game_data):
        super().__init__(team_number, game_data)
        self.plane_type = PlaneType.AttackAircraft

    def primary_weapon_attack(self):
        print('primary_weapon_attack')

    def secondary_weapon_attack(self):
        print('primary_weapon_attack')


class Bomber(AirPlane):
    def __init__(self, team_number, game_data):
        super().__init__(team_number, game_data)
        self.plane_type = PlaneType.Bomber
        self.primary_weapon_type = WeaponType.Weapon_None
        self.secondary_weapon_type = WeaponType.Weapon_None
        self.reload_counter = 0
        self.reload_time = 1

    def primary_weapon_attack(self):
        height_start = self._air_plane_params.plane_height * 0.4
        position_list = [[height_start, self._air_plane_params.plane_height * 0.3],
                         [height_start, self._air_plane_params.plane_height * 0.1],
                         [height_start, -self._air_plane_params.plane_height * 0.1],
                         [height_start, -self._air_plane_params.plane_height * 0.3]]

        for pos in position_list:
            self.create_bullet(
                self.air_plane_sprites.primary_bullet_sprite, np.array(pos),
                self.get_direction_vector())

    def secondary_weapon_attack(self):
        position_list = [[self._air_plane_params.plane_height * 0.4, 0]]

        for pos in position_list:
            self.create_bullet(self.air_plane_sprites.secondary_bullet_sprite, np.array(pos),
                               self.get_direction_vector())

