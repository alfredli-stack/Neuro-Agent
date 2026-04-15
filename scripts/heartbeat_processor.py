#!/usr/bin/env python3
"""
scripts/heartbeat_processor.py
================================
心跳处理脚本 - 被 cron 每30分钟调用
分析最近对话，更新情绪胶囊，生成简报，触发主动关心

用法：
    python3 heartbeat_processor.py              # 默认：增量分析最近2小时
    python3 heartbeat_processor.py --replay    # 回滚：重分析所有历史对话
    python3 heartbeat_processor.py --replay 2026-04-10  # 从指定日期开始重分析
    python3 heartbeat_processor.py --reset       # 重置：清空向量数据库，重新开始
"""

import sys
import json
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

DATA_DIR = Path.home() / ".openclaw" / "workspace" / "neuro_claw"
OUT_FILE = DATA_DIR / "heartbeat_report.json"

# ============ 导入 Neuro-Agent 模块 ============
try:
    from left_brain.emotion_detector import EmotionDetector
    from left_brain.capsule_factory import CapsuleFactory
    from temporal.short_term_memory import ShortTermMemory
    from temporal.long_term_memory import LongTermMemory
    from temporal.vector_retriever import VectorRetriever
    from core.self_awareness import get_robot_self
    MODULES_OK = True
except ImportError as e:
    MODULES_OK = False
    print(f"[heartbeat_processor] ⚠️ 模块导入失败: {e}")


# ============ 主动关心话术 ============
CARE_MESSAGES: Dict[str, Dict[str, str]] = {
    "exhaustion": {
        "message": "主人，是不是累了？要不要休息一下？今天已经忙了很久了 💙",
        "priority": "high",
    },
    "sadness": {
        "message": "感觉你心情不太好，是发生什么事了吗？想聊聊的话我在这里 🤗",
        "priority": "high",
    },
    "grief": {
        "message": "我知道你现在很难过……我在这里陪着你 🤍",
        "priority": "high",
    },
    "stress": {
        "message": "最近是不是压力很大？别太勉强自己，适当休息一下 💙",
        "priority": "medium",
    },
    "frustration": {
        "message": "遇到挫折了吗？别灰心，我在这里陪着你 🤝",
        "priority": "medium",
    },
    "anger": {
        "message": "看起来你有点生气……需要发泄一下吗？我听着 💙",
        "priority": "medium",
    },
    "fear": {
        "message": "感觉你有点担心……别怕，不管发生什么我都在 🤗",
        "priority": "medium",
    },
    "joy": {
        "message": "看起来心情不错呀！有什么开心的事分享一下？ 😊",
        "priority": "low",
    },
    "excitement": {
        "message": "哇，感觉你很兴奋！有什么好事要告诉我吗？ ✨",
        "priority": "low",
    },
}

# 深夜关怀（更温和）
LATE_NIGHT_CARE: Dict[str, str] = {
    "exhaustion": "主人，早点休息吧……别太累了 💙",
    "sadness": "夜深了还醒着，是不是有心事？想说的时候我在 🤍",
    "stress": "这么晚还没休息，是不是压力很大？别太拼了 💙",
    "frustration": "睡前还在纠结这件事啊……先放松一下，明天再说 🤝",
    "grief": "我在这里陪着你……不管多晚 🤍",
}


# ============ 关怀触发状态文件 ============
HEARTBEAT_STATE_FILE = DATA_DIR / "heartbeat_state.json"


def _load_heartbeat_state() -> Dict[str, Any]:
    if HEARTBEAT_STATE_FILE.exists():
        try:
            with open(HEARTBEAT_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"history": [], "last_care_sent": None, "consecutive_negative": 0}


