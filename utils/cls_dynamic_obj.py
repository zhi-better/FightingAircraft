
class DynamicObjects:
    def __init__(self):
        self._position = 0, 0
        self._direction_vector = 0, 0
        self.velocity = 0

    def set_position(self, x, y):
        self._position = x if x > 0 else 0, y if y > 0 else 0

    def move(self):
        self._position = self._position + self.velocity * self._direction_vector


