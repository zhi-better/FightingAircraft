from utils.cls_obj import DynamicObject
import pygame

class Ammunition(DynamicObject):
    def __init__(self):
        super().__init__()
        self.damage = 0
        self.animation_list = []
        self.count = 0

    def get_sprite(self):
        if self.count >= len(self.animation_list):
            self.count = 0
        rect_dic = self.animation_list[self.count]
        rect = pygame.Rect(rect_dic['x'], rect_dic['y'], rect_dic['width'], rect_dic['height'])
        self.count += 1
        sprite_subsurface = self.sprite.subsurface(rect)

        return sprite_subsurface

    def explode(self):
        print('explode')







