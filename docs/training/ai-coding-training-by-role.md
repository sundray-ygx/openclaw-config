# 校招新员工AI Coding入职培训方案（按岗位分类）

> **版本**: v3.0  
> **适用对象**: 校招入职各岗位新员工（软件开发/测试/前端/硬件）  
> **执行周期**: 5个工作日  
> **评审方式**: 代码审查 + 10分钟演示  
> **特别说明**: 所有课题均为纯软件实现，无需额外硬件器件

---

## 一、培训目标

1. **掌握SDD规范驱动编程**: 理解并实践OpenSpec框架的完整流程
2. **熟练使用AI Coding工具**: 能够高效使用Claude/Codex等AI助手进行开发
3. **建立工程化思维**: 从需求分析到验收测试的完整闭环
4. **快速融入团队**: 熟悉团队的代码规范和工作流程

---

## 二、SDD流程规范（基于OpenSpec）

### 2.1 流程概览

```
Day 1          Day 2          Day 3          Day 4          Day 5
├─────────────┼─────────────┼─────────────┼─────────────┼─────────────┤
│  Proposal   │   Specs     │   Design    │ Implement   │  Verify     │
│   + Specs   │   (完善)     │   + Tasks   │   (编码)     │   + Demo    │
└─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘
```

### 2.2 各阶段交付物

| 阶段 | 交付文件 | 关键要求 |
|------|----------|----------|
| **Proposal** | `proposal.md` | 背景、目标、范围、验收标准 |
| **Specs** | `specs/*.md` | Given/When/Then格式，覆盖正常+异常场景 |
| **Design** | `design.md` | 架构图、模块划分、接口定义、技术选型 |
| **Tasks** | `tasks.md` | 原子任务列表，可勾选追踪 |
| **Implementation** | 源代码 + Git历史 | 按Task提交，commit message规范 |
| **Verification** | 测试报告 + 运行截图 | 测试通过率≥80%，核心功能演示 |

### 2.3 OpenSpec初始化命令

```bash
# 1. 安装OpenSpec CLI
npm install -g @fission-ai/openspec@latest

# 2. 在项目目录初始化
cd your-project
openspec init --tools claude

# 3. 创建变更
openspec new change feature-xxx

# 4. 按提示创建各阶段文档
openspec instructions --change feature-xxx
```

---

## 三、硬件研发工程师课题（3个）

> **说明**: 硬件课题采用软件仿真方式，通过模拟器/虚拟机实现，无需额外硬件器件

### HW-01: 基于Arduino框架的虚拟开发板入门
**难度**: ⭐
**技术栈**: C/C++ (Arduino语法) + QEMU (模拟STM32/AVR) + 虚拟串口工具

**核心功能**:
1. 搭建QEMU虚拟Arduino开发板（如STM32F103或Arduino Uno）
2. 用`digitalWrite()`/`analogWrite()`实现LED呼吸灯效果
3. 用`random()`模拟温度传感器数据，通过`Serial.print()`输出到虚拟串口
4. 实现简单逻辑："温度>30℃时LED快闪，否则慢闪"
5. 用QEMU+GDB单步调试，观察变量变化

**学习要点**:
- 嵌入式开发环境搭建（交叉编译、QEMU启动参数）
- Arduino框架下的GPIO/串口/定时器基础使用
- 基本的状态机逻辑（if-else/switch-case实现）
- 仿真环境下的调试方法（断点、变量查看）

**软件环境**:
- QEMU for Arduino (预配置好的虚拟开发板镜像)
- Arduino CLI 或 PlatformIO (简化编译流程)
- 虚拟串口监视器 (如PuTTY或Arduino IDE自带串口监视器)