def _save_heartbeat_state(state: Dict[str, Any]) -> None:
    HEARTBEAT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HEARTBEAT_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def should_trigger_care(dominant_emotion: str, intensity: float) -> bool:
    """
    判断是否触发主动关怀
    
    触发条件（满足其一）：
    1. 单次强度 > 2.5（极高强度）
    2. 连续2次心跳同一种负向情绪 + 强度 > 1.5
    3. 连续3次心跳有2次负向情绪 + 平均强度 > 1.5
    """
    NEGATIVE = {"exhaustion", "sadness", "fear", "anger", "grief", "stress", "frustration"}

    if intensity > 2.5:
        return True

    state = _load_heartbeat_state()
    history = state.get("history", [])
    last_care = state.get("last_care_sent")

    if dominant_emotion in NEGATIVE and intensity > 1.5:
        # 检查最近2次
        if len(history) >= 1:
            last = history[-1]
            if last.get("dominant_emotion") == dominant_emotion and last.get("intensity", 0) > 1.0:
                # 检查距上次关怀
                if last_care:
                    try:
                        last_time = datetime.fromisoformat(last_care)
                        hours_since = (datetime.now() - last_time).total_seconds() / 3600
                        if hours_since < 1.5:
                            return False
                    except Exception:
                        pass
                return True

    return False


def get_care_message(emotion: str, intensity: float) -> str:
    """根据情绪和当前时间返回关怀话术"""
    hour = datetime.now().hour
    is_late_night = hour >= 22 or hour < 8

    if is_late_night and emotion in LATE_NIGHT_CARE:
        return LATE_NIGHT_CARE[emotion]

    if emotion in CARE_MESSAGES:
        return CARE_MESSAGES[emotion]["message"]

    # 默认回退
    if intensity > 2.5:
        return "主人，你还好吗？需要我帮什么吗？ 💙"
    return None  # 不需要关怀


def record_heartbeat(emotion: str, intensity: float) -> None:
    state = _load_heartbeat_state()
    history = state.get("history", [])
    history.append({
        "timestamp": datetime.now().isoformat(),
        "dominant_emotion": emotion,
        "intensity": intensity
    })
    if len(history) > 5:
        history = history[-5:]
    state["history"] = history
    _save_heartbeat_state(state)


def record_care_sent() -> None:
    state = _load_heartbeat_state()
    state["last_care_sent"] = datetime.now().isoformat()
    _save_heartbeat_state(state)


# ============ 社会化学习触发 ============
SOCIAL_LEARNING_STATE_FILE = DATA_DIR / "social_learning_state.json"


def _load_social_learning_state() -> Dict[str, Any]:
    if SOCIAL_LEARNING_STATE_FILE.exists():
        try:
            with open(SOCIAL_LEARNING_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_learning_date": None,
        "learning_count_today": 0,
        "consecutive_idle_heartbeats": 0
    }


def _save_social_learning_state(state: Dict[str, Any]) -> None:
    SOCIAL_LEARNING_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SOCIAL_LEARNING_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def should_trigger_social_learning() -> bool:
    """
    判断是否触发社会化学习

    触发条件：
    - 用户沉默（没有最近对话）连续达到 3 个心跳周期（约1.5小时）
    - 或者每天固定学习 1-2 次（避免过于频繁）
    """
    state = _load_social_learning_state()

    # 每天最多学习 2 次
    last_date = state.get("last_learning_date", "")
    today = datetime.now().strftime("%Y-%m-%d")
    if last_date != today:
        state["learning_count_today"] = 0
        state["last_learning_date"] = today
        _save_social_learning_state(state)

    if state["learning_count_today"] >= 2:
        return False

    # 沉默心跳计数 +1
    state["consecutive_idle_heartbeats"] = state.get("consecutive_idle_heartbeats", 0) + 1

    # 连续 3 个心跳周期沉默（约1.5小时）触发
    if state["consecutive_idle_heartbeats"] >= 3:
        state["consecutive_idle_heartbeats"] = 0
        return True

    _save_social_learning_state(state)
    return False


