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
        self.real_speed = self.speed
        self.real_turning_speed = self.turning_speed
        self.engine_temperature = 0
        self.roll_mapping = {}
        self.pitch_mapping = {}
        self.attitude = np.zeros((2,))      # 表示飞行姿态
        self.target_attitude = np.zeros((2,))
        self.sprite_attitude = None

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
        self.real_speed = self.speed * 1.5

    def slow_down(self):
        self.real_speed = self.speed * 0.7

    def set_speed(self, speed):
        self.speed = speed
        self.real_speed = speed

    @overrides
    def move(self):
        self.set_position(
            self.get_position() + self.real_speed * np.multiply(self.direction_vector, np.array([1, -1])))
        self.real_speed = self.speed

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
        self.real_turning_speed = self.turning_speed * 1.5
        self.turn_left()


    def sharply_turn_right(self):
        self.real_turning_speed = self.turning_speed * 1.5
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


