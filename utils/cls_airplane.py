import numpy as np

from utils.cls_obj import DynamicObject
from abc import ABCMeta, abstractmethod

class AirPlane(DynamicObject):
    def __init__(self):
        super().__init__()
        self.health_points = 1000
        self.flying_speed = 5
        self.turning_speed = 5

    def get_angle(self):
        angle_rad = np.arctan2(self.direction_vector[1], self.direction_vector[0])
        # 将弧度转换为角度
        angle_deg = np.degrees(angle_rad)
        # print(angle_deg)
        return angle_deg

    def take_damage(self, damage):
        print(f'take_damage: {damage}')

    def turn_left(self):
        # 逆时针旋转方向向量
        rotation_matrix = np.array([[np.cos(np.radians(self.turning_speed)), -np.sin(np.radians(self.turning_speed))],
                                    [np.sin(np.radians(self.turning_speed)), np.cos(np.radians(self.turning_speed))]])
        self.direction_vector = np.dot(rotation_matrix, self.direction_vector)

        # print('turn_left')

    def turn_right(self):
        # 顺时针旋转方向向量
        rotation_matrix = np.array([[np.cos(np.radians(-self.turning_speed)), -np.sin(np.radians(-self.turning_speed))],
                                    [np.sin(np.radians(-self.turning_speed)), np.cos(np.radians(-self.turning_speed))]])
        self.direction_vector = np.dot(rotation_matrix, self.direction_vector)

        # print('turn_right')

    def sharply_turn_left(self):
        print('sharply_turn_left')

    def sharply_turn_right(self):
        print('sharply_turn_right')

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