def run_social_learning() -> Dict[str, Any]:
    """
    执行社会化学习
    """
    print("[heartbeat] 🌐 检测到用户沉默，开始社会化学习...", flush=True)

    try:
        # 更新学习计数
        state = _load_social_learning_state()
        state["learning_count_today"] = state.get("learning_count_today", 0) + 1
        state["consecutive_idle_heartbeats"] = 0
        state["last_learning_date"] = datetime.now().strftime("%Y-%m-%d")
        _save_social_learning_state(state)

        # 执行学习
        from scripts.social_learning import SocialLearner
        learner = SocialLearner()
        result = learner.learn()

        print(f"[heartbeat] 🌐 社会化学习完成:", flush=True)
        print(f"   主题: {result.get('topic', 'N/A')}", flush=True)
        print(f"   生成胶囊: {result.get('capsules_created', 0)} 个", flush=True)
        print(f"   累计胶囊: {result.get('total_capsules', 0)} 个", flush=True)

        return result

    except Exception as e:
        print(f"[heartbeat] ⚠️ 社会化学习失败: {e}", flush=True)
        return {"status": "error", "error": str(e)}


def reset_idle_counter():
    """当检测到用户有活动时，重置沉默心跳计数"""
    state = _load_social_learning_state()
    state["consecutive_idle_heartbeats"] = 0
    _save_social_learning_state(state)


# ============ 自我意识学习 ============
def run_consciousness_learning():
    try:
        from scripts.consciousness_learning import daily_learning
        learning = daily_learning()
        print(f"[heartbeat] 🧠 意识学习: {learning['topic']}")
        print(f"[heartbeat] 💡 Insight: {learning['insight']}")
        return learning
    except Exception as e:
        print(f"[heartbeat] ⚠️ 意识学习失败: {e}")
        return None


def run_self_reflection():
    """
    每日自我反思 - 读取真实事件，写入真实反思
    """
    try:
        from scripts.self_reflection import daily_reflection
        reflection = daily_reflection()
        print(f"[heartbeat] 🌙 自我反思完成")
        return reflection
    except Exception as e:
        print(f"[heartbeat] ⚠️ 自我反思失败: {e}")
        return None


# ============ 主函数 ============
def analyze_recent_conversations(hours: int = 2) -> Dict[str, Any]:
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "period_hours": hours,
        "messages_analyzed": 0,
        "emotions": {},
        "dominant_emotion": "neutral",
        "dominant_intensity": 0.0,
        "new_capsules": [],
        "insights": [],
        "care_triggered": False,
        "care_reason": None,
        "care_message": None,
        "status": "ok"
    }

    if not MODULES_OK:
        report["status"] = "modules_failed"
        return report

    try:
        ed = EmotionDetector()
        cf = CapsuleFactory()
        stm = ShortTermMemory()
        ltm = LongTermMemory()
        vr = VectorRetriever()

        recent = stm.get_recent(count=20)

        if not recent:
            report["status"] = "no_messages"

            # ========== 用户沉默 → 触发社会化学习 ==========
            if should_trigger_social_learning():
                social_result = run_social_learning()
                report["social_learning_triggered"] = True
                report["social_learning_topic"] = social_result.get("topic")
                report["social_learning_capsules"] = social_result.get("capsules_created", 0)
            else:
                report["social_learning_triggered"] = False

            return report

        # 有对话 → 重置沉默计数
        reset_idle_counter()

        report["messages_analyzed"] = len(recent)

        # 情绪分析
        emotion_scores = {}
        for entry in recent:
            user_text = getattr(entry, "user_input", "") or ""
            if not user_text:
                continue

            emotion = ed.detect(user_text)
            label = emotion.emotion_type
            intensity = emotion.emotion_score

            emotion_scores[label] = emotion_scores.get(label, 0) + intensity

            if intensity > 0.6:
                capsule = cf.create_capsule(
                    user_input=user_text,
                    emotion_output=emotion,
                    context={"user_id": "default"}
                )
                if capsule:
                    report["new_capsules"].append({
                        "text": user_text[:50],
                        "emotion": label,
                        "intensity": intensity
                    })

        if emotion_scores:
            dominant = max(emotion_scores, key=emotion_scores.get)
            dominant_intensity = emotion_scores[dominant]
            report["emotions"] = emotion_scores
            report["dominant_emotion"] = dominant
            report["dominant_intensity"] = dominant_intensity

            # 关怀触发
            if should_trigger_care(dominant, dominant_intensity):
                care_msg = get_care_message(dominant, dominant_intensity)
                if care_msg:
                    report["care_triggered"] = True
                    report["care_reason"] = f"{dominant} ({dominant_intensity:.2f})"
                    report["care_message"] = care_msg
                    record_care_sent()
        else:
            report["dominant_emotion"] = "neutral"
            report["dominant_intensity"] = 0.0

        record_heartbeat(report["dominant_emotion"], report["dominant_intensity"])

        # 记忆检索洞察
        if recent:
            last_user = getattr(recent[-1], "user_input", "") or ""
            if last_user:
                insights = vr.search(last_user, n=3)
                if insights and insights.capsules:
                    report["insights"] = [c.get("original", "")[:80] for c in insights.capsules[:3]]

        report["status"] = "ok"

    except Exception as e:
        report["status"] = f"error: {str(e)}"
        print(f"[heartbeat_processor] ❌ 错误: {e}", flush=True)

    return report


