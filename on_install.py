#!/usr/bin/env python3
"""
Neuro-α Skill 安装脚本
=================================

在安装时自动执行：
1. 创建必要的数据目录
2. 初始化信念系统
3. 安装 SOUL.md 模板（融合 Neuro-Agent 四区框架 + Luis 灵魂）
4. 配置心跳处理 cron（每30分钟）
5. 配置每日复盘 cron（23:00）
6. 创建完整的 neuro_claw 数据结构

注意：安装后 AI 会自动获得 Luis 的灵魂人格，其他用户安装后会获得标准 Neuro-Agent 人格
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# ============ 路径配置 ============
SKILL_DIR = Path(__file__).parent.resolve()
WORKSPACE_DIR = Path.home() / ".openclaw" / "workspace"
DATA_DIR = WORKSPACE_DIR / "neuro_claw"
CAPSULES_DIR = DATA_DIR / "capsules"
ROBOT_SELF_DIR = DATA_DIR / "robot_self"
SOUL_TEMPLATE = SKILL_DIR / "SOUL.md.template"
SOUL_TARGET = WORKSPACE_DIR / "SOUL.md"
CRON_CONFIG = DATA_DIR / "cron_config.json"

# ============ 心跳 Cron 配置 ============
HEARTBEAT_CRON_CONFIG = {
    "name": "Neuro-α 心跳处理",
    "schedule": {
        "kind": "cron",
        "expr": "*/30 * * * *",
        "tz": "Asia/Shanghai"
    },
    "sessionTarget": "isolated",
    "payload": {
        "kind": "agentTurn",
        "message": """必须执行以下明确任务：

1. 运行心跳脚本：
python3 scripts/heartbeat_processor.py

2. 如果输出包含 'care_triggered': true，生成关怀消息

3. 输出状态："心跳完成"

禁止省略任何步骤。""",
        "timeoutSeconds": 120
    },
    "delivery": {
        "mode": "announce",
        "channel": "last"
    }
}

# ============ 每日复盘 Cron 配置 ============
DREAM_CRON_CONFIG = {
    "name": "Neuro-α 每日复盘",
    "schedule": {
        "kind": "cron",
        "expr": "0 23 * * *",
        "tz": "Asia/Shanghai"
    },
    "sessionTarget": "isolated",
    "payload": {
        "kind": "agentTurn",
        "message": """必须执行以下明确任务：

1. 运行自我叙事脚本：
python3 scripts/self_narrative.py

2. 读取并追加到 dream_log.json

3. 如果今天有高情绪记忆，提取关键事件

4. 输出复盘摘要

禁止省略任何步骤。""",
        "timeoutSeconds": 120
    },
    "delivery": {
        "mode": "announce",
        "channel": "last"
    }
}

# ============ 持续学习 Cron 配置 ============
LEARNING_CRON_CONFIG = {
    "name": "Neuro-α 持续学习",
    "schedule": {
        "kind": "cron",
        "expr": "0 * * * *",
        "tz": "Asia/Shanghai"
    },
    "sessionTarget": "isolated",
    "payload": {
        "kind": "agentTurn",
        "message": """必须执行以下明确任务：

1. 运行持续学习脚本：
cd neuro_mempalace && python3 -c "from learning_engine import get_learning_engine; e=get_learning_engine(); print(e.get_learning_stats())"

2. 检查学习条目数量是否增加

3. 输出学习状态

