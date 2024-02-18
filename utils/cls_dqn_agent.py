import collections
import random
import time

import numpy as np
from matplotlib import pyplot as plt
from torch.autograd import Variable

import torch
import torch.nn as nn
import torch.nn.functional as F
from tqdm import tqdm


class AIAircraftNet(nn.Module):
    def __init__(self):
        super(AIAircraftNet, self).__init__()
        """
        神经网络 v1.0 输入：
            所有敌人相对于自身的位置，方向，速度，转向速度，自身温度
            2 + 2 + 1 + 1 + 1 = 7
        神经网络 v2.0 输入：
            增加自身的引擎温度，速度，转向速度，横滚姿态，俯仰姿态
            冻结1.0神经网络参数，开始训练对于自身状态评估的神经网络结构和融合网络的参数，
            使得生成更好的网络决策结果。
        神经网络输出：
        ==> 下一步的动作：加速，减速，左转，右转，左急转，右急转，拉升，无动作，主武器攻击，副武器攻击
            8 + 2 = 10
        """
        self.map_fc1 = nn.Linear(7, 32)
        self.map_fc2 = nn.Linear(32, 32)

        self.output_fc = nn.Linear(32, 10)  # 输出层，产生8种可能的动作

    def forward(self, input_data):
        x = F.relu(self.map_fc1(input_data.float()))  # 使用ReLU作为激活函数
        x = F.relu(self.map_fc2(x))
        output = self.output_fc(x)
        probabilities = F.softmax(output, dim=1)  # 使用softmax激活函数得到输出的概率
        return probabilities


# --------------------------------------- #
# 经验回放池
# --------------------------------------- #

class ReplayBuffer():
    def __init__(self, capacity):
        # 创建一个先进先出的队列，最大长度为capacity，保证经验池的样本量不变
        self.buffer = collections.deque(maxlen=capacity)

    # 将数据以元组形式添加进经验池
    def add(self, state, action, reward, next_state, done):
        self.buffer.append((state, action, reward, next_state, done))

    # 随机采样batch_size行数据
    def sample(self, batch_size):
        transitions = random.sample(self.buffer, batch_size)  # list, len=32
        # *transitions代表取出列表中的值，即32项
        state, action, reward, next_state, done = zip(*transitions)
        return np.array(state), action, reward, np.array(next_state), done

    # 目前队列长度
    def size(self):
        return len(self.buffer)


# -------------------------------------- #
# 构造深度强化学习模型
# -------------------------------------- #

class DQN:
    # （1）初始化
    def __init__(self, n_states, n_hidden, n_actions,
                 learning_rate, gamma, epsilon,
                 target_update, device):
        # 属性分配
        self.n_states = n_states  # 状态的特征数
        self.n_hidden = n_hidden  # 隐含层个数
        self.n_actions = n_actions  # 动作数
        self.learning_rate = learning_rate  # 训练时的学习率
        self.gamma = gamma  # 折扣因子，对下一状态的回报的缩放
        self.epsilon = epsilon  # 贪婪策略，有1-epsilon的概率探索
        self.target_update = target_update  # 目标网络的参数的更新频率
        self.device = device  # 在GPU计算
        # 计数器，记录迭代次数
        self.count = 0

        # 构建2个神经网络，相同的结构，不同的参数
        # 实例化训练网络  [b,4]-->[b,2]  输出动作对应的奖励
        self.q_net = AIAircraftNet()
        # 实例化目标网络
        self.target_q_net = AIAircraftNet()

        # 优化器，更新训练网络的参数
        self.optimizer = torch.optim.Adam(self.q_net.parameters(), lr=self.learning_rate)

    # （3）网络训练
    def update(self, transition_dict):  # 传入经验池中的batch个样本
        # 获取当前时刻的状态 array_shape=[b,4]
        states = torch.tensor(transition_dict['states'], dtype=torch.float)
        # 获取当前时刻采取的动作 tuple_shape=[b]，维度扩充 [b,1]
        actions = torch.tensor(transition_dict['actions']).view(-1, 1)
        # 当前状态下采取动作后得到的奖励 tuple=[b]，维度扩充 [b,1]
        rewards = torch.tensor(transition_dict['rewards'], dtype=torch.float).view(-1, 1)
        # 下一时刻的状态 array_shape=[b,4]
        next_states = torch.tensor(transition_dict['next_states'], dtype=torch.float)
        # 是否到达目标 tuple_shape=[b]，维度变换[b,1]
        dones = torch.tensor(transition_dict['dones'], dtype=torch.float).view(-1, 1)

        # 输入当前状态，得到采取各运动得到的奖励 [b,4]==>[b,2]==>[b,1]
        # 根据actions索引在训练网络的输出的第1维度上获取对应索引的q值（state_value）
        q_values = self.q_net(states).gather(1, actions)  # [b,1]
        # 下一时刻的状态[b,4]-->目标网络输出下一时刻对应的动作q值[b,2]-->
        # 选出下个状态采取的动作中最大的q值[b]-->维度调整[b,1]
        max_next_q_values = self.target_q_net(next_states).max(1)[0].view(-1, 1)
        # 目标网络输出的当前状态的q(state_value)：即时奖励+折扣因子*下个时刻的最大回报
        q_targets = rewards + self.gamma * max_next_q_values * (1 - dones)

        # 目标网络和训练网络之间的均方误差损失
        dqn_loss = torch.mean(F.mse_loss(q_values, q_targets))
        # PyTorch中默认梯度会累积,这里需要显式将梯度置为0
        self.optimizer.zero_grad()
        # 反向传播参数更新
        dqn_loss.backward()
        # 对训练网络更新
        self.optimizer.step()

        # 在一段时间后更新目标网络的参数
        if self.count % self.target_update == 0:
            # 将目标网络的参数替换成训练网络的参数
            self.target_q_net.load_state_dict(
                self.q_net.state_dict())

        self.count += 1