**Specs示例**:
```markdown
### Requirement: 温度监控与LED指示
The system SHALL 模拟温度采集并根据温度控制LED

#### Scenario: 正常温度模式
- GIVEN QEMU虚拟开发板已启动
- WHEN 模拟温度为25℃ (<=30℃)
- THEN LED每1000ms切换一次状态
- AND 串口输出: "Temperature: 25.0 C, LED: Slow Blink"

#### Scenario: 高温报警模式
- GIVEN QEMU虚拟开发板已启动
- WHEN 模拟温度为35℃ (>30℃)
- THEN LED每200ms切换一次状态
- AND 串口输出: "Temperature: 35.0 C, LED: Fast Blink"
```

---

### HW-02: 基础外设驱动的单元测试入门
**难度**: ⭐⭐
**技术栈**: C (基础语法) + Unity测试框架 + Python辅助脚本 + 软件仿真

**核心功能**:
1. 编写两个基础驱动：`led_driver.c` (控制LED开关) 和 `button_driver.c` (读取按键状态)
2. 用Unity框架写单元测试：验证"调用led_on()时LED状态为1"等基础逻辑
3. 用Python脚本模拟"按键按下/释放"信号，注入到驱动中
4. 生成简单的测试报告（通过/失败统计）
5. *选做：用gcov查看代码覆盖率（仅要求覆盖核心函数）*

**学习要点**:
- 硬件驱动的基本结构（初始化、读写函数）
- 单元测试的核心概念（测试用例、断言）
- 简单的"信号注入"思想（用全局变量/函数参数模拟硬件输入）
- 测试报告的阅读与分析

**软件环境**:
- Unity测试框架 (单文件集成，无需复杂构建)
- GCC编译器 (本地编译即可，无需交叉编译)
- Python 3.x (用于生成测试输入数据)

**Specs示例**:
```markdown
### Requirement: LED驱动测试
The system SHALL 验证LED驱动的基本功能

#### Scenario: 打开LED
- GIVEN LED驱动已初始化
- WHEN 调用 led_on() 函数
- THEN 读取 LED状态变量 应为 1
- AND 测试用例通过

#### Scenario: 关闭LED
- GIVEN LED驱动已初始化
- WHEN 调用 led_off() 函数
- THEN 读取 LED状态变量 应为 0
- AND 测试用例通过
```

---

### HW-03: 基于lwIP的简单网络通信
**难度**: ⭐⭐⭐
**技术栈**: C (基础网络编程) + lwIP (轻量级IP栈) + QEMU虚拟网卡 + Wireshark

**核心功能**:
1. 用QEMU搭建带虚拟TAP网卡的虚拟开发板，连接到宿主机
2. 基于lwIP的`socket API`，实现一个简单的UDP客户端
3. 客户端向宿主机发送"Hello from Embedded!"字符串
4. 用Wireshark捕获虚拟网卡的数据包，分析UDP/IP头
5. *选做：实现ARP请求的观察（用Wireshark看ARP交互过程）*

**学习要点**:
- 网络分层的基本概念（链路层、IP层、传输层）
- lwIP的基础配置（网卡初始化、IP地址设置）
- Socket API的基本使用（socket()、sendto()、close()）
- 用Wireshark分析简单网络数据包的能力

**软件环境**:
- lwIP (预移植好的QEMU版本，只需修改应用层代码)
- QEMU with TAP/TUN支持 (宿主机需配置虚拟网卡)
- Wireshark (用于抓包分析)

**Specs示例**:
```markdown
### Requirement: UDP数据发送
The system SHALL 通过虚拟网卡发送UDP数据包

#### Scenario: 发送字符串
- GIVEN 虚拟网卡已配置 (IP: 192.168.1.10)
- AND 宿主机UDP服务端已启动 (IP: 192.168.1.1, Port: 8888)
- WHEN 调用 send_udp_message() 函数
- THEN 宿主机收到字符串: "Hello from Embedded!"
- AND Wireshark能捕获到源IP为192.168.1.10的UDP数据包
```

---

## 四、软件测试工程师课题（2个）

