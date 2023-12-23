from utils.cls_obj import DynamicObject
import pygame

class Bullet(DynamicObject):
    def __init__(self):
        super().__init__()
        self.damage = 0
        self.animation_list = []
        self.count = 0
        self.life_time = 5000
        self.time_passed = 0

    def get_sprite(self):

        return self.sprite

    def move(self, delta_time):
        self.time_passed += delta_time
        return super().move(delta_time=delta_time)

    def explode(self):
        print('explode')