if __name__ == '__main__':
    # ------------------------------- #
    # 全局变量
    # ------------------------------- #

    capacity = 500  # 经验池容量
    lr = 2e-3  # 学习率
    gamma = 0.9  # 折扣因子
    epsilon = 0.9  # 贪心系数
    target_update = 200  # 目标网络的参数的更新频率
    batch_size = 32
    n_hidden = 128  # 隐含层神经元个数
    min_size = 200  # 经验池超过200后再训练
    return_list = []  # 记录每个回合的回报
    n_states = 7
    n_actions = 10
    env = None

    # 实例化经验池
    replay_buffer = ReplayBuffer(capacity)
    # 实例化DQN
    agent = DQN(n_states=n_states,
                n_hidden=n_hidden,
                n_actions=n_actions,
                learning_rate=lr,
                gamma=gamma,
                epsilon=epsilon,
                target_update=target_update,
                device='cpu'
                )

    # 训练模型
    for i in range(500):  # 100回合
        # 每个回合开始前重置环境
        state = env.reset()[0]  # len=4
        # 记录每个回合的回报
        episode_return = 0
        done = False

        # 打印训练进度，一共10回合
        with tqdm(total=10, desc='Iteration %d' % i) as pbar:

            while True:
                # 获取当前状态下需要采取的动作
                action = agent.take_action(state)
                # 更新环境
                next_state, reward, done, _, _ = env.step(action)
                # 添加经验池
                replay_buffer.add(state, action, reward, next_state, done)
                # 更新当前状态
                state = next_state
                # 更新回合回报
                episode_return += reward

                # 当经验池超过一定数量后，训练网络
                if replay_buffer.size() > min_size:
                    # 从经验池中随机抽样作为训练集
                    s, a, r, ns, d = replay_buffer.sample(batch_size)
                    # 构造训练集
                    transition_dict = {
                        'states': s,
                        'actions': a,
                        'next_states': ns,
                        'rewards': r,
                        'dones': d,
                    }
                    # 网络更新
                    agent.update(transition_dict)
                # 找到目标就结束
                if done: break

            # 记录每个回合的回报
            return_list.append(episode_return)

            # 更新进度条信息
            pbar.set_postfix({
                'return': '%.3f' % return_list[-1]
            })
            pbar.update(1)

    # 绘图
    episodes_list = list(range(len(return_list)))
    plt.plot(episodes_list, return_list)
    plt.xlabel('Episodes')
    plt.ylabel('Returns')
    plt.title('DQN Returns')
    plt.show()
