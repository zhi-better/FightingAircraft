import torch

# 假设您的1x10张量为probs

# 加速、减速、左转、右转、左急转、右急转、拉升、无动作、主武器攻击、副武器攻击
probs = torch.rand(1, 10)  # 示例的随机概率张量
print(probs)
# 将概率张量划分为三组
group1 = torch.stack((probs[0, 0], probs[0, 1], probs[0, 7]), dim=0)  # 加速，减速，无动作
group2 = torch.stack((probs[0, 2], probs[0, 3], probs[0, 4], probs[0, 5], probs[0, 7]), dim=0)  # 左转，右转，左急转，右急转，无动作
group3 = torch.stack((probs[0, 8], probs[0, 9]), dim=0)  # 主武器攻击，副武器攻击

# 找到每组中概率最大的动作
max_prob_action_group1 = torch.argmax(group1)
max_prob_action_group2 = torch.argmax(group2)
max_prob_action_group3 = torch.argmax(group3)

print(f"Max probability action for group 1: {max_prob_action_group1}")
print(f"Max probability action for group 2: {max_prob_action_group2}")
print(f"Max probability action for group 3: {max_prob_action_group3}")

# 通过这些信息执行较大概率的动作
# ...
