import numpy as np

from utils.cls_obj import DynamicObject, get_rect_sprite, vector_2_angle
import pygame



class Bullet(DynamicObject):
    def __init__(self, team_number, game_data):
        super().__init__(team_number, game_data)
        self._damage = 0
        self.expired_time = 2000
        self.time_passed = 0
        self.parent = None

    def is_bullet_expired(self):
        return self.time_passed >= self.expired_time

    def get_sprite(self):
        return self.image

    def explode(self, target):
        self.parent.bullet_group.remove(self)
        # 释放自身资源
        self.on_death()
        # 返回真表示攻击目标已死亡，假表示未死亡
        if target is not None:
            return target.take_damage(self._damage)
        else:
            return False


    def fixed_update(self, delta_time):
        self.time_passed += delta_time
        pos, _ = self.move(delta_time=delta_time)
        self.set_position(pos)
        # 如果自己的生命周期到了，那么就自己从父亲的子弹列表中删除
        if self.is_bullet_expired():
            self.explode(None)

    def set_parent(self, parent):
        """
        设置是谁发射的这个子弹
        :param parent:
        :return:
        """
        self.parent = parent

    def get_damage(self):
        return self._damage

    def set_damage(self, damage):
        self._damage = damage


class RKT(Bullet):
    """
    火箭弹，主要用于对地攻击
    """
    def __init__(self, team_number, game_data):
        super().__init__(team_number, game_data)

    def explode(self, target):
        super().explode(target)


class AAM(RKT):
    """
    追踪导弹，相较于普通火箭弹增加了追踪功能
    """
    def __init__(self, team_number, game_data):
        super().__init__(team_number, game_data)
        self.target_object = None
        self.angular_speed = 1.5
        self._damage = 200
        self.expired_time = 4000
        self.angle_threshold = 0.5

    def get_sprite(self):
        """
        追踪导弹在发射出去后需要转向，因此模型贴图需要更新
        :return:
        """
        tmp_image = pygame.transform.rotate(
            self.image, vector_2_angle(self.get_direction_vector()))

        return tmp_image

    def fixed_update(self, delta_time):
        """
        追踪目标
        :return:
        """
        self.time_passed += delta_time
        # 如果自己的生命周期到了，那么就自己从父亲的子弹列表中删除
        if self.is_bullet_expired():
            self.explode(None)
        else:
            if self.target_object is not None:
                lead_target_position = self.target_object.get_position() - self.get_position()
                # 此处需要得到目标和自己的夹角大小，超出阈值的话直接取消追踪
                target_vector = lead_target_position / np.linalg.norm(lead_target_position)
                cross_result = -np.cross(
                    self.get_direction_vector().T*np.array([1, -1]), target_vector.T)
                # print(f'\rcross result: {cross_result}', end='')
                abs_cross_result = np.abs(cross_result)[0]
                if 0.05 < abs_cross_result < self.angle_threshold:
                    self.angular_velocity = (self.angular_speed
                                             * np.sign(cross_result))[0]
                elif abs_cross_result < 0.05:
                    self.angular_velocity = 0
                else:
                    # 超出对应的范围，直接取消追踪
                    # print('target escaped! ')
                    self.target_object = None

            # 如果没有目标，仍然要向前进
            pos, direction_vector = self.move(delta_time=delta_time)
            self.set_position(pos)
            self.set_direction_vector(direction_vector)



