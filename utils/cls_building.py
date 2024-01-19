import time

import numpy as np

from utils.cls_bullets import Bullet
from utils.cls_obj import *


def detect_target_obj(self_position, obj_positions):
    """
    根据自身位置和物体的位置来寻找到自身的攻击目标
    :param objs:
    :return:
    """


def calculate_lead_target_rotate_direction(target_vector, target_move_vector,
                                           target_move_velocity, bullet_move_velocity):
    """
    计算对应目标防空炮塔应该攻击的方向
    :param target_vector:
    :param target_move_vector:
    :param target_move_velocity:
    :param bullet_move_velocity:
    :return:
    """
    # 先归一化
    target_move_vector = target_move_vector / np.linalg.norm(target_move_vector)
    target_vector = target_vector / np.linalg.norm(target_vector)

    # 利用正弦定理直接求解对应的
    lead_target_angle_sin = target_move_velocity / bullet_move_velocity * np.linalg.norm(
        np.cross(target_vector.reshape((1,2)), target_move_vector.reshape((1,2))))
    rad_lead_target = np.arcsin(lead_target_angle_sin)

    rad_target = vector_2_angle(target_vector, is_deg=False)
    rotate_target = rad_lead_target + rad_target

    return np.array([np.cos(rotate_target), np.sin(rotate_target)]).reshape((2, 1))


class Building(StaticObject):
    """
    普通建筑
    """

    def __init__(self):
        super().__init__()
        self.durability = 1000  # 建筑的耐久度

    def take_damage(self, damage):
        self.durability -= damage
        if self.durability <= 0:
            print('building destroyed!')
            return True
        else:
            return False


class Turret(DynamicObject):
    """
    炮台的基类，主要用于控制发射子弹等操作
    """
    def __init__(self):
        super().__init__()
        self.bullet_sprite = None
        self._bullet_damage = 2

        #  炮塔不能动，但是可以旋转，哈哈哈哈哈哈笑死
        self.speed = 0
        self.velocity = 0
        self.angular_speed = 1
        self.bullet_velocity = 4  # 因为不能动，所以要设置的大一些

    def set_bullet_sprite(self, sprite):
        self.bullet_sprite = sprite

    def set_bullet_damage(self, damage):
        self._bullet_damage = damage

    def get_sprite(self):
        """
        由于炮塔需要旋转，所以此函数需要重写，自动刷新对应的 sprite
        :return:
        """
        # 注意此处要在基础的上面进行改动，是一种相对变化
        new_image = pygame.transform.rotate(
            self.image, vector_2_angle(np.multiply(self.direction_vector, np.array([1, -1]).reshape((2, 1)))))
        rect = new_image.get_rect()
        self.rect.width = rect.width
        self.rect.height = rect.height
        self.mask = pygame.mask.from_surface(self.image)

        return new_image


    def fire(self, local_position):
        """
        控制在某个位置创造子弹，并按照预定义的速度和炮塔的方向出射
        :return: 返回创建的子弹
        """
        # direction = np.array([-direction[1], direction[0]])
        new_bullet = Bullet()
        new_bullet.set_map_size(self.get_map_size())
        new_bullet.set_sprite(pygame.transform.rotate(self.bullet_sprite, vector_2_angle(self.direction_vector)))
        new_bullet.set_position(local_to_world(
            self.get_position(), self.direction_vector, local_point=local_position))
        new_bullet.set_speed(self.velocity + self.bullet_velocity)
        new_bullet.set_direction_vector(self.direction_vector)
        new_bullet.set_damage(self._bullet_damage)

        return new_bullet


class Flak(Turret):
    """
    防空炮
    """

    def __init__(self):
        super().__init__()
        self.target_obj = None  # 表示攻击的目标
        self.round_bullet_count = 5  # 每轮发射子弹时候的子弹数量
        self.round_shoot_interval = 15  # 每轮设计过程中子弹发射间隔
        self.round_interval = 120  # 每轮发射之间的时间间隔
        self.weapon_cool_down_timer = 0  # 辅助判断发射冷却时间的计数器

    def fixed_update(self, delta_time):
        self.weapon_cool_down_timer += 1
        '''
        首先判断目前是否有攻击的目标单位
        有攻击目标：
            转动炮台开始瞄准，然后判断目前的角度是否已经瞄准目标敌机并且可以打提前量
            已瞄准：
                判断当前炮弹是否处于冷却时间
                已经冷却：
                    发射，打特喵的
                没有冷却：
                    等待
        '''
        if self.target_obj:
            pos = self.target_obj.get_position()
            velocity = self.target_obj.velocity
            direction_vector = self.target_obj.direction_vector
            target_vector = pos - self.get_position()
            # 旋转炮台瞄准
            turret_rotate_target_vector = calculate_lead_target_rotate_direction(
                target_vector=target_vector, target_move_vector=direction_vector,
                target_move_velocity=velocity, bullet_move_velocity=self.bullet_velocity
            )
            # 调用父类的旋转的代码，首先判断防空炮应该旋转的位置
            cross_result = float(np.dot(self.direction_vector.T, turret_rotate_target_vector))
            # self.angular_velocity = -float(self.angular_speed * np.sign(cross_result))
            self.angular_velocity = 1
            pos, direction_vector = self.move(delta_time=delta_time)
            self.set_position(pos)
            self.direction_vector = direction_vector
            # 如果实际炮塔角度和理想角度比较接近的话就可以开火了
            vector_angle_cos = float(np.dot(self.direction_vector.T, turret_rotate_target_vector))
            if vector_angle_cos > 0.9:
                self.direction_vector = turret_rotate_target_vector
                if self.weapon_cool_down_timer > self.round_interval:
                    self.weapon_cool_down_timer = 0
                # 如果刚好满足发射间隔要求并且未超过发射的最大数量，直接发射
                if (self.weapon_cool_down_timer % self.round_shoot_interval == 0
                        and self.weapon_cool_down_timer < self.round_shoot_interval * self.round_bullet_count):
                    # self.fire(local_position=np.array([0, 30]).reshape((2, 1)))
                    print('fired!')
            # else:
            #     print(vector_angle_cos)


class BFlak(StaticObject):
    """
    防空炮
    """

    def __init__(self):
        super().__init__()
        self.target_obj = None  # 表示攻击的目标
        self.round_bullet_count = 5  # 每轮发射子弹时候的子弹数量
        self.round_shoot_interval = 2  # 每轮设计过程中子弹发射间隔
        self.round_interval = 6  # 每轮发射之间的时间间隔

    def detect_target_obj(self, objs):
        """
        根据自身位置和物体的位置来寻找到自身的攻击目标
        :param objs:
        :return:
        """

    def fire(self):
        """
        发射子弹，每次发射一轮
        :return:
        """


class Tower(StaticObject):
    """
    防御塔，攻击能力稍微弱一点
    """

    def __init__(self):
        super().__init__()
