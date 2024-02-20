import os

import numpy as np
import copy
import torch
import torch.nn as nn

import torch
import torchvision
import torchvision.transforms as transforms

from utils.cls_dqn_agent import AIAircraftNet

"""
基于遗传算法的AI优化方案：
1. 初始化
    初始化过程在指定的位置创建对应的飞机和指向，然后开始AI决策
"""

class GeneticAlgorithm:
    def __init__(self, _pop_size=8, _r_mutation=0.1, _p_mutation=0.1):
        # input params
        self.pop_size = _pop_size       # 单次训练种群数量
        self.r_mutation = _r_mutation   #
        self.p_mutation = _p_mutation  # for generational
        # other params
        self.population = []            # 每次测试算法的人口总量
        self.evaluation_history = []    # 训练过程中比较好的历史记录
        self.stddev = 0.5
        self.criterion = nn.CrossEntropyLoss()
        self.model = None
        self.elite_num = 4
        self.mating_pool_size = 12
        self.generation = 0

    def selection(self, evaluation_result):
        self.generation += 1
        sorted_evaluation = sorted(evaluation_result, key=lambda x: x.score, reverse=True)
        max_score = sorted_evaluation[0].score
        # 首先选出最好的个体
        elites = [e.agent_network for e in sorted_evaluation[:self.elite_num]]
        # print('Elites: {}'.format(elites))
        children = elites
        if os.path.exists('pth') is False:
            os.makedirs('pth')

        # 把最好的个体参数保存下来
        for i, plane in enumerate(sorted_evaluation[:self.elite_num]):
            torch.save(plane.agent_network.state_dict(), 'pth/gen_{}_score_{:.2f}.pth'.format(self.generation, plane.score))

        # 然后选出较合格的父母
        mating_pool = np.array(
            [self.roulette_wheel_selection(evaluation_result) for _ in range(self.mating_pool_size)])
        mating_pool = mating_pool.reshape(-1)
        pairs = []
        # print('mating_pool')
        # print(mating_pool)
        # 生成所有不足的子代个体
        while len(children) < self.pop_size:
            pair = [np.random.choice(mating_pool) for _ in range(2)]
            pairs.append(pair)
            children.append(self.crossover(pair))
        # print('Pairs: {}'.format(pairs))
        # print('Cross over finished.')
        # 替换原来的种群个体
        self.replacement(children)
        for i in range(self.elite_num, self.pop_size):  # do not mutate elites
            if np.random.rand() < self.p_mutation:
                mutated_child = self.mutation(self.population[i])
                del self.population[i]
                self.population.insert(i, mutated_child)

        self.evaluation_history.append(max_score)
        print('generation: {}, max score: {}'.format(self.generation, max_score))
        return max_score

    def crossover(self, _selected_pop):
        if _selected_pop[0] == _selected_pop[1]:
            return copy.deepcopy(_selected_pop[0])

        chrom1 = copy.deepcopy(_selected_pop[0])
        chrom2 = copy.deepcopy(_selected_pop[1])

        chrom1_layers = list(chrom1.modules())
        chrom2_layers = list(chrom2.modules())

        child_net = copy.deepcopy(_selected_pop[0])
        # 遍历神经网络的层，逐层交叉参数
        for name, param1 in dict(_selected_pop[1].named_parameters()).items():
            # parts = name_ori.rsplit('_', 1)  # 从后往前以第一个'_'为分隔符拆分字符串
            # name = '.'.join(parts)
            param2 = dict(_selected_pop[1].named_parameters())[name]

            # 判断参数是否需要交叉
            if param1.size() == param2.size():
                # 随机选择两个父网络的参数
                child_param = param1 if np.random.rand() < 0.5 else param2
                # 将交叉后的参数赋值给子代网络
                setattr(child_net, name.replace(".", "_"), nn.Parameter(child_param.data.clone()))

        return child_net

    def mutation(self, _selected_pop):
        mutated_net = copy.deepcopy(_selected_pop)

        for name, param in dict(_selected_pop.named_parameters()).items():
            # 判断是否进行变异
            if torch.rand(1) < self.r_mutation:
                # 生成一个与原参数同样形状的随机扰动
                noise = torch.randn_like(param) * self.stddev
                # 创建一个新的变异参数
                mutated_param = nn.Parameter(param.data + noise)
            else:
                # 使用未变异的参数
                mutated_param = param
            # 将变异后的参数赋值给mutated_net
            setattr(mutated_net, name.replace(".", "_"), mutated_param)

        return mutated_net


    def replacement(self, _child):
        self.population[:] = _child
        print('Replacement finished.')

    def roulette_wheel_selection(self, evaluation_result):
        # sorted_evaluation = sorted(evaluation_result, key=lambda x: x.score)
        # cum_acc = np.array([e['train_acc'] for e in sorted_evaluation]).cumsum()
        # extra_evaluation = [{'pop': e['pop'], 'train_acc': e['train_acc'], 'cum_acc': acc}
        #                     for e, acc in zip(sorted_evaluation, cum_acc)]
        # rand = np.random.rand() * cum_acc[-1]
        # for e in extra_evaluation:
        #     if rand < e['cum_acc']:
        #         return e['pop']
        # return extra_evaluation[-1]['pop']

        # 计算每个个体的适应度（假设fitness_list为适应度列表，包含每个个体的适应度分数）
        fitness_list = [individual.score for individual in evaluation_result]
        # 找到概率列表中的最小值
        min_fitness = min(fitness_list)
        # 将概率列表中的所有值加上最小值的绝对值，确保所有概率值为非负数
        adjusted_fitness_list = [fitness + abs(min_fitness) for fitness in fitness_list]
        total_adjusted_fitness = sum(adjusted_fitness_list)
        # 计算调整后的概率
        selection_probabilities = [fitness / total_adjusted_fitness for fitness in adjusted_fitness_list]
        # 使用俄罗斯轮盘赌算法选择父母个体
        # 此处实现俄罗斯轮盘赌算法选择父母的逻辑
        selected_parent = np.random.choice(evaluation_result, p=selection_probabilities)
        # 获取被选择的父母个体的agent_network属性
        selected_agent_network = selected_parent.agent_network
        # 将agent_network属性组合成一个新的列表
        new_list = [selected_agent_network]
        # 返回新的列表
        return new_list

