import xml.etree.ElementTree as ET

def load_plane_xml_data(file_path):
    # 解析XML文件
    tree = ET.parse(file_path)
    root = tree.getroot()

    # 获取图片路径
    image_path = root.attrib.get('imagePath')

    # 初始化滚转和俯仰的映射字典
    roll_mapping = {}
    pitch_mapping = {}

    # 遍历SubTexture元素
    for subtexture in root.findall('SubTexture'):
        name = subtexture.attrib.get('name')
        x = int(subtexture.attrib.get('x'))
        y = int(subtexture.attrib.get('y'))
        width = int(subtexture.attrib.get('width'))
        height = int(subtexture.attrib.get('height'))

        # 判断是滚转还是俯仰
        parts = name.split('/')
        if parts[1] == 'roll':
            roll_mapping[int(parts[2][4:])] = {'x': x, 'y': y, 'width': width, 'height': height}
        elif parts[1] == 'pitch':
            pitch_mapping[int(parts[2][4:])] = {'x': x, 'y': y, 'width': width, 'height': height}

    # 返回图片路径和映射字典
    return image_path, roll_mapping, pitch_mapping

# 替换下面的file_path变量为你的XML文件路径
file_path = 'objects/Ar234.xml'

image_path, roll_mapping, pitch_mapping = load_plane_xml_data(file_path)

# 打印结果
print(f"Image Path: {image_path}")
print("Roll Mapping:")
for key, value in roll_mapping.items():
    print(f"{key}: {value}")
print("Pitch Mapping:")
for key, value in pitch_mapping.items():
    print(f"{key}: {value}")
