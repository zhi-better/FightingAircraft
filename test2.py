import xml.etree.ElementTree as ET
import pygame
import base64
import zlib
import struct

# 读取XML文件
xml_file_path = "map/map0.xml"  # 替换为你的TMX文件路径
tree = ET.parse(xml_file_path)
root = tree.getroot()

# 获取地图的宽度和高度
width = int(root.attrib["width"])
height = int(root.attrib["height"])

# 获取瓦片宽度和高度
tilewidth = int(root.attrib["tilewidth"])
tileheight = int(root.attrib["tileheight"])

# 设置缩放比例
scale_factor = 0.1  # 调整为你需要的缩放比例
scaled_tilewidth = int(tilewidth * scale_factor)
scaled_tileheight = int(tileheight * scale_factor)

# 创建Pygame窗口
initial_window_size = (width * scaled_tilewidth, height * scaled_tileheight)
pygame.init()
screen = pygame.display.set_mode(initial_window_size)
pygame.display.set_caption("Tiled Map")

# 解析图层数据
data_element = root.find(".//layer/data")
data_str = data_element.text.strip()
data_bytes = base64.b64decode(data_str)
data = zlib.decompress(data_bytes)

# 将解压后的数据转换为列表
tile_ids = list(struct.unpack("<" + "I" * (len(data) // 4), data))

# 获取tileset中的tile元素
tileset = root.find(".//tileset")
# 获取图像文件信息
image_elem = tileset.find('image')
image_source = image_elem.get('source')

# 加载瓦片集图片
tileset_image = pygame.image.load("map/"+image_source)  # 替换为你的瓦片集图片路径

# 缩放瓦片集图片
scaled_tileset_image = pygame.transform.scale(tileset_image, (scaled_tilewidth * 8, scaled_tileheight * 8))

# 渲染地图
for y in range(height):
    for x in range(width):
        tile_id = tile_ids[y * width + x]
        print(f"Tile ID at ({x}, {y}): {tile_id}", end='')
        if tile_id != 0:
            rec_x = tile_id % 8 - 1
            if rec_x < 0:
                rec_x = 7
                rec_y = tile_id // 8 - 1
            else:
                rec_y = tile_id // 8
            tile_rect = pygame.Rect(rec_x * scaled_tilewidth, rec_y * scaled_tileheight, scaled_tilewidth, scaled_tileheight)
            print(f', rect at {rec_x}, {rec_y}')
            screen.blit(scaled_tileset_image, (x * scaled_tilewidth, y * scaled_tileheight), tile_rect)


# 刷新屏幕
pygame.display.flip()

# 运行事件循环
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

# 退出程序
pygame.quit()
