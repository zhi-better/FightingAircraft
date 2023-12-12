import numpy as np
import pygame
from overrides import overrides

from utils.cls_obj import DynamicObject
from abc import ABCMeta, abstractmethod

class AirPlane(DynamicObject):
    def __init__(self):
        super().__init__()
        self.health_points = 1000
        self.turning_speed = 0.8
        self.real_speed = 0
        self.max_speed = 0
        self.min_speed = 3
        self._speed_modulation_factor = 1.0
        self.real_turning_speed = self.turning_speed
        self._engine_temperature = 0
        self.engine_heat_rate = 0
        self.roll_mapping = {}
        self.pitch_mapping = {}
        self.attitude = np.zeros((2,))      # 表示飞行姿态
        self.target_attitude = np.zeros((2,))
        self.sprite_attitude = None

    def get_engine_temperature(self):
        return self._engine_temperature

    def _linear_interpolation(self, start, end, t=0.7, threshold=0.5):
        res = (1 - t) * start + t * end
        if np.abs(res - end) < threshold:
            res = end
        return res

    @overrides
    def get_sprite(self):
        idx_sprite = 0

        # 水平回归原位是优先级较高的操作
        rect_dic = self.roll_mapping[idx_sprite]
        plane_rect = pygame.Rect(rect_dic['x'], rect_dic['y'], rect_dic['width'], rect_dic['height'])
        plane_sprite_subsurface = self.sprite.subsurface(plane_rect)
        self.sprite_attitude = pygame.transform.rotate(plane_sprite_subsurface, self.get_angle())

        return self.sprite_attitude

    def get_angle(self):
        angle_rad = np.arctan2(self.direction_vector[1], self.direction_vector[0])
        # 将弧度转换为角度
        angle_deg = np.degrees(angle_rad)
        # print(angle_deg)
        return angle_deg

    def sppe_up(self):
        self._speed_modulation_factor = 1.1
        self.engine_heat_rate += 0.2

    def slow_down(self):
        self._speed_modulation_factor = 0.7

    def set_speed(self, speed):
        self.speed = speed
        self.real_speed = speed
        self.max_speed = self.speed * 2
        self.min_speed = 3

    @overrides
    def move(self):
        # 实际的速度永远和增益的比例有关
        if self._speed_modulation_factor > 1:
            # self._engine_temperature += self._speed_modulation_factor * 0.2
            if self._engine_temperature >= 100:
                self._engine_temperature = 100
                # print('engine overheating. ')
                # 速度插值，为了恢复常规的运行速度
                self.real_speed = self._linear_interpolation(self.real_speed, self.speed)
            else:
                self.real_speed = np.minimum(self.real_speed * self._speed_modulation_factor, self.max_speed)
        elif self._speed_modulation_factor < 1:
            self.real_speed = np.maximum(self.real_speed * self._speed_modulation_factor, self.min_speed)
        else:
            # 速度插值，为了恢复常规的运行速度
            self.real_speed = self._linear_interpolation(self.real_speed, self.speed)

        # 如果没有升温，那么就设置此时降温
        if self.engine_heat_rate == 0:
            self.engine_heat_rate = -0.3
        self._engine_temperature = np.maximum(0, self._engine_temperature + self.engine_heat_rate)

        print('\rthe real speed is: {:.2f}, engine temperature is: {}'.format(
            self.real_speed, self._engine_temperature), end='')

        self.set_position(
            self.get_position() + int(self.real_speed) * np.multiply(self.direction_vector, np.array([1, -1])))
        # 根据速度自动调整目前的速度向着
        self._speed_modulation_factor = 1   # 增益复位，防止影响下一帧运行速度
        self.engine_heat_rate = 0


    def take_damage(self, damage):
        print(f'take_damage: {damage}')

    def turn_left(self):
        # 逆时针旋转方向向量
        rotation_matrix = np.array([[np.cos(np.radians(self.real_turning_speed)), -np.sin(np.radians(self.real_turning_speed))],
                                    [np.sin(np.radians(self.real_turning_speed)), np.cos(np.radians(self.real_turning_speed))]])
        self.direction_vector = np.dot(rotation_matrix, self.direction_vector)

        self.real_turning_speed = self.turning_speed

    def turn_right(self):
        # 顺时针旋转方向向量
        rotation_matrix = np.array([[np.cos(np.radians(-self.real_turning_speed)), -np.sin(np.radians(-self.real_turning_speed))],
                                    [np.sin(np.radians(-self.real_turning_speed)), np.cos(np.radians(-self.real_turning_speed))]])
        self.direction_vector = np.dot(rotation_matrix, self.direction_vector)

        self.real_turning_speed = self.turning_speed

    def sharply_turn_left(self):
        if self._engine_temperature < 100:
            self.real_turning_speed = self.turning_speed * 2
            self.engine_heat_rate += 0.2
        self.turn_left()


    def sharply_turn_right(self):
        if self._engine_temperature < 100:
            self.real_turning_speed = self.turning_speed * 2
            self.engine_heat_rate += 0.2
        self.turn_right()

    @abstractmethod
    def primary_weapon_attack(self):
        pass

    @abstractmethod
    def secondary_weapon_attack(self):
        pass


class FighterJet(AirPlane):
    def __init__(self):
        super().__init__()

    def primary_weapon_attack(self):
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


