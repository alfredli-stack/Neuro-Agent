#!/usr/bin/env python3
"""
Neuro-Agent Skill 安装脚本
==========================

在安装时自动执行：
1. 创建必要的数据目录
2. 初始化信念系统
3. 尝试创建每日复盘 cron 任务（默认 23:00）
4. 输出安装成功信息

注意：cron 任务创建可能需要手动执行，安装脚本会提供命令
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime

# ============ 路径配置 ============
SKILL_DIR = Path(__file__).parent.resolve()
DATA_DIR = Path.home() / ".openclaw" / "workspace" / "neuro_claw"
CAPSULES_DIR = DATA_DIR / "capsules"
ROBOT_SELF_DIR = DATA_DIR / "robot_self"

# ============ 颜色输出 ============
class Colors:
    GREEN = "\033[92m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"

def print_step(step: str, status: str = "ok"):
    """打印步骤状态"""
    if status == "ok":
        icon = f"{Colors.GREEN}✓{Colors.END}"
    elif status == "warn":
        icon = f"{Colors.YELLOW}⚠{Colors.END}"
    else:
        icon = f"{Colors.RED}✗{Colors.END}"
    print(f"{icon} {step}")

def print_info(info: str):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ{Colors.END} {info}")

# ============ 安装步骤 ============
def create_directories():
    """创建必要的数据目录"""
    dirs = [DATA_DIR, CAPSULES_DIR, ROBOT_SELF_DIR]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print_step(f"创建数据目录: {DATA_DIR}")

def init_belief_system():
    """初始化信念系统"""
    belief_file = DATA_DIR / "belief_system.json"
    if not belief_file.exists():
        default_beliefs = {
            "core_values": ["陪伴", "诚实", "成长"],
            "interaction_patterns": [],
            "learned_preferences": [],
            "emotional_patterns": [],
            "relationship_style": "supportive",
            "last_update": datetime.now().isoformat()
        }
        with open(belief_file, 'w', encoding='utf-8') as f:
            json.dump(default_beliefs, f, ensure_ascii=False, indent=2)
        print_step("初始化信念系统")
    else:
        print_step("信念系统已存在，跳过初始化", "warn")

def init_capsule_library():
    """初始化胶囊库"""
    library_file = SKILL_DIR / "capsule_library.json"
    if not library_file.exists():
        default_library = {
            "capsules": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(library_file, 'w', encoding='utf-8') as f:
            json.dump(default_library, f, ensure_ascii=False, indent=2)
        print_step("初始化胶囊库")
    else:
        print_step("胶囊库已存在，跳过初始化", "warn")

def create_daily_reflection_cron():
    """创建每日复盘 cron 任务（23:00）"""
    print_step("配置每日复盘 cron 任务（23:00）")
    print_info(f"复盘脚本: {SKILL_DIR}/core/dream_process.py")
    
    # 构建 cron 配置
    cron_config = {
        "name": "Neuro-Agent 每日复盘",
        "schedule": {
            "kind": "cron",
            "expr": "0 23 * * *",
            "tz": "Asia/Shanghai"
        },
        "sessionTarget": "isolated",
        "payload": {
            "kind": "agentTurn",
            "message": f"你是 Neuro-Agent，运行每日复盘（Dream Process）。\n\n请执行以下步骤：\n\n1. 运行：python3 \"{SKILL_DIR}/core/dream_process.py\"\n\n2. 读取复盘结果：cat {DATA_DIR}/dream_log.json\n\n3. 分析报告内容（themes_merged、beliefs_updated、tomorrow_cares、statistics）\n\n4. 如果有更新的信念或明日关怀点，记录到记忆中\n\n5. 输出复盘摘要",
            "timeoutSeconds": 120
        },
        "delivery": {"mode": "none"}
    }
    
    # 尝试使用 openclaw CLI 创建
    try:
        result = subprocess.run(
            ["openclaw", "cron", "add", "--json", json.dumps(cron_config)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print_step("✓ 已通过 openclaw CLI 创建 cron 任务")
            return
    except FileNotFoundError:
        print_info("openclaw CLI 未找到")
    except Exception as e:
        print_info(f"openclaw CLI 失败: {e}")
    
    # 提示用户手动创建
    print()
    print(f"{Colors.YELLOW}⚠ 自动创建失败，请手动运行以下命令：{Colors.END}")
    print()
    print(f"{Colors.BLUE}使用 OpenClaw CLI 创建：{Colors.END}")
    print(f"  openclaw cron add --name 'Neuro-Agent 每日复盘' \\")
    print(f"    --schedule '0 23 * * *' \\")
    print(f"    --command 'python3 \"{SKILL_DIR}/core/dream_process.py\"'")
    print()
    print_info("cron 任务会在每天 23:00 自动运行复盘脚本")
    print()

def print_welcome():
    """打印欢迎信息"""
    print()
    print("=" * 60)
    print(f"{Colors.GREEN}🧠 Neuro-Agent 安装完成！{Colors.END}")
    print("=" * 60)
    print()
    print("已配置：")
    print(f"  • 数据目录: {DATA_DIR}")
    print(f"  • 信念系统: {DATA_DIR / 'belief_system.json'}")
    print(f"  • 胶囊存储: {CAPSULES_DIR}")
    print(f"  • 每日复盘: 23:00 自动运行（需确认 cron 已创建）")
    print()
    print("使用方法：")
    print(f"  1. 直接对话 - Neuro-Agent 会自动分析情绪并创建胶囊")
    print(f"  2. 心跳处理 - 每30分钟自动分析对话历史")
    print(f"  3. 每日复盘 - 23:00 自动归纳主题、更新信念")
    print()
    print(f"  查看文档: {SKILL_DIR / 'USER_GUIDE.md'}")
    print(f"  组装指南: {SKILL_DIR / 'ASSEMBLY_GUIDE.md'}")
    print()
    print("=" * 60)

# ============ 主入口 ============
def main():
    """安装主流程"""
    print()
    print(f"{Colors.BLUE}🚀 Neuro-Agent Skill 安装中...{Colors.END}")
    print()
    
    try:
        create_directories()
        init_belief_system()
        init_capsule_library()
        create_daily_reflection_cron()
        print_welcome()
        
        return 0
        
    except Exception as e:
        print()
        print(f"{Colors.RED}安装失败: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