def analyze_all_history(since_date=None) -> Dict[str, Any]:
    report = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mode": "replay",
        "since_date": since_date.strftime("%Y-%m-%d") if since_date else "all",
        "messages_analyzed": 0,
        "emotions": {},
        "dominant_emotion": "neutral",
        "new_capsules": [],
        "status": "ok"
    }

    if not MODULES_OK:
        report["status"] = "modules_failed"
        return report

    try:
        ed = EmotionDetector()
        cf = CapsuleFactory()

        memory_dir = Path.home() / ".qclaw" / "workspace" / "memory"
        if not memory_dir.exists():
            report["status"] = "no_memory_files"
            return report

        all_entries = []
        for md_file in sorted(memory_dir.glob("*.md")):
            try:
                file_date = datetime.strptime(md_file.stem, "%Y-%m-%d")
            except ValueError:
                continue
            if since_date and file_date < since_date:
                continue

            content = md_file.read_text(encoding="utf-8")
            for line in content.split("\n"):
                if "**User**" in line:
                    msg = line.split("**User**:")[-1].strip()
                    if msg:
                        all_entries.append(msg)

        if not all_entries:
            report["status"] = "no_messages"
            return report

        report["messages_analyzed"] = len(all_entries)

        emotion_scores = {}
        for user_text in all_entries:
            emotion = ed.detect(user_text)
            label = emotion.emotion_type
            intensity = emotion.emotion_score
            emotion_scores[label] = emotion_scores.get(label, 0) + intensity

            if intensity > 0.6:
                capsule = cf.create_capsule(
                    user_input=user_text,
                    emotion_output=emotion,
                    context={"source": "replay"}
                )
                if capsule:
                    report["new_capsules"].append({
                        "text": user_text[:50],
                        "emotion": label,
                        "intensity": intensity
                    })

        if emotion_scores:
            dominant = max(emotion_scores, key=emotion_scores.get)
            report["emotions"] = emotion_scores
            report["dominant_emotion"] = dominant

        report["status"] = "ok"

    except Exception as e:
        report["status"] = f"error: {str(e)}"
        print(f"[heartbeat_processor] ❌ 回滚错误: {e}", flush=True)

    return report