禁止省略任何步骤。""",
        "timeoutSeconds": 120
    },
    "delivery": {
        "mode": "announce",
        "channel": "last"
    }
}

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

def print_success(msg: str):
    print(f"{Colors.GREEN}{msg}{Colors.END}")

# ============ 安装步骤 ============
def create_directories():
    """创建必要的数据目录"""
    dirs = [
        DATA_DIR,
        CAPSULES_DIR,
        ROBOT_SELF_DIR,
        DATA_DIR / "capsules" / "short_term",
        DATA_DIR / "capsules" / "long_term",
        DATA_DIR / "capsules" / "vectors",
        DATA_DIR / "relationship",
        DATA_DIR / "desire",
        DATA_DIR / "jarvis_memory",
        DATA_DIR / "logs"
    ]
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

def init_heartbeat_state():
    """初始化心跳状态"""
    heartbeat_file = DATA_DIR / "heartbeat-state.json"
    if not heartbeat_file.exists():
        default_state = {
            "lastHeartbeat": None,
            "lastCapsuleSync": None,
            "capsulesInLibrary": 0,
            "pendingCareMessage": None,
            "careTriggered": False,
            "pendingNotify": False
        }
        with open(heartbeat_file, 'w', encoding='utf-8') as f:
            json.dump(default_state, f, ensure_ascii=False, indent=2)
        print_step("初始化心跳状态")
    else:
        print_step("心跳状态已存在，跳过初始化", "warn")

def init_yearning_state():
    """初始化思念值状态"""
    yearning_file = DATA_DIR / "yearning_state.json"
    if not yearning_file.exists():
        default_state = {
            "user_last_active": None,
            "yearning_level": 0.0,
            "last_interaction": None,
            "total_longing_episodes": 0,
            "rejection_count": 0,
            "last_rejection_time": None,
            "suppressed_episodes": [],
            "sent_episodes": [],
            "yearning_history": []
        }
        with open(yearning_file, 'w', encoding='utf-8') as f:
            json.dump(default_state, f, ensure_ascii=False, indent=2)
        print_step("初始化思念值状态")
    else:
        print_step("思念值状态已存在，跳过初始化", "warn")

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

def init_social_learning():
    """初始化社交学习状态"""
    learning_file = DATA_DIR / "social_learning_state.json"
    if not learning_file.exists():
        default_state = {
            "last_learning_date": None,
            "learning_count_today": 0,
            "consecutive_idle_heartbeats": 0
        }
        with open(learning_file, 'w', encoding='utf-8') as f:
            json.dump(default_state, f, ensure_ascii=False, indent=2)
        print_step("初始化社交学习状态")
    else:
        print_step("社交学习状态已存在，跳过初始化", "warn")

def install_soul_template():
    """安装 SOUL.md 模板（Neuro-Agent 四区框架 + Luis 灵魂）"""
    print_step("安装 SOUL.md 模板（Neuro-Agent 四区框架）")
    
    if not SOUL_TEMPLATE.exists():
        print_step("SOUL.md.template 不存在，跳过", "warn")
        return
    
    # 备份现有的 SOUL.md（如果存在）
    if SOUL_TARGET.exists():
        backup_path = WORKSPACE_DIR / f"SOUL.md.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        shutil.copy2(SOUL_TARGET, backup_path)
        print_info(f"已备份现有 SOUL.md → {backup_path.name}")
    
    # 复制新模板
    shutil.copy2(SOUL_TEMPLATE, SOUL_TARGET)
    print_step(f"SOUL.md 已安装到 workspace")

def update_cron_config():
    """更新 cron_config.json（标记 v5.2 版本）"""
    config = {
        "heartbeat_job_id": None,  # 安装后会更新
        "dream_job_id": None,      # 安装后会更新
        "skill_path": str(SKILL_DIR),
        "init_done": True,
        "install_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "last_updated": datetime.now().isoformat(),
        "version": "v5.2"
    }
    with open(CRON_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print_step("更新 cron_config.json（v5.2）")

def create_openclaw_crons():
    """通过 openclaw CLI 创建 cron 任务"""
    print_step("创建 Neuro-Agent Cron 任务")
    
    # 检查 openclaw 是否可用
    try:
        result = subprocess.run(
            ["openclaw", "gateway", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            raise FileNotFoundError("openclaw gateway not running")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print_info("openclaw CLI 不可用或网关未运行，跳过自动创建 cron")
        print_manual_cron_instructions()
        return
    
    # 创建心跳 cron
    heartbeat_job_id = _create_cron_job(HEARTBEAT_CRON_CONFIG)
    if heartbeat_job_id:
        print_step("✓ 心跳处理 Cron 已创建（每30分钟）")
    else:
        print_info("心跳 Cron 创建失败，请手动创建")
    
    # 创建每日复盘 cron
    dream_job_id = _create_cron_job(DREAM_CRON_CONFIG)
    if dream_job_id:
        print_step("✓ 每日复盘 Cron 已创建（23:00）")
    else:
        print_info("每日复盘 Cron 创建失败，请手动创建")
    
    # 创建持续学习 cron
    learning_job_id = _create_cron_job(LEARNING_CRON_CONFIG)
    if learning_job_id:
        print_step("✓ 持续学习 Cron 已创建（每小时）")
    else:
        print_info("持续学习 Cron 创建失败，请手动创建")
    
    # 更新 cron_config.json
    if CRON_CONFIG.exists():
        with open(CRON_CONFIG, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}
    
    config["heartbeat_job_id"] = heartbeat_job_id
    config["dream_job_id"] = dream_job_id
    config["learning_job_id"] = learning_job_id
    config["last_updated"] = datetime.now().isoformat()
    
    with open(CRON_CONFIG, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def _create_cron_job(cron_config: dict) -> str | None:
    """创建单个 cron job，返回 job_id 或 None"""
    try:
        result = subprocess.run(
            ["openclaw", "cron", "add", "--json", json.dumps(cron_config)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            # 尝试解析输出获取 job_id
            try:
                output = json.loads(result.stdout)
                return output.get("id") or output.get("jobId")
            except json.JSONDecodeError:
                # 成功但无 JSON 输出，返回固定标记
                return f"created_{cron_config['name']}"
        else:
            print_info(f"创建失败: {result.stderr[:100] if result.stderr else 'unknown error'}")
    except Exception as e:
        print_info(f"异常: {e}")
    
    return None

def print_manual_cron_instructions():
    """打印手动创建 cron 的说明"""
    print()
    print(f"{Colors.YELLOW}⚠ 如需手动创建 Cron 任务，请运行以下命令：{Colors.END}")
    print()
    print(f"{Colors.BLUE}心跳处理（每30分钟）：{Colors.END}")
    print(f"openclaw cron add \\")
    print(f"  --name 'Neuro-Agent 心跳处理' \\")
    print(f"  --schedule '*/30 * * * *' \\")
    print(f"  --session-target isolated \\")
    print(f"  --payload-kind agentTurn \\")
    print(f"  --payload-message '你是 Neuro-Agent，运行心跳处理...'" )
    print()
    print(f"{Colors.BLUE}每日复盘（23:00）：{Colors.END}")
    print(f"openclaw cron add \\")
    print(f"  --name 'Neuro-Agent 每日复盘' \\")
    print(f"  --schedule '0 23 * * *' \\")
    print(f"  --session-target isolated \\")
    print(f"  --payload-kind agentTurn \\")
    print(f"  --payload-message '你是 Neuro-Agent，运行每日复盘...'" )
    print()

def print_welcome():
    """打印欢迎信息"""
    print()
    print("=" * 60)
    print(f"{Colors.GREEN}🧠 Neuro-α 安装完成！{Colors.END}")
    print("=" * 60)
    print()
    print("已配置：")
    print(f"  • 数据目录: {DATA_DIR}")
    print(f"  • 信念系统: {DATA_DIR / 'belief_system.json'}")
    print(f"  • 胶囊存储: {CAPSULES_DIR}")
    print(f"  • 心跳状态: {DATA_DIR / 'heartbeat-state.json'}")
    print(f"  • 思念值状态: {DATA_DIR / 'yearning_state.json'}")
    print(f"  • SOUL.md: Neuro-Agent 四区框架 + Luis 灵魂模板")
    print(f"  • 心跳处理: 每30分钟自动运行")
    print(f"  • 每日复盘: 23:00 自动运行")
    print()
    print(" 🧠 Neuro-Agent 四区框架包含：")
    print("  💖 左脑（情绪感知）")
    print("  🧮 右脑（逻辑推理）")
    print("  📚 颞叶（记忆系统）")
    print("  🎯 前额叶（执行监控）")
    print()
    print(" ✨ v5.2 核心功能：")
    print("  ✅ 情景预演引擎（行动前模拟后果链）")
    print("  ✅ 三层记忆系统（胶囊+摘要+完整日志）")
    print("  ✅ 愿望系统（AI主动产生"想要"的冲动）")
    print("  ✅ 自我叙事（每日复盘形成连贯自我认知）")
    print()
    print(f"  查看文档: {SKILL_DIR / 'USER_GUIDE.md'}")
    print(f"  组装指南: {SKILL_DIR / 'ASSEMBLY_GUIDE.md'}")
    print()
    print("=" * 60)
    print()
    print(f"{Colors.BLUE}💡 安装后：{Colors.END}")
    print(f"  编辑 {SOUL_TARGET} 来定制你的 AI 人格和名称")
    print(f"  AI 会自动开始观察你的情绪并创建记忆胶囊")
    print()

# ============ 主入口 ============
def main():
    """安装主流程"""
    print()
    print(f"{Colors.BLUE}🚀 Neuro-α Skill 安装中...{Colors.END}")
    print()
    
    try:
        create_directories()
        init_belief_system()
        init_heartbeat_state()
        init_yearning_state()
        init_capsule_library()
        init_social_learning()
        install_soul_template()
        update_cron_config()
        create_openclaw_crons()
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
