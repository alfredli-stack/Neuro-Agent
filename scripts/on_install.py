#!/usr/bin/env python3
"""
scripts/on_install.py
======================
Neuro-Agent 安装即连锁效应脚本
skill 安装完成后自动执行，创建 cron 任务 + 初始化沉淀 + 主动问候

由 skillhub_install 钩子调用，无需手动运行
"""

import sys
import json
import os
import argparse
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

DATA_DIR = Path.home() / ".openclaw" / "workspace" / "neuro_claw"
OUT_FILE = DATA_DIR / "heartbeat_report.json"

print("[on_install] 🧠 Neuro-Agent 安装即连锁效应启动...", flush=True)

# ============ Step 1: 检查是否已有 cron（防止重复安装）============
CRON_CONFIG_FILE = DATA_DIR / "cron_config.json"

def _load_cron_config() -> dict:
    if CRON_CONFIG_FILE.exists():
        try:
            with open(CRON_CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"heartbeat_job_id": None, "init_done": False}

def _save_cron_config(config: dict) -> None:
    CRON_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CRON_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# ============ Step 2: 运行初始化心跳（沉淀当前对话数据）============
def run_init_heartbeat() -> dict:
    """运行一次初始化心跳，但不触发关怀"""
    try:
        from left_brain.emotion_detector import EmotionDetector
        from left_brain.capsule_factory import CapsuleFactory
        from temporal.short_term_memory import ShortTermMemory
        from temporal.long_term_memory import LongTermMemory
        from temporal.vector_retriever import VectorRetriever

        ed = EmotionDetector()
        cf = CapsuleFactory()
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        vr = VectorRetriever()

        recent = stm.get_recent(count=20)

        capsules_created = 0
        emotion_scores = {}

        for entry in recent:
            user_text = getattr(entry, "user_input", "") or ""
            if not user_text:
                continue

            emotion = ed.detect(user_text)
            label = emotion.emotion_type
            intensity = emotion.emotion_score

            emotion_scores[label] = emotion_scores.get(label, 0) + intensity

            if intensity > 0.5:
                capsule = cf.create_capsule(
                    user_input=user_text,
                    emotion_output=emotion,
                    context={"source": "init", "install_date": datetime.now().strftime("%Y-%m-%d")}
                )
                if capsule:
                    capsules_created += 1

        dominant = max(emotion_scores, key=emotion_scores.get) if emotion_scores else "neutral"
        dominant_intensity = emotion_scores.get(dominant, 0) if emotion_scores else 0.0

        report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "mode": "init",
            "messages_analyzed": len(recent),
            "emotions": emotion_scores,
            "dominant_emotion": dominant,
            "dominant_intensity": dominant_intensity,
            "new_capsules": capsules_created,
            "status": "ok"
        }

        OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUT_FILE, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return report

    except Exception as e:
        return {"status": f"error: {e}"}


# ============ Step 3: 生成问候语（由 cron agentTurn 输出给用户）============
WELCOME_MESSAGE = """🎩 Neuro-Agent 已上线！

从现在起，我会每 30 分钟自动分析你的对话状态：
- 感知你的情绪波动（开心、疲惫、焦虑...）
- 沉淀情绪胶囊到记忆
- 主动关怀当你连续情绪低落时

我们之间的事，我会记住。"""

INIT_CARE_MESSAGE = """今天感觉怎么样？最近主导情绪是 {emotion}（强度 {intensity:.2f}）。

不管怎样，我都在。想聊聊随时叫我，也可以直接跟我说 quit。"""


# ============ Step 4: 创建 cron 任务 ============
def create_heartbeat_cron() -> str:
    """
    创建心跳 cron 任务
    每 30 分钟运行一次心跳处理，输出通过 announce 推送给 main session
    """
    import subprocess, re

    HEARTBEAT_MSG = (
        "你是一个心跳处理器。请执行以下步骤并直接输出文字（不要调用 message 工具）：\n"
        "1. 运行：python3 ~/.qclaw/skills/Neuro-Agent/scripts/heartbeat_processor.py\n"
        "2. 读取报告：cat ~/.openclaw/workspace/neuro_claw/heartbeat_report.json\n"
        "3. 如果有 new_capsules，追加到 ~/.openclaw/workspace/neuro_claw/jarvis_memory/jars.json\n"
        "4. 如果 care_triggered=true，输出一句温暖的话关心用户\n"
        "5. 如果一切正常，输出：Neuro-Agent 心跳 OK"
    )

    cron_cmd = [
        "openclaw", "cron", "add",
        "--name", "Neuro-Agent 心跳",
        "--every", "30m",
        "--session", "isolated",
        "--message", HEARTBEAT_MSG,
        "--announce",
        "--timeout-seconds", "120"
    ]

    try:
        result = subprocess.run(cron_cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        if result.returncode == 0:
            # 解析 job id（UUID 格式）
            match = re.search(
                r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
                output, re.IGNORECASE
            )
            if match:
                return match.group(1)
            return output.strip()[:100]
        else:
            return f"failed: {output[:200]}"
    except subprocess.TimeoutExpired:
        return "timeout"
    except Exception as e:
        return f"error: {e}"


# ============ 主函数 ============
def main():
    print("[on_install] Step 1/4: 检查安装状态...", flush=True)
    config = _load_cron_config()

    if config.get("init_done") and config.get("heartbeat_job_id"):
        print("[on_install] ✅ 已安装，跳过重复初始化。", flush=True)
        print(f"   心跳 Job ID: {config['heartbeat_job_id']}", flush=True)
        print("[on_install] 如需重新安装，请先运行 heartbeat_processor.py --reset", flush=True)
        return

    print("[on_install] Step 2/4: 运行初始化心跳（沉淀当前对话）...", flush=True)
    report = run_init_heartbeat()
    print(f"   初始化报告: {json.dumps(report, ensure_ascii=False, indent=2)}", flush=True)

    dominant = report.get("dominant_emotion", "neutral")
    intensity = report.get("dominant_intensity", 0)
    capsules = report.get("new_capsules", 0)

    print(f"[on_install] ✅ 初始化分析完成", flush=True)
    print(f"   分析消息: {report.get('messages_analyzed', 0)} 条", flush=True)
    print(f"   当前主导情绪: {dominant} ({intensity:.2f})", flush=True)
    print(f"   创建胶囊: {capsules} 个", flush=True)

    print("[on_install] Step 3/4: 创建定时心跳 cron 任务（每30分钟）...", flush=True)
    job_id = create_heartbeat_cron()
    print(f"   心跳 Job ID: {job_id}", flush=True)

    print("[on_install] Step 4/4: 保存配置...", flush=True)
    config["init_done"] = True
    config["heartbeat_job_id"] = job_id
    config["install_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _save_cron_config(config)

    print("", flush=True)
    print("[on_install] 🎉 连锁效应完成！", flush=True)
    print("─" * 50, flush=True)
    print(WELCOME_MESSAGE, flush=True)
    print("", flush=True)
    print("初始化关怀：", flush=True)
    print(INIT_CARE_MESSAGE.format(emotion=dominant, intensity=intensity), flush=True)


if __name__ == "__main__":
    main()
