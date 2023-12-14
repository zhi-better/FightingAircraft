from utils.cls_obj import DynamicObject


class Ammunition(DynamicObject):
    def __init__(self):
        super().__init__()
        self.damage = 0

    def explode(self):
        print('explode')







