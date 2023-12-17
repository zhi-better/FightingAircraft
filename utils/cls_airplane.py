from enum import Enum, IntFlag

import numpy as np
import pygame
from overrides import overrides
from utils.cls_ammunition import *
from utils.cls_obj import DynamicObject
from abc import ABCMeta, abstractmethod


class PlaneType(Enum):
    FighterJet = 1
    AttackAircraft = 2
    Bomber = 3


class FlyState(IntFlag):
    Norm = 0b00000000
    SharpTurnLeft = 0b00000100
    SharpTurnRight = 0b00001000
    Roll = 0b00010000
    Pitch = 0b00100000
    SpeedUp = 0b01000000
    SlowDown = 0b10000000
    TurnLeft = 0b00000001
    TurnRight = 0b00000010


class WeaponType(Enum):
    Weapon_None = 0
    MG_762_4x = 1
    MG_762_2x = 2


class AirPlane(DynamicObject):
    def __init__(self):
        super().__init__()
        self.primary_weapon_animation_list = []
        self.health_points = 1000
        self.angular_speed = 0.8
        self.velocity = 0
        self._velocity_modulation_factor = 0
        self.max_speed = 0
        self.min_speed = 3
        self.angular_velocity = 0
        self._engine_temperature = 0
        self.engine_heat_rate = 0
        self.overheat_duration = 60
        self.heat_counter = 60
        self.roll_mapping = {}
        self.pitch_mapping = {}
        self.roll_attitude = 0.0
        self._roll_modulation_factor = 0
        self.pitch_attitude = 0.0
        self._pitch_modulation_factor = 0
        self.target_attitude = np.zeros((2,))
        self.fly_state = FlyState.Norm
        self.ammunition_list = []
        self.ammunition_sprite = None

    def reset_roll_attitude(self):
        if self.roll_attitude == 0:
            self._roll_modulation_factor = 0
        elif 1 <= self.roll_attitude <= 18:
            self._roll_modulation_factor = -1
        elif 18 < self.roll_attitude <= 35:
            self._roll_modulation_factor = 1
        else:
            self._roll_modulation_factor = 0
            self.roll_attitude = 0
            print('err roll attitude: {}'.format(self.roll_attitude))

    def reset_pitch_attitude(self):
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

    def roll(self):
        self.fly_state = self.fly_state | FlyState.Roll

    def pitch(self):
        self.fly_state = self.fly_state | FlyState.Pitch


    def get_engine_temperature(self):
        return self._engine_temperature

    def _linear_interpolation(self, start, end, t=0.7, threshold=0.5):
        res = (1 - t) * start + t * end
        if np.abs(res - end) < threshold:
            res = end
        return res

    @overrides
    def get_sprite(self):
        # 水平回归原位是优先级较高的操作
        if self.roll_attitude != 0:
            rect_dic = self.roll_mapping[int(self.roll_attitude)]
        elif self.pitch_attitude != 0:
            rect_dic = self.pitch_mapping[int(self.pitch_attitude)]
        else:
            rect_dic = self.pitch_mapping[int(0)]
        plane_rect = pygame.Rect(rect_dic['x'], rect_dic['y'], rect_dic['width'], rect_dic['height'])
        plane_sprite_subsurface = self.sprite.subsurface(plane_rect)
        # self.sprite_attitude = pygame.transform.rotate(plane_sprite_subsurface, self.get_angle())

        return plane_sprite_subsurface

    def get_angle(self):
        angle_rad = np.arctan2(self.direction_vector[1], self.direction_vector[0])
        # 将弧度转换为角度
        angle_deg = np.degrees(angle_rad)
        # print(angle_deg)
        return float(angle_deg)

    def sppe_up(self):
        self._speed_modulation_factor = 1.1
        self.engine_heat_rate += 0.2
        self.fly_state = self.fly_state | FlyState.SpeedUp

    def slow_down(self):
        self._speed_modulation_factor = 0.7
        self.fly_state = self.fly_state | FlyState.SlowDown

    def set_speed(self, speed):
        self.speed = speed
        self.velocity = speed
        self.max_speed = self.speed * 2
        self.min_speed = 3

    @overrides
    def move(self, delta_time):
        # 首先调整控制飞机姿态
        # ---------------------------------------------
        # 横滚
        if self.fly_state & FlyState.Roll:
            if self._engine_temperature < 100:
                # 滚动处理
                if self.pitch_attitude == 0:
                    self._roll_modulation_factor = 1
            else:
                self.heat_counter = 0

        # ---------------------------------------------
        # 俯仰
        if self.fly_state & FlyState.Pitch:
            if self._engine_temperature < 100:
                # 俯仰
                if self.roll_attitude == 0:
                    self._pitch_modulation_factor = 1
                    self.engine_heat_rate += 0.5
            else:
                self.heat_counter = 0
                self.reset_pitch_attitude()
        else:
            self.reset_pitch_attitude()
        self.pitch_attitude += self._pitch_modulation_factor * delta_time * 0.016
        self._pitch_modulation_factor = 0
        if self.pitch_attitude >= 36:
            self.pitch_attitude = 0
        # print('\rplane roll attitude: {}, pitch attitude: {}. '.format(self.roll_attitude, self.pitch_attitude), end='')

        # ---------------------------------------------
        # 加减速
        if self.fly_state & FlyState.SpeedUp:
            self.engine_heat_rate += 0.3
            self.heat_counter = 0
            self._velocity_modulation_factor += 0.5
        elif self.fly_state & FlyState.SlowDown:
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
            self.velocity += np.sign(self.speed - self.velocity) * 0.5
        self._velocity_modulation_factor = 0
        # print('\rthe real speed is: {:.2f}, engine temperature is: {}'.format(
        #     self.velocity, self._engine_temperature), end='')

        # ---------------------------------------------
        # 转弯
        if self.pitch_attitude == 0:
            # 首先看一下当前的姿态，然后更新对应的姿态信息
            # 姿态正确才能更细对应的转向速度等信息
            if self.fly_state & FlyState.SharpTurnLeft:
                if self._engine_temperature >= 100:
                    self.heat_counter = 0
                    self.fly_state = self.fly_state | FlyState.TurnLeft
                else:
                    self.engine_heat_rate += 0.5
                    if self.roll_attitude < 8:
                        self._roll_modulation_factor = 1
                    elif 8 <= self.roll_attitude < 10:
                        self._roll_modulation_factor = 0
                        self.roll_attitude = 9
                    else:
                        self.reset_roll_attitude()
                    self.angular_velocity = self.angular_speed * 2
            elif self.fly_state & FlyState.SharpTurnRight:
                if self._engine_temperature >= 100:
                    self.heat_counter = 0
                    self.fly_state = self.fly_state | FlyState.TurnRight
                else:
                    self.engine_heat_rate += 0.5
                    if self.roll_attitude == 0:
                        self.roll_attitude = 36
                    if self.roll_attitude > 28:
                        self._roll_modulation_factor = -1
                    elif 26 < self.roll_attitude <= 28:
                        self._roll_modulation_factor = 0
                        self.roll_attitude = 27
                    else:
                        self.reset_roll_attitude()
                    self.angular_velocity = self.angular_speed * -2


            # 普通转弯
            if self.fly_state & FlyState.TurnLeft:
                if self.roll_attitude < 2:
                    self._roll_modulation_factor = 1
                elif self.roll_attitude >= 2:
                    self._roll_modulation_factor = 0
                    self.roll_attitude = 2
                else:
                    self.reset_roll_attitude()
                self.angular_velocity = self.angular_speed
            elif self.fly_state & FlyState.TurnRight:
                if self.roll_attitude == 0:
                    self.roll_attitude = 36
                if self.roll_attitude > 34:
                    self._roll_modulation_factor = -1
                elif self.roll_attitude <= 34:
                    self._roll_modulation_factor = 0
                    self.roll_attitude = 34
                else:
                    self.reset_roll_attitude()
                self.angular_velocity = -self.angular_speed
            else:
                if self._roll_modulation_factor == 0:
                    self.reset_roll_attitude()
        self.roll_attitude += self._roll_modulation_factor * delta_time * 0.016
        self._roll_modulation_factor = 0
        self.angular_velocity = self.angular_velocity * delta_time * 0.02

        # 如果姿态不对，记得及时修正
        if self.roll_attitude >= 36:
            self.roll_attitude = 0

        # ---------------------------------------------
        # turn
        rotation_matrix = np.array(
            [[np.cos(np.radians(self.angular_velocity)), -np.sin(np.radians(self.angular_velocity))],
             [np.sin(np.radians(self.angular_velocity)), np.cos(np.radians(self.angular_velocity))]])
        self.direction_vector = np.dot(rotation_matrix, self.direction_vector)

        # ---------------------------------------------
        # move
        _2d_velocity = int(
            self.velocity * delta_time * 0.1 * np.cos(np.radians(self.pitch_attitude * 10))) * np.multiply(self.direction_vector, np.array([1, -1]))
        self.set_position(
            self.get_position() + _2d_velocity)

        print(f'\r velocity: {_2d_velocity[0]}, {_2d_velocity[1]}', end='')

        # ---------------------------------------------
        # 发动机温度
        if self.engine_heat_rate == 0:
            # 如果发动机温度过高，持续一段时间后再降温
            if self._engine_temperature >= 100:
                if self.heat_counter >= self.overheat_duration:
                    self.engine_heat_rate = -0.3
            else:
                self.engine_heat_rate = -0.3
        self._engine_temperature = np.minimum(
            100, np.maximum(0, self._engine_temperature + self.engine_heat_rate * delta_time * 0))
        # self._engine_temperature = np.minimum(
        #     100, np.maximum(0, self._engine_temperature + self.engine_heat_rate * delta_time * 0.02))
        self.heat_counter += 1
        self.engine_heat_rate = 0

        # 重置飞行状态
        self.angular_velocity = 0
        self.fly_state = FlyState.Norm

        # 所有发射的弹药也得 move
        for ammu in self.ammunition_list:
            ammu.move()

    def take_damage(self, damage):
        print(f'take_damage: {damage}')

    def turn_left(self):
        self.fly_state = self.fly_state | FlyState.TurnLeft

    def turn_right(self):
        self.fly_state = self.fly_state | FlyState.TurnRight

    def sharply_turn_left(self):
        self.fly_state = self.fly_state | FlyState.SharpTurnLeft

    def sharply_turn_right(self):
        self.fly_state = self.fly_state | FlyState.SharpTurnRight

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
        # 首先根据创建的武器类型在对应位置创建对应的子弹
        if self.reload_counter < self.reload_time:
            self.reload_counter += 1
        else:
            self.reload_counter = 0
            new_ammunition = Ammunition()
            new_ammunition.sprite = self.ammunition_sprite
            new_ammunition.animation_list = self.primary_weapon_animation_list
            new_ammunition.set_position(self.get_position())
            new_ammunition.set_direction_vector(self.direction_vector)
            self.ammunition_list.append(new_ammunition)
            print('primary_weapon_attack')

    def secondary_weapon_attack(self):
        print('primary_weapon_attack')


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

    def primary_weapon_attack(self):
        print('primary_weapon_attack')

    def secondary_weapon_attack(self):
        print('primary_weapon_attack')


