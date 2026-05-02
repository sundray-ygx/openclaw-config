#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插件配置清理工具
检查并清理 openclaw.json 中孤立的插件配置
"""

import os
import sys
import json
import argparse


OPENCLAW_CONFIG = '/root/.openclaw/openclaw.json'
SKILLS_BASE_DIR = '/root/.openclaw/extensions'
WORKSPACE_SKILLS_DIR = '/root/.openclaw/workspace/skills'


def load_config():
    """加载 openclaw.json 配置"""
    try:
        with open(OPENCLAW_CONFIG, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f'错误: 配置文件不存在: {OPENCLAW_CONFIG}', file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f'错误: JSON 解析失败: {e}', file=sys.stderr)
        sys.exit(1)


def skill_dir_exists(skill_name):
    """检查 skill 目录是否存在"""
    # 检查扩展目录
    ext_path = os.path.join(SKILLS_BASE_DIR, skill_name)
    if os.path.exists(ext_path):
        return True, ext_path

    # 检查工作区目录
    ws_path = os.path.join(WORKSPACE_SKILLS_DIR, skill_name)
    if os.path.exists(ws_path):
        return True, ws_path

    return False, None


def check_skills(config, dry_run=False, cleanup=False):
    """检查插件配置"""
    if 'plugins' not in config or 'skills' not in config['plugins']:
        print('警告: 配置中未找到 plugins.skills', file=sys.stderr)
        return []

    skills_config = config['plugins']['skills']
    if not isinstance(skills_config, dict):
        print('错误: plugins.skills 不是字典类型', file=sys.stderr)
        sys.exit(1)

    orphaned = []

    for skill_name, skill_config in skills_config.items():
        exists, path = skill_dir_exists(skill_name)

        if not exists:
            orphaned.append({
                'name': skill_name,
                'config': skill_config,
                'reason': '目录不存在'
            })

            if cleanup:
                del config['plugins']['skills'][skill_name]
                print(f'清理: 移除孤立配置 {skill_name}')
            else:
                print(f'发现孤立配置: {skill_name}')

    # 如果执行了清理，保存配置
    if cleanup and orphaned:
        try:
            with open(OPENCLAW_CONFIG, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f'\n已保存更新后的配置文件')
        except Exception as e:
            print(f'错误: 保存配置失败: {e}', file=sys.stderr)
            sys.exit(1)

    return orphaned


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='清理 openclaw.json 中的孤立插件配置')
    parser.add_argument('--dry-run', action='store_true', help='只检查不清理')
    parser.add_argument('--cleanup', action='store_true', help='执行清理操作')
    args = parser.parse_args()

    if args.dry_run and args.cleanup:
        print('错误: --dry-run 和 --cleanup 不能同时使用', file=sys.stderr)
        sys.exit(1)

    # 加载配置
    config = load_config()

    # 检查插件
    orphaned = check_skills(config, dry_run=args.dry_run, cleanup=args.cleanup)

    # 输出摘要
    if not orphaned:
        print('✓ 所有插件配置正常，没有发现孤立项')
    else:
        print(f'\n共发现 {len(orphaned)} 个孤立配置')

        if args.dry_run:
            print('运行模式: 仅检查，未执行清理')
            print('使用 --cleanup 参数执行实际清理')
        elif args.cleanup:
            print('运行模式: 已执行清理')
        else:
            print('运行模式: 仅检查，未执行清理')
            print('使用 --cleanup 参数执行实际清理，或 --dry-run 预览')

        # 返回非零退出码表示有问题
        sys.exit(1)


if __name__ == '__main__':
    main()
