import torch
import torch.nn as nn
import torch.nn.functional as F


class FusionNet(nn.Module):
    def __init__(self, input_size_map, input_size_self, output_size):
        super(FusionNet, self).__init__()

        self.map_fc1 = nn.Linear(input_size_map, 64)
        self.map_fc2 = nn.Linear(64, 32)

        self.self_fc1 = nn.Linear(input_size_self, 64)
        self.self_fc2 = nn.Linear(64, 32)

        self.fc3 = nn.Linear(64, 32)
        self.fc4 = nn.Linear(32, output_size)

    def forward(self, map_input, self_input):
        map_out = F.relu(self.map_fc1(map_input))
        map_out = F.relu(self.map_fc2(map_out))

        self_out = F.relu(self.self_fc1(self_input))
        self_out = F.relu(self.self_fc2(self_out))

        fusion_out = torch.cat((map_out, self_out), dim=1)
        fusion_out = F.relu(self.fc3(fusion_out))
        fusion_out = self.fc4(fusion_out)

        action_probs = F.softmax(fusion_out, dim=1)

        return action_probs

# 设置输入和输出的维度
input_size_map = 20  # 适应地图上所有飞机的信息
input_size_self = 10  # 适应自己的飞机信息
output_size = 6  # 可能的动作数量

# 初始化神经网络
fusion_net = FusionNet(input_size_map, input_size_self, output_size)

# 假设有3个飞机
num_planes = 3

# 创建模拟输入数据
map_inputs = [torch.rand(1, input_size_map) for _ in range(num_planes)]  # 每个飞机对应的地图信息
self_inputs = [torch.rand(1, input_size_self) for _ in range(num_planes)]  # 每个飞机自身信息

# 处理每个飞机的信息并生成对应的动作概率分布
action_probs_list = []
for i in range(num_planes):
    action_probs = fusion_net(map_inputs[i], self_inputs[i])
    action_probs_list.append(action_probs)

# 计算所有飞机的动作概率分布的平均值
avg_action_probs = torch.stack(action_probs_list).mean(dim=0)

# 选定一个飞机作为攻击目标，使用其输出的概率分布
target_plane_index = 0
attack_action_probs = action_probs_list[target_plane_index]

# 打印结果
print("所有飞机的动作概率分布的平均值：", avg_action_probs)
print("选定的攻击目标飞机的动作概率分布：", attack_action_probs)