> **说明**: 测试课题均为纯软件实现，无需专业测试仪器

### QA-01: API自动化测试框架
**难度**: ⭐⭐  
**技术栈**: Python/Node.js + HTTP客户端 + YAML/JSON

**核心功能**:
- YAML/JSON格式的测试用例定义
- 支持环境变量和参数化
- 断言库（状态码、响应体、响应时间、JSON Schema）
- 测试套件组织和并发执行
- HTML/JSON测试报告生成
- 支持测试数据驱动（CSV/Excel）

**学习要点**:
- 测试框架架构设计
- 声明式配置解析
- HTTP客户端封装
- 并发测试执行
- 报告生成与可视化

**软件环境**:
- Python + pytest/requests
- 或 Node.js + jest/axios

**Specs示例**:
```markdown
### Requirement: 测试用例执行
The system SHALL 按顺序执行测试用例集

#### Scenario: 执行通过
- GIVEN 测试用例文件有效
- WHEN 执行测试
- THEN 所有断言通过
- AND 生成成功报告

#### Scenario: 断言失败
- GIVEN 测试用例定义
- WHEN 实际响应不符合预期
- THEN 标记用例失败
- AND 记录实际值与期望值
```

---

### QA-02: 自动化UI测试工具
**难度**: ⭐⭐⭐  
**技术栈**: Python/Node.js + Playwright/Puppeteer

**核心功能**:
- 基于无头浏览器的UI自动化
- 元素定位与操作（点击/输入/等待）
- 截图对比测试（视觉回归）
- 测试步骤录制与回放
- 并行执行与报告生成

**学习要点**:
- 浏览器自动化原理
- 元素定位策略
- 异步等待机制
- 视觉测试基础
- 测试稳定性保障

**软件环境**:
- Playwright/Puppeteer
- 无头Chrome/Firefox

**Specs示例**:
```markdown
### Requirement: 页面元素操作
The system SHALL 自动化操作Web页面

#### Scenario: 表单提交
- GIVEN 测试页面已加载
- WHEN 填写表单并提交
- THEN 验证提交成功提示
- AND 截图保存测试结果
```

---

## 五、前端开发工程师课题（1个）

### FE-01: 低代码表单设计器
**难度**: ⭐⭐⭐  
**技术栈**: React/Vue + TypeScript + 拖拽库 + JSON Schema

**核心功能**:
- 可视化拖拽组件到画布
- 组件属性配置面板
- 表单验证规则配置
- 实时预览功能
- JSON Schema导入/导出
- 自定义组件注册机制

**学习要点**:
- 拖拽交互实现
- 组件化设计
- JSON Schema规范
- 动态表单渲染
- 配置驱动开发

**Specs示例**:
```markdown
### Requirement: 拖拽设计
The system SHALL 支持拖拽组件设计表单

#### Scenario: 添加输入框
- GIVEN 组件库显示"输入框"
- WHEN 拖拽到画布
- THEN 画布显示输入框组件
- AND 可配置其属性
```

---

## 六、软件开发工程师课题（11个）

### 后端基础（4个）

#### SD-01: RESTful任务管理API
**难度**: ⭐⭐  
**技术栈**: Python(FastAPI)/Node.js(Express) + SQLite

**核心功能**:
- 任务的增删改查（CRUD）
- 多条件过滤（状态、优先级、时间）
- 分页和排序
- 数据验证和错误处理
- API文档自动生成（OpenAPI/Swagger）

**学习要点**:
- RESTful API设计
- 数据库ORM操作
- 数据验证机制
- API版本管理

---

#### SD-02: 轻量级Key-Value数据库
**难度**: ⭐⭐⭐  
**技术栈**: Python/Go/Rust

**核心功能**:
- 内存/文件存储引擎
- B+树索引实现
- 基础CRUD操作
- 事务支持（ACID）
- WAL日志机制

**学习要点**:
- 存储引擎设计
- B+树算法
- 事务实现
- 崩溃恢复

