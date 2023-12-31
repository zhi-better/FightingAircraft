from abc import abstractmethod
import numpy as np
import pygame


def local_to_world(local_position, direction_vector, local_point):
    # 构造旋转矩阵
    rotation_matrix_local_to_world = np.array([[direction_vector[0], direction_vector[1]],
                                               [-direction_vector[1], direction_vector[0]]])

    # 将局部坐标转换为世界坐标
    world_point = local_position + np.dot(rotation_matrix_local_to_world, local_point)

    return world_point


def get_rect_sprite(sprite, rect_dic):
    plane_rect = pygame.Rect(rect_dic['x'], rect_dic['y'], rect_dic['width'], rect_dic['height'])
    plane_sprite_subsurface = sprite.subsurface(plane_rect)

    return plane_sprite_subsurface


class StaticObject(pygame.sprite.Sprite):
    def __init__(self):
        # 调用父类的初始化方法
        super().__init__()
        self._position = np.zeros((2,))
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.image = None
        self.collision_box = None

        self._map_size = np.array([0, 0])

    def set_map_size(self, map_size):
        self._map_size = map_size

    def get_map_size(self):
        return self._map_size

    def update(self, *args, **kwargs):
        """
        更新
        :param args:
        :param kwargs:
        :return:
        """

    def set_sprite(self, sprite):
        rect = sprite.get_rect()
        self.rect.width = rect.width
        self.rect.height = rect.height
        self.image = sprite

    def get_sprite(self):
        return self.image

    def load_sprite(self, img_file_name):
        self.image = pygame.image.load(img_file_name)
        rect = self.image.get_rect()
        self.rect.width = rect.width
        self.rect.height = rect.height
        return self.image

    def set_position(self, vector_2d):
        if self._map_size[0] == 0 or self._map_size[1] == 0:
            Warning('please set map size first!!!')
        # 更新对应的 Sprite 的位置
        vector_2d[0] = vector_2d[0] % self._map_size[0]
        vector_2d[1] = vector_2d[1] % self._map_size[1]
        self.rect.x = vector_2d[0] - 0.5 * self.rect.width
        self.rect.y = vector_2d[1] - 0.5 * self.rect.height
        if self.rect.x < 0:
            self.rect.x += self._map_size[0]
        if self.rect.y < 0:
            self.rect.y += self._map_size[1]

        self._position = vector_2d

    def get_rect(self):
        return self.rect

    def get_position(self):
        return self._position


class DynamicObject(StaticObject):
    def __init__(self):
        super().__init__()
        self.direction_vector = np.array([0, 1])
        self.speed = 0.0
        self.velocity = 0
        self.angular_velocity = 0

    def set_speed(self, speed):
        self.speed = speed
        self.velocity = speed

    def move(self, delta_time):
        """
        move函数并不会修改任何游戏数据，只是会根据从上一个逻辑帧出发经过的时间
        计算得到目前实例应该在的位置
        :param delta_time:
        :return:
        """
        # ---------------------------------------------
        # turn
        direction_vector = self.direction_vector
        # print("\rdirection vector: {}".format(direction_vector[0], direction_vector[1]), end='')
        ang_velocity_tmp = self.angular_velocity * delta_time * 0.08
        rotation_matrix = np.array(
            [[np.cos(np.radians(ang_velocity_tmp)), -np.sin(np.radians(ang_velocity_tmp))],
             [np.sin(np.radians(ang_velocity_tmp)), np.cos(np.radians(ang_velocity_tmp))]])
        direction_vector = np.dot(rotation_matrix, direction_vector)
        # ---------------------------------------------
        # move
        _2d_velocity = (int(self.velocity * delta_time * 0.1) *
                        np.multiply(direction_vector, np.array([1, -1])))

        return self.get_position() + _2d_velocity, direction_vector

    def set_direction_vector(self, vector_2d):
        vector_2d = vector_2d / np.linalg.norm(vector_2d)
        self.direction_vector = vector_2d

    def get_angle(self, direction_vector):
        """
        获取飞机当前在屏幕上渲染的2d角度
        :return:
        """
        angle_rad = np.arctan2(direction_vector[1], direction_vector[0])
        # 将弧度转换为角度
        angle_deg = np.degrees(angle_rad)
        # print(angle_deg)
        return float(angle_deg)



