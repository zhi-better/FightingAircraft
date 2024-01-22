from utils.cls_obj import StaticObject, get_rect_sprite


class Explode(StaticObject):
    """
    爆炸的 class, 用法为在飞机死亡后在死亡的地点创建一个爆炸，爆炸完毕后自动死去
    """
    def __init__(self, list_explodes):
        super().__init__()
        self.list_explodes = list_explodes
        self.list_explodes.append(self)
        self.explode_sub_textures = []
        self.explode_sprite = None
        self.explode_time_scale = 1
        self.time_counter = 0

    def set_explode_sprites(self, explode_sub_textures, explode_sprite):
        self.explode_sub_textures = explode_sub_textures
        self.explode_sprite = explode_sprite
        sprite = get_rect_sprite(self.explode_sprite, self.explode_sub_textures[0])
        self.set_sprite(sprite)

    def get_sprite(self):
        sprite = get_rect_sprite(self.explode_sprite, self.explode_sub_textures[0])
        self.set_sprite(sprite)
        return self.image

    def fixed_update(self, delta_time):
        self.time_counter += 1
        if self.time_counter % self.explode_time_scale == 0:
            self.time_counter = 0
            self.explode_sub_textures.pop(0)
            if len(self.explode_sub_textures) == 0:
                self.on_death()

    def on_death(self):
        self.list_explodes.remove(self)
        # print('explode death! ')
        self.kill()