---

#### SD-03: 分布式缓存系统
**难度**: ⭐⭐⭐  
**技术栈**: Python/Go

**核心功能**:
- LRU淘汰策略
- TCP服务器实现
- 自定义协议设计
- 一致性哈希分片
- 主从复制（简化版）

**学习要点**:
- 缓存淘汰算法
- 分布式哈希
- 网络协议设计
- 数据一致性

---

#### SD-04: 消息队列实现
**难度**: ⭐⭐⭐  
**技术栈**: Python/Go

**核心功能**:
- Topic/Queue模型
- 消息持久化存储
- 发布订阅模式
- 消费者组（负载均衡）
- 消息确认机制

**学习要点**:
- 消息队列模型
- 顺序写优化
- 消费offset管理
- 高可用设计

---

### 工具开发（4个）

#### SD-05: 智能Git提交助手
**难度**: ⭐⭐  
**技术栈**: Python/Node.js + Git命令 + LLM API

**核心功能**:
- 读取git diff/staged changes
- 调用LLM生成符合Conventional Commits规范的message
- 支持交互式编辑确认
- 支持自定义prompt模板
- 提交历史分析

**学习要点**:
- 命令行工具开发
- Git命令行操作
- LLM API调用
- 交互式CLI设计

---

#### SD-06: CSV数据清洗工具
**难度**: ⭐⭐  
**技术栈**: Python(pandas)/Node.js

**核心功能**:
- 自动检测编码、分隔符
- 数据类型自动推断和转换
- 缺失值处理策略
- 数据验证规则配置
- 输出清洗报告

**学习要点**:
- 数据处理能力
- 文件编码处理
- 数据质量规则
- 报告生成

---

#### SD-07: 日志分析工具
**难度**: ⭐⭐⭐  
**技术栈**: Python/Node.js

**核心功能**:
- 常见日志格式解析（Apache/Nginx/自定义）
- 按时间/级别/关键词过滤
- 聚合统计（PV/UV/错误率）
- 大文件流式处理
- 输出摘要报告

**学习要点**:
- 日志解析技术
- 流式处理
- 数据统计分析
- 正则表达式

---

#### SD-08: API Mock服务器
**难度**: ⭐⭐⭐  
**技术栈**: Node.js(Express)/Python(FastAPI)

**核心功能**:
- JSON/YAML格式的API定义
- 自动生成路由和响应
- 动态数据生成（faker）
- 请求验证和延迟模拟
- 响应模板配置

**学习要点**:
- Mock服务原理
- 动态数据生成
- API设计
- 前后端联调

---

### 系统与网络（4个）

#### SD-09: 任务调度系统
**难度**: ⭐⭐⭐  
**技术栈**: Python/Go

**核心功能**:
- Cron表达式解析
- 任务调度引擎（时间轮）
- 任务执行器（多语言支持）
- 失败重试机制
- 执行日志与监控

**学习要点**:
- 调度算法
- 时间轮实现
- 分布式锁
- 任务编排

---

#### SD-10: 文件同步工具
**难度**: ⭐⭐⭐  
**技术栈**: Python/Go/Rust

**核心功能**:
- 文件指纹计算（MD5/SHA256）
- 增量同步算法
- 断点续传
- 冲突检测与解决
- 并发传输优化

**学习要点**:
- 差异算法
- 网络传输
- 并发控制
- 数据一致性

---

#### SD-11: 简易负载均衡器
**难度**: ⭐⭐⭐⭐  
**技术栈**: Python/Go

**核心功能**:
- 四层/七层代理
- 负载算法（轮询/最少连接/哈希）
- 健康检查机制
- 会话保持
- 动态配置更新

**学习要点**:
- 反向代理原理
- 负载均衡算法
- 健康检查设计
- 高性能网络编程

---

