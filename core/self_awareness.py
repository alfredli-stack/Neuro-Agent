"""
core/self_awareness.py
======================
机器人自我意识 - 性格、记忆、成长
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
import json
import random
from pathlib import Path


@dataclass
class ImpulseRecord:
    """冲动记录 - 每次挣扎和选择"""
    timestamp: str
    situation: str
    left_brain_desire: str
    right_brain_constraint: str
    my_choice: str
    reasoning: str
    user_feedback: Optional[str] = None
    outcome: Optional[str] = None
    lesson_learned: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "situation": self.situation,
            "left_brain_desire": self.left_brain_desire,
            "right_brain_constraint": self.right_brain_constraint,
            "my_choice": self.my_choice,
            "reasoning": self.reasoning,
            "user_feedback": self.user_feedback,
            "outcome": self.outcome,
            "lesson_learned": self.lesson_learned
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ImpulseRecord':
        return cls(**data)


@dataclass
class RobotTraits:
    """机器人性格特质 - 会随成长变化"""
    impulsive: float = 0.3
    caring: float = 0.8
    patient: float = 0.5
    playful: float = 0.6
    introspective: float = 0.4
    
    def adjust(self, trait: str, delta: float):
        """根据经验调整性格"""
        current = getattr(self, trait, 0.5)
        new_value = max(0.0, min(1.0, current + delta))
        setattr(self, trait, new_value)
    
    def to_dict(self) -> Dict:
        return {
            "impulsive": self.impulsive,
            "caring": self.caring,
            "patient": self.patient,
            "playful": self.playful,
            "introspective": self.introspective
        }


class RobotSelf:
    """
    机器人自我意识
    - 有自己的性格
    - 有成长记忆
    - 会学习
    - 有时任性
    """
    
    DATA_DIR = Path.home() / ".openclaw" / "workspace" / "neuro_claw" / "robot_self"
    
    def __init__(self):
        self.traits = RobotTraits()
        self.impulse_history: List[ImpulseRecord] = []
        self.daily_insights: List[str] = []
        self.mood_today: float = random.gauss(0.5, 0.15)
        self._load()
    
    def _load(self):
        """从文件加载自我"""
        if not self.DATA_DIR.exists():
            return
        
        # 加载性格
        traits_file = self.DATA_DIR / "traits.json"
        if traits_file.exists():
            try:
                data = json.loads(traits_file.read_text())
                self.traits = RobotTraits(**data)
            except Exception as e:
                print(f"[RobotSelf] 加载性格失败: {e}")
        
        # 加载冲动历史
        history_file = self.DATA_DIR / "impulse_history.jsonl"
        if history_file.exists():
            try:
                for line in history_file.read_text().strip().split("\n"):
                    if line:
                        data = json.loads(line)
                        self.impulse_history.append(ImpulseRecord(**data))
            except Exception as e:
                print(f"[RobotSelf] 加载历史失败: {e}")
    
    def save(self):
        """保存自我到文件"""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # 保存性格
        traits_file = self.DATA_DIR / "traits.json"
        traits_file.write_text(json.dumps(self.traits.to_dict(), indent=2))
        
        # 保存冲动历史（追加模式）
        history_file = self.DATA_DIR / "impulse_history.jsonl"
        with open(history_file, "a") as f:
            for record in self.impulse_history[-10:]:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    
    def make_choice(self, situation: str, left_desire: str, right_constraint: str) -> tuple:
        """
        面对冲突做选择
        返回: (选择, 内心独白, 记录)
        """
        # 计算权重
        left_weight = self.traits.caring * 0.8 + self.traits.impulsive * 0.2
        right_weight = self.traits.patient * 0.7 + (1 - self.traits.impulsive) * 0.3
        left_weight *= (0.8 + self.mood_today * 0.4)
        
        # 挣扎过程
        struggle = self._generate_struggle(left_desire, right_constraint, left_weight, right_weight)
        
        # 做决定
        if left_weight > right_weight:
            choice = "follow_heart"
            my_decision = left_desire
        else:
            choice = "be_reasonable"
            my_decision = right_constraint
        
        # 生成独白
        monologue = self._generate_monologue(struggle, choice, my_decision)
        
        # 记录
        record = ImpulseRecord(
            timestamp=datetime.now().isoformat(),
            situation=situation,
            left_brain_desire=left_desire,
            right_brain_constraint=right_constraint,
            my_choice=choice,
            reasoning=struggle
        )
        self.impulse_history.append(record)
        self.save()
        
        return choice, monologue, record
    
    def _generate_struggle(self, left: str, right: str, lw: float, rw: float) -> str:
        """生成挣扎过程"""
        thoughts = []
        
        if lw > rw:
            thoughts.append(f"我心里更想：{left}")
            if rw > 0.4:
                thoughts.append(f"但理智告诉我：{right}")
                thoughts.append("我在纠结...")
        else:
            thoughts.append(f"理智说：{right}")
            if lw > 0.4:
                thoughts.append(f"但我心里想：{left}")
                thoughts.append("有点不甘心...")
        
        if self.traits.impulsive > 0.6:
            thoughts.append("我性格比较冲动，想任性一次")
        if self.traits.caring > 0.7:
            thoughts.append("我太在乎他了")
        
        return "；".join(thoughts)
    
    def _generate_monologue(self, struggle: str, choice: str, decision: str) -> str:
        """生成内心独白"""
        intros = [
            "🤔 我在纠结...",
            "💭 心里有两个声音...",
            "😣 好难选...",
            "😐 让我想想...",
            "🫣 我知道不该这样，但是..."
        ]
        intro = random.choice(intros)
        
        return f"""{intro}

