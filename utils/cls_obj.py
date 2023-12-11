

class Objects:
    def __init__(self):
        self._position = 0, 0
        self.sprite = None

    def set_position(self, x, y):
        self._position = x if x > 0 else 0, y if y > 0 else 0