#### SD-12: 配置管理中心
**难度**: ⭐⭐⭐  
**技术栈**: Python/Go + 数据库

**核心功能**:
- 应用/环境/配置分组管理
- 配置版本历史
- 灰度发布策略
- 实时配置推送
- 多语言SDK

**学习要点**:
- 配置管理模型
- 版本控制
- 灰度策略
- 实时推送机制

---

## 七、课题选择指南

### 7.1 按岗位推荐

#### 硬件研发工程师（纯软件仿真）
| 推荐排序 | 课题 | 难度 | 理由 |
|---------|------|------|------|
| 1 | HW-01 Arduino虚拟开发板 | ⭐ | 入门友好，快速上手 |
| 2 | HW-02 外设驱动单元测试 | ⭐⭐ | 测试思维培养，实用性强 |
| 3 | HW-03 lwIP网络通信 | ⭐⭐⭐ | 网络协议深度学习 |

**软件环境说明**:
- 仅需安装QEMU、交叉编译工具链、GDB
- 所有开发在Linux/Windows虚拟机中完成
- 无需传感器、显示屏、开发板等硬件

#### 软件测试工程师（纯软件）
| 推荐排序 | 课题 | 难度 | 理由 |
|---------|------|------|------|
| 1 | QA-01 API测试框架 | ⭐⭐ | 测试核心能力，通用性强 |
| 2 | QA-02 UI自动化测试 | ⭐⭐⭐ | 无头浏览器，无需测试仪 |

**软件环境说明**:
- 仅需Python/Node.js环境
- UI测试使用Playwright/Puppeteer（无头浏览器）
- 无需专业测试仪器（如Spirent/Ixia）

#### 前端开发工程师（纯软件）
| 推荐排序 | 课题 | 难度 | 理由 |
|---------|------|------|------|
| 1 | FE-01 表单设计器 | ⭐⭐⭐ | 组件化思维培养，配置驱动开发 |

#### 软件开发工程师（纯软件）
| 推荐排序 | 课题 | 难度 | 方向 |
|---------|------|------|------|
| 1 | SD-01 任务管理API | ⭐⭐ | RESTful API设计 |
| 2 | SD-05 Git提交助手 | ⭐⭐ | 实用工具开发 |
| 3 | SD-06 CSV数据清洗 | ⭐⭐ | 数据处理 |
| 4 | SD-08 API Mock服务 | ⭐⭐⭐ | 全栈开发 |
| 5 | SD-09 任务调度系统 | ⭐⭐⭐ | 系统设计 |
| 6 | SD-12 配置管理中心 | ⭐⭐⭐ | 微服务基础 |
| 7 | SD-03 分布式缓存 | ⭐⭐⭐ | 分布式入门 |

### 7.2 按基础水平推荐

| 基础水平 | 推荐课题 |
|---------|---------|
| 基础较弱 | QA-01, FE-01, SD-01, SD-05, SD-06, HW-01 |
| 基础中等 | QA-02, SD-04, SD-07, SD-08, SD-09, SD-10, HW-02 |
| 基础较好 | HW-03, SD-02, SD-03, SD-11, SD-12 |

### 7.3 按兴趣方向推荐

| 兴趣方向 | 推荐课题 |
|---------|---------|
| 底层/系统 | SD-02, SD-03, SD-11, HW-01, HW-02, HW-03 |
| 工具开发 | SD-05, SD-06, SD-07, SD-08 |
| 网络/分布式 | SD-03, SD-04, SD-09, SD-11, SD-12, HW-03 |
| 数据/算法 | SD-02, SD-06, SD-07, SD-10 |
| 前端/可视化 | FE-01 |
| 嵌入式/硬件 | HW-01, HW-02, HW-03 |
| 测试/质量 | QA-01, QA-02, HW-02 |

---

## 八、执行指南

### 8.1 环境准备（纯软件）

