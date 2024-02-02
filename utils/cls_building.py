import time

import numpy as np

from utils.cls_bullets import Bullet
from utils.cls_explode import Explode
from utils.cls_obj import *


def detect_turret_target_obj(turret_obj, target_objs, distance_threshold):
    """
    根据自身位置和物体的位置来寻找到自身的攻击目标
    :param objs:
    :return:
    """
    for target_obj in target_objs:
        if target_obj.team_number != turret_obj.team_number:
            distances = np.linalg.norm(target_obj.get_position() - turret_obj.get_position())
            if distances < distance_threshold:
                return target_obj

    return None



def calculate_lead_target_position(target_relative_position, target_move_direction,
                                   target_move_velocity, bullet_move_velocity):
    """
    计算对应目标防空炮塔应该攻击的方向
    :param target_relative_position:
    :param target_move_direction:
    :param target_move_velocity:
    :param bullet_move_velocity:
    :return:
    """
    # 先归一化
    target_move_direction = target_move_direction / np.linalg.norm(target_move_direction)
    target_relative_direction = target_relative_position / np.linalg.norm(target_relative_position)

    # 利用正弦定理直接求解对应的
    lead_target_angle_sin = \
        (target_move_velocity / bullet_move_velocity *
         np.cross(np.multiply(target_relative_direction.T, np.array([1, -1]).reshape((1, 2))),
                  target_move_direction.T))
    rad_lead_target = -np.arcsin(lead_target_angle_sin)

    # 此处根据四个象限应该是有四种情况用于计算
    rad_target = vector_2_angle(target_relative_position, is_deg=False)
    rotate_target = rad_lead_target + rad_target
    # print(f'\rcross result: {lead_target_angle_sin}, angle origional: {np.rad2deg(rad_target)}', end='')

    return np.array([np.cos(rotate_target), -np.sin(rotate_target)]).reshape((2, 1))


class Building(StaticObject):
    """
    普通建筑
    """
    def __init__(self, team_number, game_data):
        super().__init__(team_number, game_data)
        self.durability = 100  # 建筑的耐久度
        self.body_sprite = None     # 常规的建筑的精灵
        self.ruin_sprite = None     # 被破坏后的建筑的精灵
        self.explode_sub_textures = None
        self.explode_sprite = None

    def take_damage(self, damage):
        self.durability -= damage
        if self.durability <= 0:
            self.on_death()
            return True
        else:
            return False

    def create_explode(self):
        explode = Explode(self.game_data)
        # 此处对应的 list 给他一个新的 list, 防止影响原有的 list
        explode.set_explode_sprites(
            self.explode_sub_textures.copy(), self.explode_sprite)
        explode.set_map_size(self.get_map_size())
        explode.set_position(self.get_position())

    def on_death(self):
        print('building destroyed!')
        self.set_sprite(self.ruin_sprite)

        self.create_explode()


