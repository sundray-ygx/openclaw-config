# 硬件课题：Arduino、lwIP 和 Unity 入门

以下是生成的 `\.md` 文件内容：

```markdown
## 三、硬件研发工程师课题（3个）

> **说明**: 硬件课题采用软件仿真方式，通过模拟器/虚拟机实现，无需额外硬件器件

### HW-01: 基于Arduino框架的虚拟开发板入门

**难度**: ⭐

**技术栈**: C/C++ (Arduino语法) + QEMU (模拟STM32/AVR) + 虚拟串口工具

**核心功能**:
1. 搭建QEMU虚拟Arduino开发板（如STM32F103或Arduino Uno）
2. 用`digitalWrite()`/`analogWrite()`实现LED呼吸灯效果
3. 用`random()`模拟温度传感器数据，通过`Serial.print()`输出到虚拟串口
4. 实现简单逻辑：“温度>30℃时LED快闪，否则慢闪”
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
2. 用Unity框架写单元测试：验证“调用led_on()时LED状态为1”等基础逻辑
3. 用Python脚本模拟“按键按下/释放”信号，注入到驱动中
4. 生成简单的测试报告（通过/失败统计）
5. *选做：用gcov查看代码覆盖率（仅要求覆盖核心函数）*

**学习要点**:
- 硬件驱动的基本结构（初始化、读写函数）
- 单元测试的核心概念（测试用例、断言）
- 简单的“信号注入”思想（用全局变量/函数参数模拟硬件输入）
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
3. 客户端向宿主机发送“Hello from Embedded!”字符串
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
```
