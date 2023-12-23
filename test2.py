import pygame as py
import math
import random

py.init()
mysize = width, height = 800, 600
screen = py.display.set_mode(mysize)
fullscreen = False  # 全屏开关
py.display.set_caption("游戏测试")


class Point:
    speed = 0
    upspeed = 1;
    direction = 0
    position = [0, 0]
    size = 1

    def __init__(self, position, speed, direction, size):
        self.position = position
        self.speed = speed
        self.direction = direction
        self.size = size
        return  # 坐标，速度，方向，点大小

    def run(self, ):
        if (self.position[0] <= 0 or self.position[0] >= width):
            self.direction = -self.direction + math.pi
        if (self.position[1] <= 0 or self.position[1] >= height):
            self.direction = -self.direction
        if (self.distance(py.mouse.get_pos()) > 130 and self.distance(py.mouse.get_pos()) < 200):
            y = (py.mouse.get_pos()[1] - self.position[1])
            x = (py.mouse.get_pos()[0] - self.position[0])
            if x != 0:
                self.mouse_direction = math.atan2(y, x)
            self.upspeed = 3
            x = self.upspeed * self.speed * math.cos(self.mouse_direction)
            y = self.upspeed * self.speed * math.sin(self.mouse_direction)
            if x != 0 and (self.distance(py.mouse.get_pos()) < 110 or self.distance(py.mouse.get_pos()) > 130):
                self.position[0] += x / abs(x) * math.ceil(abs(x))
            if y != 0 and (self.distance(py.mouse.get_pos()) < 110 or self.distance(py.mouse.get_pos()) > 130):
                self.position[1] += y / abs(y) * math.ceil(abs(y))
        else:
            self.upspeed = 1
            x = self.upspeed * self.speed * math.cos(self.direction)
            y = self.upspeed * self.speed * math.sin(self.direction)
            if x != 0 and (self.distance(py.mouse.get_pos()) < 110 or self.distance(py.mouse.get_pos()) > 130):
                self.position[0] += x / abs(x) * math.ceil(abs(x))
            if y != 0 and (self.distance(py.mouse.get_pos()) < 110 or self.distance(py.mouse.get_pos()) > 130):
                self.position[1] += y / abs(y) * math.ceil(abs(y))  # 运动

    def show(self):
        self.position = [int(i + 0.5) for i in self.position]
        py.draw.circle(screen, (44, 67, 116), self.position, self.size)  # 图像变动

    def distance(self, other):  # 求点距
        return math.sqrt((self.position[0] - other[0]) ** 2 + (self.position[1] - other[1]) ** 2)


class Graph:
    pointlist = []  # 点列表

    def __init__(self, number):
        self.pointlist.append(Point([0, 0], 0, 0, 0))
        for i in range(number):
            self.pointlist.append(Point([random.randint(1, width), random.randint(1, height)], random.randint(1, 3),
                                        i / number * 2 * math.pi, 3))  # 根据number创建点个数

    def run(self):
        for it in self.pointlist:
            it.run()  # 运动

    def show(self):
        for it in self.pointlist:
            it.show()
        self.line()  # 图像变动

    def line(self):  # 画线
        color = [0, 0, 0]
        self.pointlist[0].position = py.mouse.get_pos()
        for i in self.pointlist:
            for j in self.pointlist:
                s = i.distance(j.position)
                if s < 150:
                    color = [int(s * 1.6), int(80 + s), int(180 + s * 0.5)]
                    py.draw.aaline(screen, color, i.position, j.position, 5)


mygraph = Graph(40)  # 画线
while True:
    screen.fill((255, 255, 255))
    for each in py.event.get():
        if each.type == py.KEYDOWN:
            if each.key == py.K_F11:
                fullscreen = not fullscreen
                if fullscreen:
                    mysize = width, height = 1920, 1080
                    screen = py.display.set_mode((1920, 1080), py.FULLSCREEN | py.HWSURFACE)
                else:
                    mysize = width, height = 800, 600
                    screen = py.display.set_mode(mysize)

    mygraph.run()
    mygraph.show()
    py.display.flip()
    py.time.Clock().tick(150)