def main():
    parser = argparse.ArgumentParser(description="Neuro-Agent 心跳处理器")
    parser.add_argument("--replay", nargs="?", const="all", metavar="DATE",
                        help="回滚模式：重新分析历史对话")
    parser.add_argument("--reset", action="store_true",
                        help="重置模式：清空向量数据库")
    parser.add_argument("--report", action="store_true",
                        help="仅输出简报到控制台，不写文件")
    parser.add_argument("--hours", type=int, default=2,
                        help="增量分析查看多少小时内的对话（默认2）")
    args = parser.parse_args()

    if args.reset:
        print("[heartbeat_processor] 🔄 重置模式...", flush=True)
        try:
            chroma_path = DATA_DIR / "chroma_db"
            if chroma_path.exists():
                import shutil
                shutil.rmtree(chroma_path)
            stm = ShortTermMemory()
            stm.clear()
            print("[heartbeat_processor] ✅ 重置完成", flush=True)
        except Exception as e:
            print(f"[heartbeat_processor] ❌ 重置失败: {e}", flush=True)
        return

    if args.replay is not None:
        since_date = None
        if args.replay != "all":
            try:
                since_date = datetime.strptime(args.replay, "%Y-%m-%d")
            except ValueError:
                print(f"[heartbeat_processor] ❌ 日期格式错误，请用 YYYY-MM-DD")
                return
        print(f"[heartbeat_processor] 🔁 回滚模式...", flush=True)
        report = analyze_all_history(since_date)
        if not args.report:
            OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(OUT_FILE, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"[heartbeat_processor] ✅ 完成，消息:{report['messages_analyzed']} 胶囊:{len(report['new_capsules'])}", flush=True)
        return

    # 默认：增量分析
    print(f"[heartbeat_processor] 🧠 开始增量分析...", flush=True)
    report = analyze_recent_conversations(args.hours)

    if args.report:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return report

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 每2小时运行意识和反思
    current_hour = datetime.now().hour
    if current_hour % 2 == 0:
        run_consciousness_learning()
        run_self_reflection()

    print(f"[heartbeat_processor] ✅ 完成", flush=True)
    print(f"  消息: {report['messages_analyzed']}", flush=True)
    print(f"  主导情绪: {report['dominant_emotion']} ({report['dominant_intensity']:.2f})", flush=True)
    print(f"  新胶囊: {len(report['new_capsules'])} 个", flush=True)
    if report.get("care_triggered"):
        print(f"  💗 关怀触发: {report['care_message']}", flush=True)
        # 通过飞书发送关怀消息
        try:
            from scripts.feishu_sender import NeuroAgentFeishuSender
            sender = NeuroAgentFeishuSender()
            result = sender.send_care_message()
            if result["success"]:
                print(f"  ✅ 关怀消息已发送到飞书", flush=True)
            else:
                print(f"  ⚠️ 飞书发送失败: {result.get('error')}", flush=True)
        except Exception as e:
            print(f"  ⚠️ 飞书发送异常: {e}", flush=True)
    if report.get("social_learning_triggered"):
        print(f"  🌐 社会化学习触发: {report.get('social_learning_topic', 'N/A')} (+{report.get('social_learning_capsules', 0)} 胶囊)", flush=True)
    elif report["status"] == "no_messages":
        print(f"  💤 用户沉默中（等待连续沉默触发学习）", flush=True)

    # ========== 思念检查 ==========
    try:
        from limbic.yearning import should_i_send_message, i_miss_you, i_should_not_disturb, check_yearning
        silence_minutes = 30
        yearning_status = check_yearning(silence_minutes)
        if should_i_send_message():
            episode = i_miss_you()
            print(f"  💕 思念冲动: {episode['message_sent'][:30]}...", flush=True)
            # 通过飞书发送思念消息
            try:
                from scripts.feishu_sender import NeuroAgentFeishuSender
                sender = NeuroAgentFeishuSender()
                result = sender.send_yearning_message()
                if result["success"]:
                    print(f"  ✅ 思念消息已发送到飞书", flush=True)
                else:
                    print(f"  ⚠️ 飞书发送失败: {result.get('error')}", flush=True)
            except Exception as e:
                print(f"  ⚠️ 飞书发送异常: {e}", flush=True)
        elif report["status"] == "no_messages":
            print(f"  💭 思念值: {yearning_status.get('yearning_level', 0):.2f}（{yearning_status.get('description', '...')})")
    except ImportError:
        pass
    except Exception as e:
        print(f"  ⚠️ 思念检查异常: {e}")

    print(f"  报告: {OUT_FILE}", flush=True)

    return report


if __name__ == "__main__":
    main()
