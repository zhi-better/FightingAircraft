import os

import PyInstaller.__main__

# 请替换为你的.py文件的路径
file_to_package = 'main.py'

# 请替换为你想要生成的.exe文件的路径和名称
output_directory = ''
output_name = 'FightingAircraft.exe'

# 确保输出目录存在，如果不存在则创建
if output_directory:
    os.makedirs(output_directory, exist_ok=True)

# 执行打包操作
PyInstaller.__main__.run([
    '--onefile',
    # '--noconsole',  # 这个选项会使生成的exe文件不显示cmd窗口
    '--distpath', output_directory,
    '--name', output_name,
    file_to_package
])

print(f'打包完成，可执行文件位于: {output_directory}/{output_name}')
