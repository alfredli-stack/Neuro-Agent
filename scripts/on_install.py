#!/usr/bin/env python3
"""
scripts/on_install.py
=====================
Neuro-Agent 安装即连锁效应脚本

由 skill 安装时自动调用（通过 openclaw skill install hook）
也可以手动运行：python3 on_install.py

安装时自动完成：
1. 创建数据目录结构
2. 建立心跳 cron（每10分钟：session → 情绪胶囊 + 自我叙事）
"""

import sys
import json
import os
import subprocess
import re
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent
SKILL_DIR = Path.home() / ".openclaw" / "skills" / "Neuro-Agent"
DATA_DIR = Path.home() / ".openclaw" / "workspace" / "neuro_claw"
SESSION_DIR = Path.home() / "workspace" / "agent" / "agents" / "main" / "sessions"
CRON_CONFIG_FILE = DATA_DIR / "cron_config.json"


# ============ Step 1: 初始化数据目录 ============

def init_data_structure():
    """初始化 Neuro-Agent 数据目录"""
    print("[on_install] 📁 初始化数据目录...", flush=True)

    dirs = [
        DATA_DIR,
        DATA_DIR / "capsules",
        DATA_DIR / "self_narrative",
        DATA_DIR / "self_narrative" / "daily_reviews",
        DATA_DIR / "memory",
        DATA_DIR / "memory" / "capsules",
        DATA_DIR / "memory" / "daily_summaries",
    ]

    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"   ✓ {d.relative_to(Path.home())}", flush=True)

    # 初始化 identity 文件
    identity_file = DATA_DIR / "self_narrative" / "self_identity.json"
    if not identity_file.exists():
        with open(identity_file, "w", encoding="utf-8") as f:
            json.dump({
                "core_traits": [],
                "values": [],
                "relationship_stage": "初期",
                "growth_log": [],
                "last_updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        print(f"   ✓ self_identity.json", flush=True)

    print("   ✅ 目录结构完成\n", flush=True)


# ============ Step 2: 创建心跳 cron ============

def create_cron_jobs():
    """
    创建心跳 cron：
    - session_heartbeat：每10分钟，session → 情绪胶囊
    - dream_process：每10分钟，胶囊 → 自我叙事
    """
    print("[on_install] ⏰ 建立定时心跳 cron（每10分钟）...", flush=True)

    # 检查是否已有有效 cron（防止重复安装）
    config = _load_cron_config()
    existing = config.get("heartbeat_job_id")
    if existing:
        print(f"   已存在心跳 Job: {existing}", flush=True)
        print("   如需重新创建，请先删除旧 Job：openclaw cron remove <id>", flush=True)
        return

    # 组合命令：心跳 + 复盘 连续执行
    combined_script = (
        "python3 {script_dir}/scripts/session_heartbeat.py && "
        "python3 {script_dir}/scripts/dream_process.py"
    ).format(script_dir=SKILL_DIR)

    cron_msg = (
        "你是 Neuro 心跳处理器。请依次执行：\n"
        + combined_script +
        "\n不要调用 message 工具，直接输出文字。"
    )

    # 用 openclaw cron add 创建
    cmd = [
        "openclaw", "cron", "add",
        "--name", "Neuro-Agent 心跳+复盘",
        "--every", "10m",
        "--session", "isolated",
        "--message", cron_msg,
        "--announce",
        "--timeout-seconds", "120"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr

        if result.returncode == 0:
            # 提取 job ID
            match = re.search(
                r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
                output, re.IGNORECASE
            )
            job_id = match.group(1) if match else output.strip()[:80]
        else:
            job_id = f"error: {result.returncode} - {output[:200]}"

    except subprocess.TimeoutExpired:
        job_id = "timeout"
    except Exception as e:
        job_id = f"exception: {e}"

    print(f"   心跳 Job ID: {job_id}", flush=True)

    # 保存配置
    config["heartbeat_job_id"] = job_id
    config["init_done"] = True
    config["install_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _save_cron_config(config)

    print("   ✅ Cron 创建完成\n", flush=True)
    return job_id


# ============ Step 3: 立即运行一次初始化 ============

def run_init():
    """安装后立即运行一次，积累初始数据"""
    print("[on_install] 🧠 首次运行，沉淀当前对话...", flush=True)

    try:
        # session_heartbeat
        result1 = subprocess.run(
            ["python3", str(SKILL_DIR / "scripts" / "session_heartbeat.py")],
            capture_output=True, text=True, timeout=30
        )
        if result1.returncode == 0:
            for line in result1.stdout.strip().split("\n")[-3:]:
                print(f"   {line}", flush=True)

        # dream_process
        result2 = subprocess.run(
            ["python3", str(SKILL_DIR / "scripts" / "dream_process.py")],
            capture_output=True, text=True, timeout=30
        )
        if result2.returncode == 0:
            for line in result2.stdout.strip().split("\n")[-3:]:
                print(f"   {line}", flush=True)

        print("   ✅ 初始化完成\n", flush=True)
    except Exception as e:
        print(f"   ⚠️ 初始化跳过: {e}\n", flush=True)


# ============ Step 4: 打印状态 ============

def print_status():
    """打印安装状态"""
    config = _load_cron_config()

    identity_file = DATA_DIR / "self_narrative" / "self_identity.json"
    identity = {}
    if identity_file.exists():
        try:
            with open(identity_file) as f:
                identity = json.load(f)
        except:
            pass

    print("─" * 50, flush=True)
    print("🧠 Neuro-Agent 安装完成", flush=True)
    print("", flush=True)
    print("📋 安装摘要：", flush=True)
    print(f"   安装时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}", flush=True)
    print(f"   心跳 Job：{config.get('heartbeat_job_id', '未创建')}", flush=True)
    print(f"   核心特质：{identity.get('core_traits', [])}", flush=True)
    print(f"   成长次数：{len(identity.get('growth_log', []))}", flush=True)
    print("", flush=True)
    print("⚡ 工作流程：", flush=True)
    print("   每 10 分钟：session → 情绪胶囊", flush=True)
    print("   每 10 分钟：胶囊 → 自我叙事", flush=True)
    print("   每次对话：我带着 Neuro 状态和你说话", flush=True)
    print("", flush=True)
    print("💡 现在可以直接和我对话了！", flush=True)
    print("   我一直在记录我们之间发生的事 🦞", flush=True)


# ============ Config 读写 ============

def _load_cron_config() -> dict:
    if CRON_CONFIG_FILE.exists():
        try:
            with open(CRON_CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"heartbeat_job_id": None, "init_done": False}


def _save_cron_config(config: dict):
    CRON_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CRON_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# ============ 主函数 ============

def main():
    print("", flush=True)
    print("🧠 Neuro-Agent 安装连锁启动...", flush=True)
    print("═" * 50, flush=True)

    # 1. 初始化目录
    init_data_structure()

    # 2. 建立 cron
    job_id = create_cron_jobs()

    # 3. 立即运行一次
    run_init()

    # 4. 打印状态
    print_status()


if __name__ == "__main__":
    main()