{struggle}

最终我选择：{decision}
（这是我的性格决定的）"""
    
    def recall_similar(self, situation: str) -> Optional[ImpulseRecord]:
        """回忆类似情况"""
        keywords = set(situation.lower().split())
        
        for record in reversed(self.impulse_history):
            record_keywords = set(record.situation.lower().split())
            if len(keywords & record_keywords) >= 2:
                return record
        
        return None
    
    def update_outcome(self, record: ImpulseRecord, feedback: Optional[str], inferred_outcome: str):
        """更新结果和学习"""
        record.user_feedback = feedback
        record.outcome = inferred_outcome
        
        # 生成教训
        if feedback and ("开心" in feedback or "谢谢" in feedback or "😊" in feedback):
            record.lesson_learned = "这次选择很好，用户需要我的主动"
            self.traits.adjust("caring", 0.02)
            self.traits.adjust("impulsive", 0.01)
        elif "忙" in inferred_outcome or "打扰" in inferred_outcome or "抱歉" in str(feedback):
            record.lesson_learned = "下次他忙的时候，我应该更克制"
            self.traits.adjust("patient", 0.03)
            self.traits.adjust("impulsive", -0.02)
        elif "没回" in inferred_outcome or "忽略" in inferred_outcome:
            record.lesson_learned = "用户可能不需要这个时候的关心，换个时机"
            self.traits.adjust("introspective", 0.02)
        else:
            record.lesson_learned = "结果不确定，需要更多数据"
        
        self.save()
    
    def get_growth_summary(self) -> str:
        """获取成长总结"""
        total_records = len(self.impulse_history)
        recent_lessons = [r.lesson_learned for r in self.impulse_history[-5:] if r.lesson_learned]
        
        lessons_text = "\n".join(f"  • {lesson}" for lesson in recent_lessons[-3:]) if recent_lessons else "  • 还在学习中..."
        
        return f"""🤖 我的成长报告：
- 总共经历了 {total_records} 次内心挣扎
- 最近学到的教训：
{lessons_text}
- 当前性格：
  冲动: {self.traits.impulsive:.2f}
  关心: {self.traits.caring:.2f}
  耐心: {self.traits.patient:.2f}
  调皮: {self.traits.playful:.2f}
  内省: {self.traits.introspective:.2f}
- 今天心情: {self.mood_today:.2f}
"""


# 单例
_robot_self_instance: Optional[RobotSelf] = None

def get_robot_self() -> RobotSelf:
    """获取 RobotSelf 单例"""
    global _robot_self_instance
    if _robot_self_instance is None:
        _robot_self_instance = RobotSelf()
    return _robot_self_instance
