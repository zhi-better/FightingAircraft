import numpy as np
import pygame


class StaticObject:
    def __init__(self):
        self._position = np.zeros((2,))
        self.faction_mask = 0
        self.sprite = None
        self.collision_box = None

    def get_sprite(self):

        return self.sprite

    def load_sprite(self, img_file_name):
        self.sprite = pygame.image.load(img_file_name)

        return self.sprite

    def set_position(self, vector_2d):
        self._position = vector_2d

    def get_position(self):
        return self._position

class DynamicObject(StaticObject):
    def __init__(self):
        super().__init__()
        self.direction_vector = np.array([0, 1])
        self.speed = 0.0

    def set_speed(self, speed):
        self.speed = speed

    def move(self):
        self.set_position(
            self.get_position() + int(self.speed) * np.multiply(self.direction_vector, np.array([1, -1])).astype(int))

    def set_direction_vector(self, vector_2d):
        self.direction_vector = vector_2d




