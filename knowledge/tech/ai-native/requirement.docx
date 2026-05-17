# **AI Native 平台度量实战考试**

## **一、 考试目标与范围**

利用 AI 辅助编程，在 8小时内 独立完成 AI Native 平台度量 的 1:1 全流程复刻。模拟完整的端到端研发生命周期：**需求分析** ➔ **架构设计** ➔ **编码实现** ➔ **测试验证** ➔ **发布**。

**【核心要求】**

**1. 1:1 精准复刻：**功能、UI 布局与交互逻辑需与原平台一致（无需在意配色）

**2. 研发内网合规：全程仅限使用考试指定 Key，系统将自动计算每位提交代码的“硅基含量”，匹配度小的示为违规**

## **二、 环境与资源前置说明**

### **1. 目标平台地址（复刻原型）**

平台入口：http://10.65.134.124:8080/metrics

### **2. 数据源（无密码，只读）**

考试提供了**预构建的 Elasticsearch 数据集**，无需你手动处理数据，你可以直接作为系统数据库。

**注意：ES数据中存在脏数据，需要过滤处理，数据库只读，性能满足项目要求**

| **服务** | **地址** | **用途** |
| --- | --- | --- |
| ES 数据库 | [http://10.65.134.124:8200](http://10.65.134.124:8200/) | 存储所有研发数据 |
| Kibana | http://10.65.134.124:8601/app/dev_tools#/console | 数据结构查看与调试 |

### **3. 核心数据结构（ES 索引）**

**（1）需要对接的三个ES索引**

| **索引** | **关键字段描述** | **备注** |
| --- | --- | --- |
| 团队组织架构：
hrm_user | ● nameid（姓名工号格式用户名， **存在重复**）
● zhilei（职类），
● comp_name：深信服或信锐
● user_status：在职、离职
● dept_1：1级部门，如研发体系
● dept_2：2级部门，如终端安全产品研发部
● dept_3：3级部门
● dept_4：4级部门 | 记录组织结构与用户信息 |
| Token使用量：
ai_token_usage | 每条数据记一次请求，一次请求的数据关键字段
● total_tokens：总Token量
● completion_tokens：响应token
● total_price：费用（**-1表示请求当前请求是失败的**）
● username：用户名称，姓名工号格式
● request_time：请求时间（北京时间） | 记录用户的模型调用与消费明细情况 |
| 硅基含量：
commits_ai_code
 | ● gitlab_key：仓库地区
● repo：仓库地址
● committer_user：代码提交用户，姓名工号格式
● commit_at：代码提交时间
● file_ai_code_match_lines：本次提交硅基代码行数
● diff_lines：本次提交增量代码行数 | 基于代码提交记录，度量 AI 代码渗透程度。
 |

**（2）职类映射关系**

| **职类** | **es 中字段：**zhilei （职类） |
| --- | --- |
| 开发类 | 开发类、软件开发类 |
| 测试类 | 测试类 |
| 其它类 | 排除开发类、软件开发类、测试类 |

### **4. 代码仓库与开发规范**

● 初始模板：git@git.sangfor.com:ai-native/ai-native-cp.git

● 开发分支：克隆后请**基于master分支**创建个人分支，**命名规范：feature-{用户名+工号} (例：feature-李云60604)**。

● 部署配置：项目内置 docker-compose.yml。

● git提交提交：必须使用自己的git账号，使用git config --list 命令查看。例如 user.name=李洋60603 ，user.email=60603@sangfor.com。如果不正确，使用git config 命令设置：

*git config --global user.name "李洋60603"*

*git config --global user.email "60603@sangfor.com"*

**（注意）若非必须，请勿修改。如必须修改，请强制保留以下 6 个环境变量，以确保自动化部署通过**

| **环境变量** | **说明** |
| --- | --- |
| BACKEND_IMAGE | 后端镜像名 |
| BACKEND_HOST_PORT | 后端服务对外端口 |
| BACKEND_CONTAINER_NAME | 后端容器名称 |
| FRONTEND_IMAGE | 前端镜像名 |
| FRONTEND_HOST_PORT | 前端服务对外端口 |
| FRONTEND_CONTAINER_NAME | 前端容器名 |

### **5. 编译环境（Docker构建）**

我们以提供了已经配置好的镜像源的Docker构建环境，解决在研发内网测试Build Docker镜像的问题。

| **服务器信息** | **备注** |
| --- | --- |
| 服务器地址：10.65.209.128
账号密码：root / Sangfor@123 | 推荐这个，配置高，性能强 |
| 服务器地址：10.74.84.10
账号密码：root / Sangfor@123 | 备选使用 |

**注意：如在自己的开发环境构建，请参考** https://mirrors.sangfor.com/ **相关软件/镜像源配置。**

### **6. 自测工具包（可选）**

安装本地自测 Skill，方便开发过程中自我验证

● 灵测本地skills：npx ainative@latest install skill http://code.sangfor.org/20036/qianliu-skills:qianliu-aitest-local

● Agent-Browser：npx ainative@latest install skill https://git.sangfor.com/84713/skills:agent-browser

● webapp-testing：npx ainative@latest install skill http://code.sangfor.org/87713/qianliu-external-ai-hub:webapp-testing

### **7. 提交与发布**

● **代码提交验证（可以多次提交）：**将代码推送至个人分支，千流平台会自动对你的分支进行构建验证，如果构建失败你将会在Dim、企微的小助理、邮箱3个渠道收到通知（成功不会通知，失败会通知），点击流水线地址可以查看失败的日志详情，帮助调试你的构建部署代码。

[](https://wdcdn.qpic.cn/MTY4ODg1NDMwODQxMDA2Mg_874319_JIK_FO58VAQ8i9oJ_1776308131?w=774&h=164&type=image/png)

● **创建 Merge Request发布（注意：只允许一次，成绩以第一次为准）：**提交合并请求后，千流平台会触发自动化测试，并且提交评分。

## **三、 功能需求详情**

**请优先实现核心业务逻辑，再考虑边缘情况。**

### **1. Token 使用量分析**

分析研发人员在 AI 工具上的消耗成本，支持多维度下钻。

● 过滤维度：按团队、职类、时间范围、AI-Native 阈值过滤

● 核心指标：

○ AI Native 人数（注意：只有hrm_user中的人员才纳入统计）

○ Token 消耗总量

○ 请求总次数

○ 费用统计（人均费用 / 总费用）

● 视图层级：支持体系整体 ➔ 团队 ➔ 个人成员 的逐级钻取。

● 阈值定义：

○ AI-Native 用户：日均 Token 使用量 ≥ 100K tokens/天。

### **2. 硅基含量分析**

基于代码 Commit 数据，度量研发工作的“智能化”水平。

● 过滤维度：按团队、职类、时间范围、硅基阈值过滤（前端可配置）。

● 核心指标：

○ 硅基人员占比

○ 硅基代码占比

● 视图层级：支持体系整体 ➔ 团队 ➔ 个人成员 的逐级分析。

● 阈值定义：

○ 硅基人员：在统计周期内，个人的 AI 代码匹配行数 / 总代码行数 ≥ 设定阈值（默认 90%）

## **四、 非功能需求 (DFX)**

此部分决定系统能否通过DFX要求。

### **1. 性能 (Performance)：**

● 所有数据分析查询接口的响应时间 ≤ 3秒。

### **2. 安全 (Security)：**

● 严格进行入参校验，防止注入攻击。

● 保障敏感数据与接口的访问安全。

## **五、 基础自测案例（仅本地测试自测参考，IP改成本地测试主机）**

## **测试步骤**

1、 访问[http://localhost:80/metrics](http://10.65.134.124:8080/metrics)

2、 访问Token使用量页面

3、 访问硅含量页面

## **期望结果**

1、 页面正常打开，页面显示度量管理

2、 Token使用量页面支持按团队、职类、日期以及阈值过滤

3、 硅基含量页面包括硅基主导与硅基代码总量统计

# **AI Native 平台度量实战考试**

## **一、 考试目标与范围**

利用 AI 辅助编程，在 8小时内 独立完成 AI Native 平台度量 的 1:1 全流程复刻。模拟完整的端到端研发生命周期：**需求分析** ➔ **架构设计** ➔ **编码实现** ➔ **测试验证** ➔ **发布**。

**【核心要求】**

**1. 1:1 精准复刻：**功能、UI 布局与交互逻辑需与原平台一致（无需在意配色）

**2. 研发内网合规：全程仅限使用考试指定 Key，系统将自动计算每位提交代码的“硅基含量”，匹配度小的示为违规**

## **二、 环境与资源前置说明**

### **1. 目标平台地址（复刻原型）**

平台入口：http://10.65.134.124:8080/metrics

### **2. 数据源（无密码，只读）**

考试提供了**预构建的 Elasticsearch 数据集**，无需你手动处理数据，你可以直接作为系统数据库。

**注意：ES数据中存在脏数据，需要过滤处理，数据库只读，性能满足项目要求**

| **服务** | **地址** | **用途** |
| --- | --- | --- |
| ES 数据库 | [http://10.65.134.124:8200](http://10.65.134.124:8200/) | 存储所有研发数据 |
| Kibana | http://10.65.134.124:8601/app/dev_tools#/console | 数据结构查看与调试 |

### **3. 核心数据结构（ES 索引）**

**（1）需要对接的三个ES索引**

| **索引** | **关键字段描述** | **备注** |
| --- | --- | --- |
| 团队组织架构：
hrm_user | ● nameid（姓名工号格式用户名， **存在重复**）
● zhilei（职类），
● comp_name：深信服或信锐
● user_status：在职、离职
● dept_1：1级部门，如研发体系
● dept_2：2级部门，如终端安全产品研发部
● dept_3：3级部门
● dept_4：4级部门 | 记录组织结构与用户信息 |
| Token使用量：
ai_token_usage | 每条数据记一次请求，一次请求的数据关键字段
● total_tokens：总Token量
● completion_tokens：响应token
● total_price：费用（**-1表示请求当前请求是失败的**）
● username：用户名称，姓名工号格式
● request_time：请求时间（北京时间） | 记录用户的模型调用与消费明细情况 |
| 硅基含量：
commits_ai_code
 | ● gitlab_key：仓库地区
● repo：仓库地址
● committer_user：代码提交用户，姓名工号格式
● commit_at：代码提交时间
● file_ai_code_match_lines：本次提交硅基代码行数
● diff_lines：本次提交增量代码行数 | 基于代码提交记录，度量 AI 代码渗透程度。
 |

**（2）职类映射关系**

| **职类** | **es 中字段：**zhilei （职类） |
| --- | --- |
| 开发类 | 开发类、软件开发类 |
| 测试类 | 测试类 |
| 其它类 | 排除开发类、软件开发类、测试类 |

### **4. 代码仓库与开发规范**

● 初始模板：git@git.sangfor.com:ai-native/ai-native-cp.git

● 开发分支：克隆后请**基于master分支**创建个人分支，**命名规范：feature-{用户名+工号} (例：feature-李云60604)**。

● 部署配置：项目内置 docker-compose.yml。

● git提交提交：必须使用自己的git账号，使用git config --list 命令查看。例如 user.name=李洋60603 ，user.email=60603@sangfor.com。如果不正确，使用git config 命令设置：

*git config --global user.name "李洋60603"*

*git config --global user.email "60603@sangfor.com"*

**（注意）若非必须，请勿修改。如必须修改，请强制保留以下 6 个环境变量，以确保自动化部署通过**

| **环境变量** | **说明** |
| --- | --- |
| BACKEND_IMAGE | 后端镜像名 |
| BACKEND_HOST_PORT | 后端服务对外端口 |
| BACKEND_CONTAINER_NAME | 后端容器名称 |
| FRONTEND_IMAGE | 前端镜像名 |
| FRONTEND_HOST_PORT | 前端服务对外端口 |
| FRONTEND_CONTAINER_NAME | 前端容器名 |

### **5. 编译环境（Docker构建）**

我们以提供了已经配置好的镜像源的Docker构建环境，解决在研发内网测试Build Docker镜像的问题。

| **服务器信息** | **备注** |
| --- | --- |
| 服务器地址：10.65.209.128
账号密码：root / Sangfor@123 | 推荐这个，配置高，性能强 |
| 服务器地址：10.74.84.10
账号密码：root / Sangfor@123 | 备选使用 |

**注意：如在自己的开发环境构建，请参考** https://mirrors.sangfor.com/ **相关软件/镜像源配置。**

### **6. 自测工具包（可选）**

安装本地自测 Skill，方便开发过程中自我验证

● 灵测本地skills：npx ainative@latest install skill http://code.sangfor.org/20036/qianliu-skills:qianliu-aitest-local

● Agent-Browser：npx ainative@latest install skill https://git.sangfor.com/84713/skills:agent-browser

● webapp-testing：npx ainative@latest install skill http://code.sangfor.org/87713/qianliu-external-ai-hub:webapp-testing

### **7. 提交与发布**

● **代码提交验证（可以多次提交）：**将代码推送至个人分支，千流平台会自动对你的分支进行构建验证，如果构建失败你将会在Dim、企微的小助理、邮箱3个渠道收到通知（成功不会通知，失败会通知），点击流水线地址可以查看失败的日志详情，帮助调试你的构建部署代码。

[](https://wdcdn.qpic.cn/MTY4ODg1NDMwODQxMDA2Mg_874319_JIK_FO58VAQ8i9oJ_1776308131?w=774&h=164&type=image/png)

● **创建 Merge Request发布（注意：只允许一次，成绩以第一次为准）：**提交合并请求后，千流平台会触发自动化测试，并且提交评分。

## **三、 功能需求详情**

**请优先实现核心业务逻辑，再考虑边缘情况。**

### **1. Token 使用量分析**

分析研发人员在 AI 工具上的消耗成本，支持多维度下钻。

● 过滤维度：按团队、职类、时间范围、AI-Native 阈值过滤

● 核心指标：

○ AI Native 人数（注意：只有hrm_user中的人员才纳入统计）

○ Token 消耗总量

○ 请求总次数

○ 费用统计（人均费用 / 总费用）

● 视图层级：支持体系整体 ➔ 团队 ➔ 个人成员 的逐级钻取。

● 阈值定义：

○ AI-Native 用户：日均 Token 使用量 ≥ 100K tokens/天。

### **2. 硅基含量分析**

基于代码 Commit 数据，度量研发工作的“智能化”水平。

● 过滤维度：按团队、职类、时间范围、硅基阈值过滤（前端可配置）。

● 核心指标：

○ 硅基人员占比

○ 硅基代码占比

● 视图层级：支持体系整体 ➔ 团队 ➔ 个人成员 的逐级分析。

● 阈值定义：

○ 硅基人员：在统计周期内，个人的 AI 代码匹配行数 / 总代码行数 ≥ 设定阈值（默认 90%）

## **四、 非功能需求 (DFX)**

此部分决定系统能否通过DFX要求。

### **1. 性能 (Performance)：**

● 所有数据分析查询接口的响应时间 ≤ 3秒。

### **2. 安全 (Security)：**

● 严格进行入参校验，防止注入攻击。

● 保障敏感数据与接口的访问安全。

## **五、 基础自测案例（仅本地测试自测参考，IP改成本地测试主机）**

## **测试步骤**

1、 访问[http://localhost:80/metrics](http://10.65.134.124:8080/metrics)

2、 访问Token使用量页面

3、 访问硅含量页面

## **期望结果**

1、 页面正常打开，页面显示度量管理

2、 Token使用量页面支持按团队、职类、日期以及阈值过滤

3、 硅基含量页面包括硅基主导与硅基代码总量统计