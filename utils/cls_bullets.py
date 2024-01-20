from utils.cls_obj import DynamicObject
import pygame



class Bullet(DynamicObject):
    def __init__(self):
        super().__init__()
        self._damage = 0
        self.expired_time = 5000
        self.time_passed = 0
        self.parent = None

    def is_bullet_expired(self):
        return self.time_passed >= self.expired_time

    def get_sprite(self):
        return self.image

    def fixed_update(self, delta_time):
        self.time_passed += delta_time
        pos, _ = self.move(delta_time=delta_time)
        self.set_position(pos)
        # 如果自己的生命周期到了，那么就自己从父亲的子弹列表中删除
        if self.is_bullet_expired():
            self.parent.bullet_group.remove(self)

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
    def __init__(self):
        super().__init__()
        self.animation_list = []

    def explode(self):
        """
        火箭弹爆炸需要有爆炸动画
        :return:
        """
        print('explode! ')

class AAM(RKT):
    """
    追踪导弹，相较于普通火箭弹增加了追踪功能
    """
    def __init__(self):
        super().__init__()
        self.target_obj



