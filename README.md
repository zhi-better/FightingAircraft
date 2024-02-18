# FightingAircraft

## 游戏玩法

1. 地图设计：

   地图设计采用的是开放性地图，玩家到达一个地图边界的时候会从对向重新进入地图
2. 战机分类

   游戏的飞机主要分为三种类型：战斗机、攻击机、轰炸机和侦察机，主要玩法如下：

   **战斗机：**

   战斗机主要用于空战格斗，主武器为4管或者2管机炮，副武器为2管机枪，具有四个挂载位置，可以挂载对空或者对地导弹，对空导弹具有一定的追踪能力，是空战格斗的大杀器，对地导弹对于地面不动的物体具有良好的打击能力，发射具有一定锁定时间，针对移动的物体需要做好提前预判。

   **攻击机：**

   攻击机主要用于高精度地面物体打击，主武器为双管机炮，副武器为携带的400kg航弹，单次载弹量为2发，对于地面目标具有强大的打击能力，针对地面移动目标也具有很高的打击精度；在面对水上目标的时候还可以灵活的将航弹切换为鱼雷，给与水上舰艇致命的一击。

   **轰炸机：**

   轰炸机主要针对大范围密集程度较高的地方建筑群实施打击，主武器为单管机枪，机枪可以旋转实现360度的打击，副武器为炸弹，炸弹可以将经过区域内的建筑物化为一片废墟；轰炸机带有一定数量的干扰弹用于干扰敌方导弹袭击，没有战斗机的护航最好不要单独出现在战场。

   **侦察机：**

   侦察机和其他战机不同，更着重于战场侦察和呼叫远程火力打击，主武器为双管机枪，副武器为传单炮，副武器可以实现对目标区域内敌军的压制，降低附近区域内防空炮等火力的攻击精度和攻击间隔；具有特殊技能，可以标记目标地点，一段时间后目标地点将会遭遇我方远程火炮的密集打击。


3. 防空火力分类

   防空火力主要分为三种：低射速高射炮，高射速高射炮，舰载高射炮

   **低射速高射炮：**

   该类型高射炮的初速快，射速较慢，主要利用破片对目标区域飞行单位进行杀伤。

   **高射速高射炮：**

   该类型高射炮初速较慢，但是射击频率更高，可以短时间内形成火力弹幕，干扰敌方单位的正常攻击，另外也可以对近程目标造成有效杀伤。

   **舰载高射炮：**

   该类型高射炮通常会集群出现在战舰上，除非迫不得已，不然不要轻易去挑战它，尽量使用鱼雷等武器在较远的地方对战舰进行攻击。

4. 基地分类

   **机场（航母）：**

   基地可以为附近的己方飞机提供防御力加成，机场附近一般会有比较完备的防空火力，飞机可以在机场降落补给生命值并重新装填弹药。

4. 任务设计


5. AI设计

**普通AI：**
    适合于1V1对战,只能根据目标飞机的位置来调整自己的攻击和移动手段,


### 2023年12月16日

**FightingAircraft v1.01**

1. 实现了飞机机动动作和姿态的配合
2. 机动动作包括左转、右转、左右急转、横滚、翻转
3. 实现了机动动作和发动机温度的动态变化
4. 优化了代码框架结构

### 2023年12月11日

**FightingAircraft v1.00**

1. 实现了地图根据飞机视角动态加载
2. 实现了飞机的飞行加减速及转向控制
3. 实现了发动机温度随着转向和加减速的动态变化
