import pygame
import xml.etree.ElementTree as ET
import random
import math

# 解析 XML 文件
tree = ET.parse('smoke.xml')
root = tree.getroot()

# 获取粒子效果配置参数
max_particles = int(root.find('maxParticles').attrib['value'])
particle_lifespan = float(root.find('particleLifeSpan').attrib['value'])
particle_lifespan_variance = float(root.find('particleLifespanVariance').attrib['value'])
start_particle_size = float(root.find('startParticleSize').attrib['value'])
start_particle_size_variance = float(root.find('startParticleSizeVariance').attrib['value'])
finish_particle_size = float(root.find('finishParticleSize').attrib['value'])
finish_particle_size_variance = float(root.find('FinishParticleSizeVariance').attrib['value'])
angle = float(root.find('angle').attrib['value'])
angle_variance = float(root.find('angleVariance').attrib['value'])
rotation_start = float(root.find('rotationStart').attrib['value'])
rotation_start_variance = float(root.find('rotationStartVariance').attrib['value'])
rotation_end = float(root.find('rotationEnd').attrib['value'])
rotation_end_variance = float(root.find('rotationEndVariance').attrib['value'])
start_color = [float(root.find('startColor').attrib[attr]) for attr in ['alpha', 'red', 'green', 'blue']]
start_color_variance = [float(root.find('startColorVariance').attrib[attr]) for attr in ['alpha', 'red', 'green', 'blue']]
finish_color = [float(root.find('finishColor').attrib[attr]) for attr in ['alpha', 'red', 'green', 'blue']]
finish_color_variance = [float(root.find('finishColorVariance').attrib[attr]) for attr in ['alpha', 'red', 'green', 'blue']]
blend_func_source = int(root.find('blendFuncSource').attrib['value'])
blend_func_destination = int(root.find('blendFuncDestination').attrib['value'])
emitter_type = int(root.find('emitterType').attrib['value'])
source_position_variance_x = float(root.find('sourcePositionVariance').attrib['x'])
source_position_variance_y = float(root.find('sourcePositionVariance').attrib['y'])
speed = float(root.find('speed').attrib['value'])
speed_variance = float(root.find('speedVariance').attrib['value'])
gravity_x = float(root.find('gravity').attrib['x'])
gravity_y = float(root.find('gravity').attrib['y'])
radial_acceleration = float(root.find('radialAcceleration').attrib['value'])
radial_accel_variance = float(root.find('radialAccelVariance').attrib['value'])
tangential_acceleration = float(root.find('tangentialAcceleration').attrib['value'])
tangential_accel_variance = float(root.find('tangentialAccelVariance').attrib['value'])
max_radius = float(root.find('maxRadius').attrib['value'])
max_radius_variance = float(root.find('maxRadiusVariance').attrib['value'])
min_radius = float(root.find('minRadius').attrib['value'])
rotate_per_second = float(root.find('rotatePerSecond').attrib['value'])
rotate_per_second_variance = float(root.find('rotatePerSecondVariance').attrib['value'])

# Pygame 初始化
pygame.init()

# 设置屏幕尺寸
screen_width, screen_height = 800, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption('Particle Effect Visualization')

# 定义粒子类
class Particle(pygame.sprite.Sprite):
    def __init__(self, x, y, size, color, lifespan):
        super().__init__()
        self.image = pygame.Surface([size, size])
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.lifespan = lifespan
        self.birth_time = pygame.time.get_ticks()

    def update(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.birth_time > self.lifespan:
            self.kill()

# 创建粒子组
all_particles = pygame.sprite.Group()

# 主循环
running = True
clock = pygame.time.Clock()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 在这里添加绘制粒子效果的代码
    for i in range(max_particles):
        particle_size = random.uniform(start_particle_size - start_particle_size_variance, start_particle_size + start_particle_size_variance)
        particle_color = [
            random.uniform(start_color[j] - start_color_variance[j], start_color[j] + start_color_variance[j])
            for j in range(4)
        ]
        particle = Particle(screen_width // 2, screen_height // 2, particle_size, particle_color, particle_lifespan)
        all_particles.add(particle)

    screen.fill((0, 0, 0))
    all_particles.update()
    all_particles.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
