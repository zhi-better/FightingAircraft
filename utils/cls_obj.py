import numpy as np


class StaticObject:
    def __init__(self):
        self._position = np.zeros((2,))
        self.faction_mask = 0
        self.sprite_list = []
        self.collision_box = None

    def set_position(self, vector_2d):
        self._position = vector_2d

    def get_position(self):
        return self._position

class DynamicObject(StaticObject):
    def __init__(self):
        super().__init__()
        self.direction_vector = np.array([0, 1])
        self.velocity = 0

    def move(self):
        self.set_position(
            self.get_position() + self.velocity * np.multiply(self.direction_vector, np.array([1, -1])))

    def set_direction_vector(self, vector_2d):
        self.direction_vector = vector_2d