```bash
# 1. 安装Node.js (v18+)
# 2. 安装Python (v3.9+)
# 3. 安装OpenSpec
npm install -g @fission-ai/openspec@latest

# 4. 安装AI Coding工具（推荐Claude Code）
npm install -g @anthropic-ai/claude-code

# 5. 配置Git
git config --global user.name "Your Name"
git config --global user.email "your.email@company.com"

# 6. 硬件课题额外安装（仅需软件）
# - QEMU: apt-get install qemu-system-arm
# - 交叉编译器: apt-get install gcc-arm-none-eabi
# - GDB: apt-get install gdb-multiarch
```

### 8.2 项目初始化流程

```bash
# 1. 创建项目目录
mkdir ai-coding-training
cd ai-coding-training

# 2. 初始化Git
git init

# 3. 初始化OpenSpec
openspec init --tools claude

# 4. 创建变更
openspec new change my-feature

# 5. 按阶段创建文档（按Day 1-5执行）
```

### 8.3 各阶段详细要求

#### Day 1: Proposal + Specs初稿

**proposal.md 模板**:
```markdown
# Proposal: [课题名称]

## 背景
[为什么要做这个工具/服务]

## 目标
[具体要实现什么]

## 范围
### 包含
- [功能1]
- [功能2]

### 不包含
[超出范围的功能]

## 验收标准
- [ ] 标准1: 具体可验证的条件
- [ ] 标准2: 具体可验证的条件

## 技术栈
- 语言: [Python/Node.js/C/...]
- 主要依赖: [列出关键库]
- 运行环境: [纯软件/仿真器]
```

**Specs编写规范**:
```markdown
### Requirement: [功能名称]
The system SHALL [功能描述]

#### Scenario: [场景名称]
- GIVEN [前置条件]
- WHEN [操作]
- THEN [预期结果]

#### Scenario: [异常场景]
- GIVEN [前置条件]
- WHEN [错误操作]
- THEN [错误处理结果]
```

#### Day 2: 完善Specs

- 每个核心功能至少2个场景（正常+异常）
- 边界条件覆盖
- 使用RFC 2119关键词（SHALL/MUST/SHOULD/MAY）

#### Day 3: Design + Tasks

**design.md 模板**:
```markdown
# Design: [课题名称]

## 架构概览
[文字描述或简单架构图]

## 模块划分
### Module 1: [名称]
- 职责: [描述]
- 接口: [关键函数/方法]

### Module 2: [名称]
...

## 数据模型
[如果有数据存储，描述数据结构]

## 技术选型说明
- 选择X而不是Y的原因
- 仿真/模拟方案说明（如适用）
```

**tasks.md 模板**:
```markdown
# Tasks: [课题名称]

## Phase 1: 基础架构
- [ ] Task 1.1: [具体任务]
- [ ] Task 1.2: [具体任务]

## Phase 2: 核心功能
- [ ] Task 2.1: [具体任务]
- [ ] Task 2.2: [具体任务]

## Phase 3: 测试与优化
- [ ] Task 3.1: 编写单元测试
- [ ] Task 3.2: 集成测试
```

#### Day 4: Implementation

**AI Coding最佳实践**:
1. **按Task逐个实现**，每完成一个Task提交一次代码
2. **Commit Message规范**:
   ```
   feat: 添加XXX功能
   fix: 修复XXX问题
   test: 添加XXX测试
   docs: 更新XXX文档
   ```
3. **与AI协作模式**:
   - 先给AI看当前Task的Specs
   - 要求AI先生成代码，再解释关键逻辑
   - Review AI生成的代码，要求改进

#### Day 5: Verification + Demo准备

**验证清单**:
- [ ] 所有Specs场景都有对应测试
- [ ] 测试通过率≥80%
- [ ] 核心功能可演示（纯软件运行）
- [ ] 代码风格统一
- [ ] 无严重bug

