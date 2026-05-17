# 教训：Nano Banana Pro 技能安装与配置

日期：2026-03-17

## 问题
安装 Nano Banana Pro 技能时遇到环境依赖问题。

## 具体情况
1. 技能脚本需要 `uv` 命令运行，但系统未安装
2. 脚本需要 Python >= 3.10，但系统只有 Python 3.6.8 和 3.8.17
3. 即使使用 Python 3.8，也无法从阿里云镜像安装 `google-genai` 包

## 根因
- 技能依赖较新的 Python 版本和特定包管理工具
- 系统环境较旧，不满足技能运行要求

## 预防措施
1. 安装技能前，先检查 SKILL.md 中的依赖要求
2. 确认系统 Python 版本是否满足 >= 3.10
3. 如需使用 uv，先执行 `curl -LsSf https://astral.sh/uv/install.sh | sh` 安装
4. 考虑使用虚拟环境隔离依赖

## 状态
待解决 - 需要升级 Python 或安装 uv 才能正常使用
