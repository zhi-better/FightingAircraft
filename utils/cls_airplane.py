from enum import Enum, IntFlag

import numpy as np
import pygame
from overrides import overrides
from utils.cls_ammunition import *
from utils.cls_obj import *
from abc import ABCMeta, abstractmethod


class AttitudeType(Enum):
    NoneAttitude = 0
    RollAttitude = 1
    PitchAttitude = 2


class PlaneType(Enum):
    FighterJet = 1
    AttackAircraft = 2
    Bomber = 3


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
    Weapon_None = 0
    MG_762_4x = 1
    MG_762_2x = 2


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
        self.name = 'AirPlane'
        self.health_points = 1000  # 生命值
        self.angular_speed = 0.8  # 转向速度
        self.speed = 0  # 正常运行速度
        self.max_speed = 0  # 最大速度
        self.min_speed = 3  # 最小速度
        self.engine_heat_rate = 0  # 引擎温度升高速率
        self.overheat_duration = 60  # 引擎过热保护时间
        self.primary_weapon_reload_time = 0.5
        self.secondary_weapon_reload_time = 0.5


class AirPlane(DynamicObject):
    def __init__(self):
        super().__init__()
        self.image_template = None
        self.air_plane_sprites = AirPlaneSprites()
        self.air_plane_params = AirPlaneParams()
        self._velocity_modulation_factor = 0
        self._engine_temperature = 0
        self.heat_counter = 60
        self.roll_attitude = 0.0
        self._roll_modulation_factor = 0
        self.pitch_attitude = 0.0
        self._pitch_modulation_factor = 0
        self.target_attitude = np.zeros((2,))
        self.input_state = InputState.NoInput
        self.primary_weapon_reload_counter = 0
        self.secondary_weapon_reload_counter = 0
        self.map_size = np.array([])
        self.bullet_group = pygame.sprite.Group()
        self.team_number = 0

    def load_sprite(self, img_file_name):
        self.image_template = pygame.image.load(img_file_name)

        return self.image_template

    def get_air_plane_params(self):
        return self.air_plane_params

    def set_air_plane_params(self, params):
        self.air_plane_params = params

    def reset_attitude(self, attitude_type=AttitudeType.NoneAttitude):
        if attitude_type == AttitudeType.RollAttitude:
            if self.roll_attitude == 0:
                self._roll_modulation_factor = 0
            elif 1 <= self.roll_attitude <= 18:
                self._roll_modulation_factor = -1
            elif 18 < self.roll_attitude <= 35:
                self._roll_modulation_factor = 1
            else:
                self._roll_modulation_factor = 0
                self.roll_attitude = 0
                # print('err roll attitude: {}'.format(self.roll_attitude))
        elif attitude_type == AttitudeType.PitchAttitude:
            if self.pitch_attitude == 0:
                self._pitch_modulation_factor = 0
            elif 1 < self.pitch_attitude <= 9:
                self._pitch_modulation_factor = -1
            elif 9 < self.pitch_attitude <= 17:
                self._pitch_modulation_factor = 1
            elif 17 < self.pitch_attitude <= 18:
                self._pitch_modulation_factor = 0
                self.pitch_attitude = 0
                self.roll_attitude = 18
                self.direction_vector = self.direction_vector * -1
            elif 18 < self.pitch_attitude < 35:
                self._pitch_modulation_factor = 1
            else:
                self.pitch_attitude = 0
                self._pitch_modulation_factor = 0
                print('err pitch attitude: {}'.format(self.pitch_attitude))
        else:
            ValueError('err attitude type: {}'.format(attitude_type))

    def roll(self):
        self.input_state = self.input_state | InputState.Roll

    def pitch(self):
        self.input_state = self.input_state | InputState.Pitch

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

        self.image = get_rect_sprite(self.image_template, rect_dic)
        self.image = pygame.transform.rotate(self.image, self.get_angle(self.direction_vector))
        rect = self.image.get_rect()
        self.rect.width = rect.width
        self.rect.height = rect.height
        return self.image

    def speed_up(self):
        """
        加速
        :return:
        """
        self._speed_modulation_factor = 1.1
        self.air_plane_params.engine_heat_rate += 0.2
        self.input_state = self.input_state | InputState.SpeedUp

    def slow_down(self):
        """
        减速
        :return:
        """
        self._speed_modulation_factor = 0.7
        self.input_state = self.input_state | InputState.SlowDown

    def set_speed(self, speed):
        """
        设置飞机的速度参数，实际速度为 velocity
        :param speed:
        :return:
        """
        self.speed = speed
        self.velocity = speed
        self.max_speed = self.speed * 1.5
        self.min_speed = self.speed * 0.7

    @overrides
    def move(self, delta_time):
        """
        move函数并不会修改任何游戏数据，只是会根据从上一个逻辑帧出发经过的时间
        计算得到目前实例应该在的位置
        :param delta_time:
        :return:
        """
        # ---------------------------------------------
        # turn
        direction_vector = self.direction_vector
        ang_velocity_tmp = self.angular_velocity * delta_time * 0.06
        rotation_matrix = np.array(
            [[np.cos(np.radians(ang_velocity_tmp)), -np.sin(np.radians(ang_velocity_tmp))],
             [np.sin(np.radians(ang_velocity_tmp)), np.cos(np.radians(ang_velocity_tmp))]])
        direction_vector = np.dot(rotation_matrix, direction_vector)
        # ---------------------------------------------
        # move
        _2d_velocity = int(
            self.velocity * delta_time * 0.14 * np.cos(np.radians(self.pitch_attitude * 10))) * np.multiply(
            direction_vector, np.array([1, -1]))

        return self.get_position() + _2d_velocity, direction_vector

    def primary_fire(self):
        self.input_state = self.input_state | InputState.PrimaryWeaponAttack

    def secondary_fire(self):
        self.input_state = self.input_state | InputState.SecondaryWeaponAttack

    def fixed_update(self, delta_time):
        """
        飞机逻辑数据的更新
        :param delta_time:
        :return:
        """
        # 首先调整控制飞机姿态
        # ---------------------------------------------
        # 横滚
        if self.input_state & InputState.Roll:
            if self._engine_temperature < 100:
                # 滚动处理
                if self.pitch_attitude == 0:
                    self._roll_modulation_factor = 1
            else:
                self.heat_counter = 0

        # ---------------------------------------------
        # 俯仰
        if self.input_state & InputState.Pitch:
            if self._engine_temperature < 100:
                # 俯仰
                if self.roll_attitude == 0:
                    self._pitch_modulation_factor = 1
                    self.air_plane_params.engine_heat_rate += 0.5
            else:
                self.heat_counter = 0
                self.reset_attitude(attitude_type=AttitudeType.PitchAttitude)
        else:
            # self.reset_pitch_attitude()
            self.reset_attitude(attitude_type=AttitudeType.PitchAttitude)
        self.pitch_attitude += self._pitch_modulation_factor * delta_time * 0.016
        self._pitch_modulation_factor = 0
        if self.pitch_attitude >= 36:
            self.pitch_attitude = 0
        # print('\rplane roll attitude: {}, pitch attitude: {}. '.format(self.roll_attitude, self.pitch_attitude), end='')

        # ---------------------------------------------
        # 加减速
        if self.input_state & InputState.SpeedUp:
            self.air_plane_params.engine_heat_rate += 0.3
            self.heat_counter = 0
            self._velocity_modulation_factor += 0.5
        elif self.input_state & InputState.SlowDown:
            self._velocity_modulation_factor -= 0.3
        if self._velocity_modulation_factor > 0:
            if self._engine_temperature >= 100:
                # 增益直接降为 -0.5
                self._velocity_modulation_factor = -0.5
                # 速度插值，为了恢复常规的运行速度
                self.velocity = np.maximum(self.velocity + self._velocity_modulation_factor, self.speed)
            else:
                self.velocity = np.minimum(self.velocity + self._velocity_modulation_factor, self.max_speed)
        elif self._velocity_modulation_factor < 0:
            self.velocity = np.maximum(self.velocity + self._velocity_modulation_factor, self.min_speed)
        else:
            # 速度插值，为了恢复常规的运行速度
            self.velocity += np.sign(self.speed - self.velocity) * 0.1
            if np.abs(self.velocity - self.speed) < 0.2:
                self.velocity = self.speed
        self._velocity_modulation_factor = 0
        # print('\rthe real speed is: {:.2f}, engine temperature is: {}'.format(
        #     self.velocity, self._engine_temperature), end='')

        # ---------------------------------------------
        # 转弯
        # self.plane_state = self.plane_state | InputState.SharpTurnLeft
        if self.pitch_attitude == 0:
            # 首先看一下当前的姿态，然后更新对应的姿态信息
            # 姿态正确才能更细对应的转向速度等信息
            if self.input_state & InputState.SharpTurnLeft:
                if self._engine_temperature >= 100:
                    self.heat_counter = 0
                    self.input_state = self.input_state | InputState.TurnLeft
                else:
                    self.air_plane_params.engine_heat_rate += 0.5
                    if self.roll_attitude < 8:
                        self._roll_modulation_factor = 1
                    elif 8 <= self.roll_attitude < 10:
                        self._roll_modulation_factor = 0
                        self.roll_attitude = 9
                    else:
                        # self.reset_roll_attitude()
                        self.reset_attitude(attitude_type=AttitudeType.RollAttitude)
                    self.angular_velocity = self.air_plane_params.angular_speed * 2
            elif self.input_state & InputState.SharpTurnRight:
                if self._engine_temperature >= 100:
                    self.heat_counter = 0
                    self.input_state = self.input_state | InputState.TurnRight
                else:
                    self.air_plane_params.engine_heat_rate += 0.5
                    if self.roll_attitude == 0:
                        self.roll_attitude = 36
                    if self.roll_attitude > 28:
                        self._roll_modulation_factor = -1
                    elif 26 < self.roll_attitude <= 28:
                        self._roll_modulation_factor = 0
                        self.roll_attitude = 27
                    else:
                        self.reset_attitude(attitude_type=AttitudeType.RollAttitude)
                        # self.reset_roll_attitude()
                    self.angular_velocity = self.air_plane_params.angular_speed * -2

            # 普通转弯
            if self.input_state & InputState.TurnLeft:
                if self.roll_attitude < 2:
                    self._roll_modulation_factor = 1
                elif self.roll_attitude >= 2:
                    self._roll_modulation_factor = 0
                    self.roll_attitude = 2
                else:
                    self.reset_attitude(attitude_type=AttitudeType.RollAttitude)
                    # self.reset_roll_attitude()
                self.angular_velocity = self.air_plane_params.angular_speed
            elif self.input_state & InputState.TurnRight:
                if self.roll_attitude == 0:
                    self.roll_attitude = 36
                if self.roll_attitude > 34:
                    self._roll_modulation_factor = -1
                elif self.roll_attitude <= 34:
                    self._roll_modulation_factor = 0
                    self.roll_attitude = 34
                else:
                    self.reset_attitude(attitude_type=AttitudeType.RollAttitude)
                    # self.reset_roll_attitude()
                self.angular_velocity = -self.air_plane_params.angular_speed
            else:
                if self._roll_modulation_factor == 0:
                    self.reset_attitude(attitude_type=AttitudeType.RollAttitude)
                    # self.reset_roll_attitude()
        self.roll_attitude += self._roll_modulation_factor * delta_time * 0.016
        self._roll_modulation_factor = 0
        self.angular_velocity = self.angular_velocity * delta_time * 0.02

        # 如果姿态不对，记得及时修正
        if self.roll_attitude >= 36:
            self.roll_attitude = 0

        # ---------------------------------------------
        # 发动机温度
        if self.air_plane_params.engine_heat_rate == 0:
            # 如果发动机温度过高，持续一段时间后再降温
            if self._engine_temperature >= 100:
                if self.heat_counter >= self.air_plane_params.overheat_duration:
                    self.air_plane_params.engine_heat_rate = -0.3
            else:
                self.air_plane_params.engine_heat_rate = -0.3
        self._engine_temperature = np.minimum(
            100, np.maximum(0, self._engine_temperature + self.air_plane_params.engine_heat_rate * delta_time * 0))
        # self._engine_temperature = np.minimum(
        #     100, np.maximum(0, self._engine_temperature + self.engine_heat_rate * delta_time * 0.02))
        self.heat_counter += 1
        self.air_plane_params.engine_heat_rate = 0

        if self.input_state & InputState.PrimaryWeaponAttack:
            if self.primary_weapon_reload_counter <= 0:
                self.primary_weapon_attack()
                self.primary_weapon_reload_counter += self.air_plane_params.primary_weapon_reload_time
            else:
                self.primary_weapon_reload_counter -= delta_time * 0.001
        else:
            if self.primary_weapon_reload_counter <= 0:
                self.primary_weapon_reload_counter = 0
            else:
                self.primary_weapon_reload_counter -= delta_time * 0.001

        if self.input_state & InputState.SecondaryWeaponAttack:
            if self.secondary_weapon_reload_counter <= 0:
                self.secondary_weapon_attack()
                self.secondary_weapon_reload_counter += self.air_plane_params.secondary_weapon_reload_time
            else:
                self.secondary_weapon_reload_counter -= delta_time * 0.001
        else:
            if self.secondary_weapon_reload_counter <= 0:
                self.secondary_weapon_reload_counter = 0
            else:
                self.secondary_weapon_reload_counter -= delta_time * 0.001

        # --------------------------------------------------------------------
        # 重置飞行状态
        self.input_state = InputState.NoInput

        pos, direction_vector = self.move(delta_time=delta_time)
        self.direction_vector = direction_vector
        # self.set_position(pos)

        # for bullet in self.bullet_group:
        #     pos, _ = bullet.move(delta_time=delta_time)
        #     bullet.set_position(pos)
        #     if bullet.time_passed >= bullet.life_time:
        #         self.bullet_group.remove(bullet)
                # print('bullet removed. ')

        return pos, self.get_angle(self.direction_vector)

    def take_damage(self, damage):
        health = self.air_plane_params.health_points
        health -= damage
        # print(f'take_damage: {damage}')
        self.air_plane_params.health_points = health
        if health <= 0:
            health = 1000
            self.air_plane_params.health_points = health
            return True
        else:
            return False


    def turn_left(self):
        self.input_state = self.input_state | InputState.TurnLeft

    def turn_right(self):
        self.input_state = self.input_state | InputState.TurnRight

    def sharply_turn_left(self):
        self.input_state = self.input_state | InputState.SharpTurnLeft

    def sharply_turn_right(self):
        self.input_state = self.input_state | InputState.SharpTurnRight

    def create_bullet(self, bullet_sprite, local_position, direction):
        new_bullet = Bullet()
        new_bullet.set_map_size(self.get_map_size())
        new_bullet.set_sprite(bullet_sprite)
        local_position[1] = np.cos(np.radians(self.roll_attitude * 10)) * local_position[1]
        new_bullet.set_position(local_to_world(
            self.get_position(), direction, local_point=local_position))
        new_bullet.set_speed(self.velocity + 3)
        new_bullet.set_direction_vector(direction)
        new_bullet.damage = 10
        self.bullet_group.add(new_bullet)

    @abstractmethod
    def primary_weapon_attack(self):
        pass

    @abstractmethod
    def secondary_weapon_attack(self):
        pass