class Turret(DynamicObject, Building):
    """
    炮台的基类，主要用于控制发射子弹等操作
    """
    def __init__(self, team_number, game_data):
        Building.__init__(self, team_number, game_data)
        DynamicObject.__init__(self, team_number, team_number)
        self.bullet_sprite = None
        self.cannon_sprite = None   # 炮管的精灵
        self._bullet_damage = 10
        self.team_number = 0
        #  炮塔不能动，但是可以旋转，哈哈哈哈哈哈笑死
        self.speed = 0
        self.velocity = 0
        self.angular_speed = 2
        self.bullet_velocity = 6    # 因为不能动，所以要设置的大一些
        self.attack_range = 1000     # 攻击范围要大于视野范围
        self.view_range = 800       # 视野范围，主要用于检测攻击敌机
        self.bullet_group = pygame.sprite.Group()
        self.all_planes = []

    def set_turret_sprites(self, cannon_sprite, body_sprite, ruin_sprite):
        """
        设置炮台的相关精灵，包括炮塔底座精灵，两种状态，正常和摧毁
        炮管精灵，一种状态，会随着目标转动
        :param cannon_sprite:
        :param turret_sprite:
        :return:
        """
        self.cannon_sprite = cannon_sprite
        self.body_sprite = body_sprite
        self.ruin_sprite = ruin_sprite
        self.set_sprite(self.body_sprite)

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
        # new_image = pygame.transform.rotate(
        #     self.cannon_sprite, vector_2_angle(self.get_direction_vector()))
        # rect = new_image.get_rect()
        # self.rect.width = rect.width
        # self.rect.height = rect.height
        # self.mask = pygame.mask.from_surface(self.image)
        # ----------------------------------------------------------------
        # 此处需要考虑资源释放问题
        if self.durability > 0:
            rotated_cannon = pygame.transform.rotate(
                self.cannon_sprite, vector_2_angle(self.get_direction_vector()))
            return self.body_sprite, rotated_cannon
        else:
            return self.ruin_sprite, None

    def fire(self, local_position):
        """
        控制在某个位置创造子弹，并按照预定义的速度和炮塔的方向出射
        :return: 返回创建的子弹
        """
        # direction = np.array([-direction[1], direction[0]])
        new_bullet = Bullet(self.team_number, self.game_data)
        new_bullet.set_map_size(self.get_map_size())
        new_bullet.set_sprite(pygame.transform.rotate(self.bullet_sprite, vector_2_angle(self._direction_vector)))
        new_bullet.set_position(local_to_world(
            self.get_position(), self._direction_vector, local_point=local_position))
        new_bullet.set_speed(self.velocity + self.bullet_velocity)
        new_bullet.set_direction_vector(self._direction_vector)
        new_bullet.set_damage(self._bullet_damage)
        new_bullet.set_parent(parent=self)
        self.bullet_group.add(new_bullet)
        return new_bullet

    def on_death(self):
        # 创建一个爆炸效果
        self.create_explode()


class Flak(Turret):
    """
    防空炮
    """
    def __init__(self, render_list, list_explodes):
        super().__init__(render_list, list_explodes)
        self.target_obj = None  # 表示攻击的目标
        self.round_bullet_count = 5  # 每轮发射子弹时候的子弹数量
        self.round_shoot_interval = 2  # 每轮设计过程中子弹发射间隔
        self.round_interval = 30  # 每轮发射之间的时间间隔
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
        # 只有有生命的时候才会检测目标并攻击
        if self.durability > 0:
            if self.target_obj:
                pos_target = self.target_obj.get_position()
                velocity = self.target_obj.velocity
                target_direction_vector = self.target_obj.get_direction_vector()
                target_relative_position = pos_target - self.get_position()
                # 旋转炮台瞄准
                lead_target_position = calculate_lead_target_position(
                    target_relative_position=target_relative_position, target_move_direction=target_direction_vector,
                    target_move_velocity=velocity, bullet_move_velocity=self.bullet_velocity
                )
                cross_result = np.cross(self.get_direction_vector().T, lead_target_position.T)

                # 防止为了精确攻击乱抖动炮台
                if np.abs(cross_result) > 0.05:
                    self.angular_velocity = (self.angular_speed
                                             * np.sign(cross_result))[0]
                else:
                    self.angular_velocity = 0
                pos, direction_vector = self.move(delta_time=delta_time)
                self.set_position(pos)
                self.set_direction_vector(direction_vector)

                # 如果实际炮塔角度和理想角度比较接近的话就可以开火了
                vector_angle_cos = float(np.dot(self.get_direction_vector().T, lead_target_position))
                # 为了避免防空炮被溜，开火前的倾角满足一定的一致性就可以同步开火了
                if vector_angle_cos > 0.95:
                    if self.weapon_cool_down_timer > self.round_interval:
                        self.weapon_cool_down_timer = 0
                    # 如果刚好满足发射间隔要求并且未超过发射的最大数量，直接发射
                    if (self.weapon_cool_down_timer % self.round_shoot_interval == 0
                            and self.weapon_cool_down_timer < self.round_shoot_interval * self.round_bullet_count):
                        self.fire(local_position=np.array([30, 0]).reshape((2, 1)))
                        # print('fired!')

                # 检测目标是否已经从攻击范围中逃脱，如果已经逃脱，那么应该
                # print(f'\r{np.linalg.norm(target_relative_position)}', end='')
                if np.linalg.norm(target_relative_position) > self.attack_range:
                    self.target_obj = None
            else:
                # 否则就要检测是否有新的目标进入到攻击范围内
                self.target_obj = detect_turret_target_obj(self, self.all_planes, self.view_range)




class Tower(StaticObject):
    """
    防御塔，攻击能力稍微弱一点
    """

    def __init__(self):
        super().__init__()
