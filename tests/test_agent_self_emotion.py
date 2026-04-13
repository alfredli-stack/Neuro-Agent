"""
tests/test_agent_self_emotion.py
================================

Agent 自我情绪记录单元测试
测试：AgentEmotionalState + 接入 input_processor
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.interfaces import AgentEmotionalState, AgentMood


class TestAgentEmotionalState:
    """测试 Agent 情绪状态"""
    
    def test_record_mood(self):
        """记录情绪"""
        state = AgentEmotionalState()
        state.record(AgentMood.JOYFUL, 0.7, "用户很开心，我被感染了", confidence=0.8)
        
        assert state.current_mood == AgentMood.JOYFUL
        assert state.mood_intensity == 0.7
        assert state.trigger_reason == "用户很开心，我被感染了"
        assert state.confidence == 0.8
    
    def test_reflect(self):
        """生成自我反思"""
        state = AgentEmotionalState()
        state.record(AgentMood.CONCERNED, 0.6, "用户难过了", confidence=0.7)
        
        reflection = state.reflect()
        assert "关切" in reflection or "CONCERNED" in reflection
    
    def test_mood_history(self):
        """情绪历史记录"""
        state = AgentEmotionalState()
        state.record(AgentMood.NEUTRAL, 0.3, "日常对话", confidence=0.5)
        state.record(AgentMood.JOYFUL, 0.6, "用户分享了好事", confidence=0.7)
        
        history = state.get_recent_moods(5)
        assert len(history) == 2
        assert history[1]["mood"] == "joyful"
    
    def test_mood_history_limit(self):
        """情绪历史最多保留50条"""
        state = AgentEmotionalState()
        for i in range(60):
            state.record(AgentMood.NEUTRAL, 0.3, f"记录{i}")
        
        assert len(state.mood_history) <= 50
    
    def test_infer_mood_from_user_joy(self):
        """用户开心 → Agent 镜像愉悦"""
        state = AgentEmotionalState()
        state.infer_mood_from_user("joy", "casual_chat")
        
        assert state.current_mood == AgentMood.JOYFUL
    
    def test_infer_mood_from_user_sadness(self):
        """用户悲伤 → Agent 关切"""
        state = AgentEmotionalState()
        state.infer_mood_from_user("sadness", "emotional_vent")
        
        assert state.current_mood == AgentMood.CONCERNED
    
    def test_infer_mood_from_user_anger(self):
        """用户愤怒 → Agent 谨慎"""
        state = AgentEmotionalState()
        state.infer_mood_from_user("anger", "emotional_vent")
        
        assert state.current_mood == AgentMood.CAUTIOUS
    
    def test_infer_mood_low_confidence(self):
        """Agent 不确定时 → 困惑"""
        state = AgentEmotionalState()
        state.infer_mood_from_user("confusion", "question", agent_confidence=0.3)
        
        assert state.current_mood == AgentMood.CONFUSED
    
    def test_to_dict(self):
        """序列化为字典"""
        state = AgentEmotionalState()
        state.record(AgentMood.REFLECTIVE, 0.6, "深入思考中", confidence=0.6)
        
        d = state.to_dict()
        assert "current_mood" in d
        assert d["current_mood"] == "reflective"
        assert "trigger_reason" in d


class TestAgentMoodEnum:
    """测试 Agent 情绪枚举"""
    
    def test_all_moods_have_value(self):
        """所有情绪都有 string value"""
        for mood in AgentMood:
            assert isinstance(mood.value, str)
            assert len(mood.value) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
