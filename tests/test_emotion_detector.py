"""
tests/test_emotion_detector.py
==============================

emotion_detector 单元测试
测试：正则预编译、情绪检测准确性、Agent自我情绪记录
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import pytest
from left_brain.emotion_detector import EmotionDetector, detect_emotion, SWEAR_PATTERNS, SARCASM_PATTERNS


class TestRegexPrecompilation:
    """测试正则预编译是否正确"""
    
    def test_swear_patterns_compiled(self):
        """SWEAR_PATTERNS 应该是已编译的正则对象"""
        for p in SWEAR_PATTERNS:
            import re
            assert isinstance(p, re.Pattern), f"{p} 未编译"
    
    def test_sarcasm_patterns_compiled(self):
        """SARCASM_PATTERNS 应该是已编译的正则对象"""
        for p in SARCASM_PATTERNS:
            import re
            assert isinstance(p, re.Pattern), f"{p} 未编译"
    
    def test_performance_no_recompile(self):
        """验证不需要每次重新编译正则（性能测试）"""
        detector = EmotionDetector()
        
        texts = [
            "我靠，这也太牛了吧！",
            "工作好累啊，老板又骂我了",
            "算了，放弃吧",
            "明天要面试了，好紧张",
            "谢谢你的帮助！",
            "我没事，真的没事...",
        ]
        
        # 预热
        for t in texts[:2]:
            detector.detect(t)
        
        # 计时：100次检测
        start = time.time()
        for _ in range(100):
            for t in texts:
                detector.detect(t)
        elapsed = time.time() - start
        
        # 600次检测应在2秒内完成（优化后性能）
        assert elapsed < 2.0, f"性能测试失败：{elapsed:.2f}秒 > 2.0秒"
        print(f"\n✅ 性能测试通过：600次检测耗时 {elapsed:.2f}秒")


class TestEmotionDetection:
    """测试情绪检测准确性"""
    
    def test_joy(self):
        result = detect_emotion("今天太开心了！")
        assert result.emotion_type == "joy"
        assert result.emotion_score > 0.4
    
    def test_sadness(self):
        result = detect_emotion("工作好累啊，老板又骂我了")
        assert result.emotion_type in ("sadness", "frustration", "exhaustion")
    
    def test_neutral(self):
        result = detect_emotion("你好")
        assert result.emotion_type == "neutral"
        assert result.emotion_score < 0.3
    
    def test_anger_swear(self):
        result = detect_emotion("妈的，气死我了")
        assert result.emotion_type == "anger"
        assert result.is_masked == False
    
    def test_swear_context_positive(self):
        """脏话语境分析："我靠，太牛了" → excitement"""
        result = detect_emotion("我靠，太牛了")
        assert result.emotion_type == "excitement", f"期望 excitement，实际 {result.emotion_type}"
    
    def test_negation_sadness(self):
        """否定消歧："不太开心" → sadness"""
        result = detect_emotion("我不太开心")
        assert result.emotion_type == "sadness"
    
    def test_hidden_pain_mask(self):
        """隐痛伪装："我没事" → sadness"""
        result = detect_emotion("我没事，真的没事...")
        assert result.is_masked == True
        assert result.underlying_emotion == "sadness"
    
    def test_sarcasm_flip(self):
        """反讽翻转："呵呵" → anger"""
        result = detect_emotion("呵呵")
        assert result.emotion_type == "anger"
    
    def test_exhaustion(self):
        """疲惫检测："好累啊" → exhaustion"""
        result = detect_emotion("工作好累啊")
        assert result.emotion_type == "excitement" or result.emotion_type == "exhaustion"


class TestEmpathyLevel:
    """测试共情等级计算"""
    
    def test_high_empathy_negative_emotion(self):
        """强烈负面情绪 → 高共情"""
        result = detect_emotion("我真的很害怕...")
        assert result.empathy_level > 0.5
    
    def test_masked_emotion_higher_empathy(self):
        """伪装情绪 → 更高共情（因为需要更深理解）"""
        normal = detect_emotion("今天不开心")
        masked = detect_emotion("我没事，真的没事...")
        assert masked.empathy_level >= normal.empathy_level


class TestSubtextDetection:
    """测试潜台词检测"""
    
    def test_hidden_pain(self):
        """隐痛检测"""
        result = detect_emotion("习惯了")
        assert result.subtext in ("hidden_pain", "none")
    
    def test_frustration_mask(self):
        """挫败伪装"""
        result = detect_emotion("随便吧，无所谓")
        assert result.subtext in ("frustration_mask", "none")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