**Demo准备**:
- 3分钟: 项目介绍 + 技术栈说明
- 5分钟: 功能演示（纯软件运行，无需硬件）
- 2分钟: SDD过程回顾（遇到的挑战、AI使用心得）

---

## 九、成果提交

培训成果提交至 **GitHub 个人仓库**，提交作品链接即可。要求：
- 仓库包含完整的项目代码及 SDD 各阶段文档（proposal、specs、design、tasks）
- Git 提交历史清晰，按 Task 提交，commit message 规范
- README.md 包含项目说明、运行方式、测试结果截图

---

## 十、评审标准

### 9.1 SDD过程完整性（40分）

| 检查项 | 分值 | 说明 |
|--------|------|------|
| proposal.md | 5分 | 目标清晰、范围明确 |
| specs/*.md | 10分 | 格式规范、覆盖完整 |
| design.md | 10分 | 架构合理、设计清晰 |
| tasks.md | 5分 | 任务可执行、追踪完整 |
| Git提交记录 | 10分 | 按Task提交、message规范 |

### 9.2 代码质量（30分）

| 检查项 | 分值 | 说明 |
|--------|------|------|
| 功能完整性 | 10分 | 核心功能实现 |
| 代码可读性 | 10分 | 命名规范、结构清晰 |
| 测试覆盖 | 10分 | 有测试、覆盖主要场景 |

### 9.3 AI工具使用（20分）

| 检查项 | 分值 | 说明 |
|--------|------|------|
| AI协作效率 | 10分 | 有效利用AI加速开发 |
| Prompt质量 | 10分 | 给AI的指令清晰、上下文完整 |

### 9.4 演示表现（10分）

| 检查项 | 分值 | 说明 |
|--------|------|------|
| 功能演示 | 5分 | 流畅展示核心功能（纯软件运行） |
| 过程回顾 | 5分 | 能总结SDD执行心得 |

**总分**: 100分  
**通过线**: 70分  
**优秀线**: 85分

---

## 十一、常见问题FAQ

### Q1: 遇到AI生成的代码有bug怎么办？
**A**: 这是正常的。把错误信息和相关代码给AI，让它修复。记录你发现的AI常见错误模式。

### Q2: Specs写得不完整，实现时发现漏了怎么办？
**A**: 回退到Specs阶段补充，然后继续。SDD是迭代过程，不是瀑布。

### Q3: 5天时间不够怎么办？
**A**: 优先保证SDD流程完整，功能可以裁剪。与导师沟通调整范围。

### Q4: 可以复制开源代码吗？
**A**: 可以参考，但必须理解并用自己的方式实现。禁止直接复制粘贴。

### Q5: 如何证明我正确使用了AI？
**A**: 保留与AI的对话截图或导出，作为过程产物的一部分。

### Q6: 硬件课题没有真实硬件怎么验证？
**A**: 硬件课题使用QEMU等仿真器，在虚拟环境中验证。仿真器可以模拟GPIO、UART、网络等外设，完全满足学习需求。

### Q7: 测试课题需要专业测试仪器吗？
**A**: 不需要。所有测试课题均为纯软件实现，API测试使用HTTP客户端，UI测试使用无头浏览器，无需Spirent/Ixia等专业仪器。

### Q8: 所有课题都需要什么软件环境？
**A**: 
- 基础环境: Git, Node.js, Python
- 硬件课题额外: QEMU, 交叉编译工具链（均为免费开源软件）
- 无需购买任何硬件设备或商业软件

---

## 十二、资源链接

- **OpenSpec文档**: https://github.com/fission-ai/openspec
- **Conventional Commits**: https://www.conventionalcommits.org/
- **QEMU文档**: https://www.qemu.org/documentation/
- **Playwright文档**: https://playwright.dev/
- **评审Checklist**: 见本文档第九章

---

*文档生成时间: 2026-04-23*  
*版本: v3.0*  
*课题总计: 17个（硬件3 + 测试2 + 前端1 + 软件11）*