class FighterJet(AirPlane):
    def __init__(self):
        super().__init__()
        self.primary_weapon_type = WeaponType.Weapon_None
        self.secondary_weapon_type = WeaponType.Weapon_None
        self.reload_counter = 0
        self.reload_time = 1

    def primary_weapon_attack(self):
        position_list = [[45, 30],
                         [45, 15],
                         [45, -15],
                         [45, -30]]

        for pos in position_list:
            self.create_bullet(self.air_plane_sprites.primary_bullet_sprite, np.array(pos), self.direction_vector)

    def secondary_weapon_attack(self):
        position_list = [[55, 0]]

        for pos in position_list:
            self.create_bullet(self.air_plane_sprites.secondary_bullet_sprite, np.array(pos), self.direction_vector)


class AttackAircraft(AirPlane):
    def __init__(self):
        super().__init__()

    def primary_weapon_attack(self):
        print('primary_weapon_attack')

    def secondary_weapon_attack(self):
        print('primary_weapon_attack')


class Bomber(AirPlane):
    def __init__(self):
        super().__init__()
        self.primary_weapon_type = WeaponType.Weapon_None
        self.secondary_weapon_type = WeaponType.Weapon_None
        self.reload_counter = 0
        self.reload_time = 1

    def pitch(self):
        pass

    def primary_weapon_attack(self):
        position_list = [[45, 30],
                         [45, 15],
                         [45, -15],
                         [45, -30]]

        for pos in position_list:
            self.create_bullet(self.air_plane_sprites.primary_bullet_sprite, np.array(pos), self.direction_vector)

    def secondary_weapon_attack(self):
        position_list = [[55, 0]]

        for pos in position_list:
            self.create_bullet(self.air_plane_sprites.secondary_bullet_sprite, np.array(pos), self.direction_vector)

