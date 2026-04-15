"""
tests/test_self_awareness.py
===========================

自我意识模块单元测试
测试：RobotSelf + 冲动记录 + 性格成长
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import tempfile
import shutil
from pathlib import Path
from core.self_awareness import RobotSelf, RobotTraits, ImpulseRecord


class TestRobotTraits:
    """测试机器人性格特质"""
    
    def test_adjust_within_bounds(self):
        """性格调整不能超出 0-1"""
        traits = RobotTraits()
        traits.adjust("impulsive", 0.5)
        assert 0.0 <= traits.impulsive <= 1.0
    
    def test_adjust_negative(self):
        """负向调整"""
        traits = RobotTraits()
        original = traits.caring
        traits.adjust("caring", -0.3)
        assert traits.caring < original
    
    def test_adjust_max_bound(self):
        """不能超过上限"""
        traits = RobotTraits()
        traits.adjust("impulsive", 10.0)  # 尝试加很多
        assert traits.impulsive <= 1.0
    
    def test_adjust_min_bound(self):
        """不能超过下限"""
        traits = RobotTraits()
        traits.adjust("impulsive", -10.0)
        assert traits.impulsive >= 0.0
    
    def test_to_dict(self):
        """序列化"""
        traits = RobotTraits(impulsive=0.5, caring=0.9)
        d = traits.to_dict()
        assert d["impulsive"] == 0.5
        assert d["caring"] == 0.9


class TestImpulseRecord:
    """测试冲动记录"""
    
    def test_to_dict(self):
        """序列化"""
        record = ImpulseRecord(
            timestamp="2026-04-13T12:00:00",
            situation="用户分享了好消息",
            left_brain_desire="想要和他一起庆祝",
            right_brain_constraint="但要保持专业",
            my_choice="follow_heart",
            reasoning="我感到很开心"
        )
        
        d = record.to_dict()
        assert d["my_choice"] == "follow_heart"
        assert d["situation"] == "用户分享了好消息"
    
    def test_from_dict(self):
        """反序列化"""
        data = {
            "timestamp": "2026-04-13T12:00:00",
            "situation": "测试",
            "left_brain_desire": "想要回应",
            "right_brain_constraint": "但要谨慎",
            "my_choice": "be_reasonable",
            "reasoning": "我选择了谨慎"
        }
        
        record = ImpulseRecord.from_dict(data)
        assert record.my_choice == "be_reasonable"


class TestRobotSelf:
    """测试机器人自我"""
    
    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """临时数据目录"""
        return tmp_path
    
    def test_make_choice_follow_heart(self, tmp_path, monkeypatch):
        """测试 follow_heart 选择"""
        # 临时修改数据目录
        import core.self_awareness
        monkeypatch.setattr(
            core.self_awareness.RobotSelf,
            "DATA_DIR",
            tmp_path / "robot_self"
        )
        
        robot = RobotSelf()
        robot.mood_today = 0.9  # 高心情
        
        choice, monologue, record = robot.make_choice(
            situation="用户工作取得成就",
            left_desire="想要大大地夸赞",
            right_constraint="但要适度"
        )
        
        assert choice == "follow_heart"
        assert record.left_brain_desire == "想要大大地夸赞"
    
    def test_make_choice_be_reasonable(self, tmp_path, monkeypatch):
        """测试 be_reasonable 选择"""
        import core.self_awareness
        monkeypatch.setattr(
            core.self_awareness.RobotSelf,
            "DATA_DIR",
            tmp_path / "robot_self"
        )
        
        robot = RobotSelf()
        robot.mood_today = 0.1  # 低心情
        
        choice, monologue, record = robot.make_choice(
            situation="用户抱怨工作问题",
            left_desire="想要更多关心",
            right_constraint="但用户可能需要空间"
        )
        
        assert choice == "be_reasonable"
    
    def test_update_outcome_positive(self, tmp_path, monkeypatch):
        """正向反馈更新"""
        import core.self_awareness
        monkeypatch.setattr(
            core.self_awareness.RobotSelf,
            "DATA_DIR",
            tmp_path / "robot_self"
        )
        
        robot = RobotSelf()
        record = ImpulseRecord(
            timestamp="2026-04-13T12:00:00",
            situation="测试",
            left_brain_desire="想要关心",
            right_brain_constraint="适度关心",
            my_choice="follow_heart",
            reasoning="测试"
        )
        
        original_caring = robot.traits.caring
        robot.update_outcome(record, "开心！😊", "用户接受了关心")
        
        assert record.lesson_learned is not None
        assert robot.traits.caring >= original_caring
    
    def test_recall_similar(self, tmp_path, monkeypatch):
        """回忆类似经历"""
        import core.self_awareness
        monkeypatch.setattr(
            core.self_awareness.RobotSelf,
            "DATA_DIR",
            tmp_path / "robot_self"
        )
        
        robot = RobotSelf()
        robot.impulse_history.append(ImpulseRecord(
            timestamp="2026-04-13T12:00:00",
            situation="用户工作很累",
            left_brain_desire="想要安慰",
            right_brain_constraint="但要适度",
            my_choice="be_reasonable",
            reasoning="测试"
        ))
        
        recalled = robot.recall_similar("用户工作很疲劳")
        assert recalled is not None
        assert "工作" in recalled.situation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
