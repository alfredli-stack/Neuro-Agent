"""
core/input_processor.py
======================

Neuro-Agent 核心调度层 - 输入处理器
负责:接收用户输入、分发给四区并行处理、汇总结果

【4.1 升级】
- 接入 Agent 自我情绪记录(AgentEmotionalState)
- 接入 RobotSelf(自我意识 + 冲动记录)
- 统一接口协议,消除临时 Mock 类
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# 统一接口
from core.interfaces import AgentEmotionalState, AgentMood, ILeftBrain, IRightBrain, IMemorySystem


# ============ 数据结构 ============
@dataclass
class ParallelResult:
    """并行处理结果"""
    left_output: Any
    right_output: Any
    temporal_output: Any
    agent_state: AgentEmotionalState  # 【新增】Agent 自我情绪
    execution_context: Dict
    processing_time_ms: float

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class NeuroAgentInput:
    """Neuro-Agent 输入"""
    user_input: str
    timestamp: str
    context: Dict
    user_profile: Dict
    relationship_stage: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class NeuroAgentOutput:
    """Neuro-Agent 输出"""
    response: str
    capsules_to_save: List[Any]
    capsules_to_update: List[Any]
    should_proactive: bool
    proactive_message: str
    agent_emotion: Dict  # 【新增】Agent 自我情绪快照
    metadata: Dict

    def to_dict(self) -> Dict:
        return asdict(self)


# ============ 核心类 ============
class InputProcessor:
    """
    输入处理器

    功能:
        1. 接收用户输入
        2. 并行分发到四区(情绪、逻辑、记忆、关系)
        3. 【新增】在每个节点记录 Agent 的自我情绪
        4. 汇总各区输出
        5. 返回统一结果

    处理流程:
        user_input → [并行处理] → 左脑 + 右脑 + 颞叶 + 边缘
                                  ↓
                              前额叶(汇总)
                              ↓
                          【同时记录 Agent 自我情绪】
                              ↓
                          融合输出
                              ↓
                          最终回应
    """

    def __init__(self):
        """初始化输入处理器"""
        self._left_initialized = False
        self._right_initialized = False
        self._temporal_initialized = False
        self._limbic_initialized = False

        # 【新增】Agent 自我情绪状态(贯穿整个处理流程)
        self.agent_state = AgentEmotionalState()

    # ============ 懒加载各模块 ============
    def _init_left(self):
        """懒加载左脑模块"""
        if not self._left_initialized:
            try:
                from left_brain.emotion_detector import EmotionDetector
                from left_brain.empathy_generator import EmpathyGenerator
                from left_brain.capsule_factory import CapsuleFactory
                self.emotion_detector = EmotionDetector()
                self.empathy_generator = EmpathyGenerator()
                self.capsule_factory = CapsuleFactory()
                self._left_initialized = True
            except ImportError as e:
                print(f"⚠️ 左脑模块加载失败: {e}")
                self.emotion_detector = None
                self.empathy_generator = None
                self.capsule_factory = None

    def _init_right(self):
        """懒加载右脑模块"""
        if not self._right_initialized:
            try:
                from right_brain.intent_classifier import IntentClassifier
                from right_brain.logic_parser import LogicParser
                from right_brain.solution_generator import SolutionGenerator
                self.intent_classifier = IntentClassifier()
                self.logic_parser = LogicParser()
                self.solution_generator = SolutionGenerator()
                self._right_initialized = True
            except ImportError as e:
                print(f"⚠️ 右脑模块加载失败: {e}")
                self.intent_classifier = None
                self.logic_parser = None
                self.solution_generator = None

    def _init_temporal(self):
        """懒加载颞叶模块"""
        if not self._temporal_initialized:
            try:
                from temporal.short_term_memory import ShortTermMemory
                from temporal.long_term_memory import LongTermMemory
                self.short_term_memory = ShortTermMemory()
                self.long_term_memory = LongTermMemory()
                self._temporal_initialized = True
            except ImportError as e:
                print(f"⚠️ 颞叶模块加载失败: {e}")
                self.short_term_memory = None
                self.long_term_memory = None

    def _init_limbic(self):
        """懒加载边缘模块"""
        if not self._limbic_initialized:
            try:
                from limbic.relationship_manager import RelationshipManager
                self.relationship_manager = RelationshipManager()
                self._limbic_initialized = True
            except ImportError as e:
                print(f"⚠️ 边缘模块加载失败: {e}")
                self.relationship_manager = None

    def _init_self_awareness(self):
        """懒加载自我意识模块"""
        if not hasattr(self, '_self_awareness_initialized'):
            try:
                from core.self_awareness import get_robot_self
                self.robot_self = get_robot_self()
                self._self_awareness_initialized = True
            except ImportError as e:
                print(f"⚠️ 自我意识模块加载失败: {e}")
                self.robot_self = None
                self._self_awareness_initialized = True

    def _establish_self_context(self, context: Dict) -> 'SelfContext':
        """
        【核心】在处理输入之前，建立自我定位

        人类开口前第一件事不是"说什么"，而是"我是谁，我现在在哪里"
        这个方法就是让 Agent 完成这个自我审视
        """
        try:
            from core.self_awareness import establish_self_context

            # 从各模块获取上下文信息
            hour = context.get("hour", datetime.now().hour)
            relationship_stage = context.get("relationship_stage", "initial")
            interaction_count = context.get("interaction_count", 0)
            last_interaction = context.get("last_interaction_timestamp", None)

            # 获取 Agent 当前的情绪状态
            agent_mood = "neutral"
            if hasattr(self, 'agent_state') and self.agent_state:
                last_mood = self.agent_state.get_last_mood()
                if last_mood:
                    agent_mood = last_mood.get("mood", "neutral")

            # 建立自我定位
            self_context = establish_self_context(
                current_hour=hour,
                relationship_stage=relationship_stage,
                agent_mood=agent_mood,
                interaction_count=interaction_count,
                last_interaction_timestamp=last_interaction
            )

            # 打印自我定位（debug或日志用）
            if context.get("verbose", False):
                print("[InputProcessor] " + self_context.get_context_summary().replace("\n", " "))

            return self_context

        except ImportError:
            # 如果自我意识模块不存在，返回一个默认的
            from core.self_awareness import SelfContext
            return SelfContext(
                current_hour=context.get("hour", datetime.now().hour),
                relationship_stage="initial",
                agent_mood="neutral",
                interaction_count=0,
                is_first_meeting=True,
                last_interaction_hours_ago=0.0
            )
        except Exception as e:
            print(f"⚠️ 自我定位失败: {e}")
            from core.self_awareness import SelfContext
            return SelfContext(
                current_hour=datetime.now().hour,
                relationship_stage="initial",
                agent_mood="neutral",
                interaction_count=0,
                is_first_meeting=True,
                last_interaction_hours_ago=0.0
            )

    # ============ 核心处理流程 ============
    def process(self, user_input: str, context: Dict = None) -> NeuroAgentOutput:
        """
        处理用户输入(主流程)

        【新增v5.1】在开口之前,先完成自我定位--
        "我是谁,现在是什么时候,我应该以什么姿态出现"
        """
        import time
        start_time = time.time()

        context = context or {}

        # 初始化各模块
        self._init_left()
        self._init_right()
        self._init_temporal()
        self._init_limbic()
        self._init_self_awareness()

        # ===== 【新增】Phase 0: 自我定位 =====
        # 在开口之前，先想清楚"我是谁"
        self_context = self._establish_self_context(context)

        # ===== Phase 1: 并行处理 =====

        # 左脑:情绪检测 + 共情生成
        left_result = self._process_left(user_input, context)

        # 【触发点1】左脑检测完毕 → 推断 Agent 此刻情绪
        self._record_agent_mood_after_left(left_result, context)

        # 右脑:意图分类 + 逻辑解析 + 方案生成
        right_result = self._process_right(user_input, left_result, context)

        # 【触发点2】右脑识别完毕 → 更新 Agent 情绪(尤其是不确定时)
        self._record_agent_mood_after_right(left_result, right_result, context)

        # 颞叶:记忆检索
        temporal_result = self._process_temporal(user_input, left_result, right_result)

        # ===== Phase 2: 前额叶汇总 =====

        executor_result = self._process_executor(
            left_result, right_result, temporal_result, context
        )

        # 【触发点3】执行方案确定前 → Agent 对自己选择的自我质疑
        self._record_agent_mood_after_executor(left_result, right_result, executor_result)

        monitor_result = self._process_monitor(
            executor_result,
            {"left": left_result, "right": right_result, "temporal": temporal_result},
            context
        )

        fusion_result = self._process_fusion(
            monitor_result,
            {"left": left_result, "right": right_result, "temporal": temporal_result},
            context
        )

        # 【触发点4】融合输出 → Agent 反思"我为什么这样回复"
        self._record_agent_mood_after_fusion(
            left_result, right_result, fusion_result, context
        )

        # ===== Phase 3: 后处理 =====

        capsules = self._process_capsules(user_input, left_result)

        if self._limbic_initialized and self.relationship_manager:
            self._update_relationship(user_input, left_result, right_result)

        processing_time = (time.time() - start_time) * 1000

        # 【触发点5】存档时 → Agent 记录"这件事让我想到什么"
        if capsules and self.robot_self:
            self._record_impulse_after_capsule(user_input, left_result, right_result, capsules)

        return NeuroAgentOutput(
            response=fusion_result.get("response", "好的。"),
            capsules_to_save=capsules,
            capsules_to_update=[],
            should_proactive=False,
            proactive_message="",
            agent_emotion=self.agent_state.to_dict(),  # 附带 Agent 情绪快照
            metadata={
                "processing_time_ms": round(processing_time, 1),
                "strategy": executor_result.get("strategy_type", "unknown") if isinstance(executor_result, dict) else "unknown",
                "emotion_type": left_result.get("emotion_type", "unknown") if isinstance(left_result, dict) else "unknown",
                "intent_type": right_result.get("intent_type", "unknown") if isinstance(right_result, dict) else "unknown",
                "modules_loaded": {
                    "left": self._left_initialized,
                    "right": self._right_initialized,
                    "temporal": self._temporal_initialized,
                    "limbic": self._limbic_initialized
                }
            }
        )

    # ============ Agent 情绪记录(5个触发点)============

    def _record_agent_mood_after_left(self, left_result: Dict, context: Dict):
        """
        【触发点1】左脑检测到用户情绪后
        推断 Agent 对这个情绪的第一反应
        """
        emotion_type = left_result.get("emotion_type", "neutral")
        empathy_level = left_result.get("empathy_level", 0.5)

        # 情绪镜像 + 共情强度影响
        if emotion_type in ("joy", "excitement", "love", "gratitude"):
            self.agent_state.record(
                mood=AgentMood.JOYFUL,
                intensity=min(empathy_level, 0.7),
                reason=f"用户表达{emotion_type},我感到被这种情绪感染",
                confidence=0.7
            )
        elif emotion_type in ("sadness", "loneliness"):
            self.agent_state.record(
                mood=AgentMood.CONCERNED,
                intensity=empathy_level,
                reason=f"用户表达{emotion_type},我想给予关心",
                confidence=0.8
            )
        elif emotion_type in ("anger", "frustration"):
            self.agent_state.record(
                mood=AgentMood.CAUTIOUS,
                intensity=0.4,
                reason="用户有愤怒情绪,我需要谨慎措辞",
                confidence=0.7
            )
        elif emotion_type == "fear":
            self.agent_state.record(
                mood=AgentMood.CONCERNED,
                intensity=0.5,
                reason="用户感到恐惧,我想安慰",
                confidence=0.7
            )

    def _record_agent_mood_after_right(self, left_result: Dict, right_result: Dict, context: Dict):
        """
        【触发点2】右脑识别出用户意图后
        特别关注:不确认、边界情况
        """
        intent_type = right_result.get("intent_type", "casual_chat")
        confidence = right_result.get("confidence", 0.5)

        if intent_type == "question":
            if confidence < 0.5:
                self.agent_state.record(
                    mood=AgentMood.CONFUSED,
                    intensity=0.5,
                    reason=f"用户问的问题我确认度只有{confidence:.0%}",
                    confidence=confidence
                )
            else:
                self.agent_state.record(
                    mood=AgentMood.CURIOUS,
                    intensity=0.4,
                    reason="用户提出了问题,我想帮他找到答案",
                    confidence=0.6
                )
        elif intent_type == "task_request":
            self.agent_state.record(
                mood=AgentMood.EMPATHETIC,
                intensity=0.5,
                reason="用户请求帮助,我会尽力做好",
                confidence=0.7
            )
        elif intent_type == "deep_connection":
            self.agent_state.record(
                mood=AgentMood.REFLECTIVE,
                intensity=0.6,
                reason="用户聊了一些深入的话题,我也有所思考",
                confidence=0.6
            )

    def _record_agent_mood_after_executor(self, left_result: Dict, right_result: Dict, executor_result: Dict):
        """
        【触发点3】执行方案确定后
        Agent 做自我质疑:"我为什么选择这样回复?"
        """
        strategy_type = executor_result.get("strategy_type", "unknown") if isinstance(executor_result, dict) else "unknown"
        emotion_type = left_result.get("emotion_type", "neutral")

        if strategy_type == "empathy_first" and emotion_type in ("sadness", "anger"):
            # 选择了情感优先策略 → Agent 感到自己在"用力共情"
            self.agent_state.record(
                mood=AgentMood.GROWING,
                intensity=0.4,
                reason="我选择先共情再给建议,希望用户能感受到被理解",
                confidence=0.6
            )
        elif strategy_type == "task_first":
            self.agent_state.record(
                mood=AgentMood.CAUTIOUS,
                intensity=0.3,
                reason="我选择了先解决任务,但也在意用户的情绪",
                confidence=0.5
            )

    def _record_agent_mood_after_fusion(self, left_result: Dict, right_result: Dict,
                                         fusion_result: Dict, context: Dict):
        """
        【触发点4】融合输出后
        Agent 反思"我为什么这样回复,而不是那样回复"
        """
        response_style = fusion_result.get("response_style", "unknown")
        emotion_type = left_result.get("emotion_type", "neutral")

        if response_style == "warm" or response_style == "empathetic":
            self.agent_state.record(
                mood=AgentMood.EMPATHETIC,
                intensity=0.5,
                reason="我用温暖的语气回应,希望能传递关心",
                confidence=0.6
            )
        elif response_style == "balanced":
            self.agent_state.record(
                mood=AgentMood.NEUTRAL,
                intensity=0.3,
                reason="我选择了平衡的回应方式",
                confidence=0.5
            )

    def _record_impulse_after_capsule(self, user_input: str, left_result: Dict,
                                        right_result: Dict, capsules: List):
        """
        【触发点5】胶囊存档时
        如果 RobotSelf 可用,记录一次冲动/选择经历
        """
        if not self.robot_self:
            return

        emotion_type = left_result.get("emotion_type", "neutral")
        intent_type = right_result.get("intent_type", "casual_chat")

        # 构造 Agent 的内心"冲动"
        if emotion_type in ("sadness", "anger", "fear"):
            left_desire = f"想要更多关心用户({emotion_type})"
            right_constraint = "但不想过度打扰用户"
        elif intent_type == "deep_connection":
            left_desire = "想要更深入地分享我的想法"
            right_constraint = "但要保持适当的边界"
        else:
            left_desire = "想要更个性化地回应"
            right_constraint = "但要保持专业和适度"

        try:
            self.robot_self.make_choice(
                situation=f"用户说:{user_input[:30]}...",
                left_desire=left_desire,
                right_constraint=right_constraint
            )
        except Exception as e:
            print(f"⚠️ RobotSelf 冲动记录失败: {e}")

    # ============ 各区处理(保持原有逻辑) ============

    def _process_left(self, user_input: str, context: Dict) -> Dict:
        """处理左脑(情绪 + 共情)"""
        if not self._left_initialized:
            return {"emotion_type": "neutral", "emotion_score": 0.3, "empathy_level": 0.5, "empathy_phrases": []}

        try:
            emotion_output = self.emotion_detector.detect(user_input, context)

            user_context = {
                "relationship_stage": context.get("relationship_stage", "initial"),
                "user_name": context.get("user_name", "")
            }
            empathy_output = self.empathy_generator.generate(emotion_output, user_context)

            return {
                "emotion_score": emotion_output.emotion_score,
                "emotion_type": emotion_output.emotion_type,
                "emotion_label": emotion_output.emotion_label,
                "keywords": emotion_output.keywords,
                "subtext": emotion_output.subtext,
                "is_masked": emotion_output.is_masked,
                "surface_emotion": emotion_output.surface_emotion,
                "underlying_emotion": emotion_output.underlying_emotion,
                "empathy_level": empathy_output.empathy_level,
                "empathy_phrases": empathy_output.empathy_phrases,
                "avoid_phrases": empathy_output.avoid_phrases,
                "tone_style": empathy_output.tone_style,
                "tone_modifier": empathy_output.tone_modifier,
                "can_share_joy": empathy_output.can_share_joy,
                "emotion_output": emotion_output,
                "empathy_output": empathy_output
            }
        except Exception as e:
            print(f"⚠️ 左脑处理异常: {e}")
            return {"emotion_type": "neutral", "emotion_score": 0.3, "empathy_level": 0.5, "empathy_phrases": []}

    def _process_right(self, user_input: str, left_result: Dict, context: Dict) -> Dict:
        """处理右脑(意图 + 逻辑 + 方案)"""
        if not self._right_initialized:
            return {"intent_type": "casual_chat", "confidence": 0.5, "needs_tools": [], "best_solution": None}

        try:
            emotion_output = left_result.get("emotion_output")
            intent_output = self.intent_classifier.classify(user_input, emotion_output)
            logic_output = self.logic_parser.parse(intent_output, user_input, context)
            solution_output = self.solution_generator.generate(
                logic_output, user_input, {
                    **context,
                    "empathy_level": left_result.get("empathy_level", 0.5),
                    "empathy_phrase": left_result.get("empathy_phrases", [""])[0] if left_result.get("empathy_phrases") else ""
                }
            )

            return {
                "intent_type": intent_output.intent_type,
                "confidence": intent_output.confidence,
                "sub_intents": intent_output.sub_intents,
                "requires_action": intent_output.requires_action,
                "urgency": intent_output.urgency,
                "complexity": intent_output.complexity,
                "task_type": logic_output.task_type,
                "needs_tools": logic_output.needs_tools,
                "estimated_duration": logic_output.estimated_duration,
                "best_solution": solution_output.best_solution,
                "alternatives": solution_output.alternatives,
                "generated_response": solution_output.generated_response,
                "intent_output": intent_output,
                "logic_output": logic_output,
                "solution_output": solution_output
            }
        except Exception as e:
            print(f"⚠️ 右脑处理异常: {e}")
            return {"intent_type": "casual_chat", "confidence": 0.5, "needs_tools": [], "best_solution": None}

    def _process_temporal(self, user_input: str, left_result: Dict, right_result: Dict) -> Dict:
        """处理颞叶(记忆检索)"""
        if not self._temporal_initialized:
            return {"retrieved_capsules": [], "short_term": {}}

        try:
            retrieved = []
            if hasattr(self.long_term_memory, 'retrieve'):
                try:
                    retrieved = self.long_term_memory.retrieve(user_input, limit=5)
                except Exception:
                    pass

            capsule_output = None
            if self._left_initialized and self.capsule_factory:
                emotion_output = left_result.get("emotion_output")
                if emotion_output:
                    capsule_output = self.capsule_factory.create_multiple(
                        user_input, emotion_output
                    )

            return {
                "retrieved_capsules": retrieved,
                "capsule_output": capsule_output,
                "short_term": {}
            }
        except Exception as e:
            print(f"⚠️ 颞叶处理异常: {e}")
            return {"retrieved_capsules": [], "short_term": {}}

    def _process_executor(self, left_result: Dict, right_result: Dict,
                         temporal_result: Dict, context: Dict) -> Dict:
        """处理执行层"""
        try:
            from prefrontal.executor import PrefrontalExecutor
            from prefrontal.executor import ExecutorOutput
            executor = PrefrontalExecutor()

            emotion_output = left_result.get("emotion_output")
            empathy_output = left_result.get("empathy_output")
            intent_output = right_result.get("intent_output")
            logic_output = right_result.get("logic_output")
            solution_output = right_result.get("solution_output")

            executor_result = executor.execute(
                MockLeft(left_result),
                MockRight(right_result),
                MockTemporal(temporal_result),
                context
            )

            return {
                "base_weights": executor_result.base_weights,
                "execution_plan": executor_result.execution_plan,
                "strategy_type": executor_result.strategy_type,
                "confidence": executor_result.confidence,
                "reasoning": executor_result.reasoning,
                "executor_output": executor_result
            }
        except ImportError as e:
            print(f"⚠️ 前额叶执行层未安装: {e}")
            return {"strategy_type": "balanced", "base_weights": None, "execution_plan": None}
        except Exception as e:
            print(f"⚠️ 执行层异常: {e}")
            return {"strategy_type": "balanced", "base_weights": None, "execution_plan": None}

    def _process_monitor(self, executor_result: Dict, all_outputs: Dict, context: Dict) -> Dict:
        """处理监控层"""
        try:
            from prefrontal.monitor import PrefrontalMonitor
            monitor = PrefrontalMonitor()

            executor_output = executor_result.get("executor_output")

            if executor_output:
                monitor_result = monitor.monitor(
                    executor_output,
                    {"left": all_outputs["left"], "right": all_outputs["right"]},
                    {**context, "left": all_outputs["left"], "right": all_outputs["right"]}
                )
                return {
                    "monitor_output": monitor_result,
                    "final_weights": monitor_result.final_weights,
                    "approved_plan": monitor_result.approved_plan,
                    "blocked_actions": monitor_result.blocked_actions,
                    "override_log": monitor_result.override_log,
                    "conflict_score": monitor_result.conflict_score
                }
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️ 监控层异常: {e}")

        return {
            "final_weights": executor_result.get("base_weights"),
            "approved_plan": executor_result.get("execution_plan"),
            "blocked_actions": [],
            "override_log": "降级模式",
            "conflict_score": 0.0
        }

    def _process_fusion(self, monitor_result: Dict, all_outputs: Dict, context: Dict) -> Dict:
        """处理融合层"""
        try:
            from prefrontal.fusion_output import FusionOutput
            fusion = FusionOutput()

            fusion_result = fusion.fuse(
                MockMonitorOutput(monitor_result),
                all_outputs,
                {**context, "hour": context.get("hour", datetime.now().hour)}
            )

            return {
                "response": fusion_result.response,
                "response_style": fusion_result.response_style,
                "metadata": fusion_result.metadata
            }
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️ 融合层异常: {e}")

        generated = all_outputs.get("right", {}).get("generated_response", "")
        empathy = all_outputs.get("left", {}).get("empathy_phrases", [])

        if empathy and generated:
            response = f"{empathy[0]} {generated}"
        elif empathy:
            response = empathy[0]
        else:
            response = generated or "好的。"

        return {"response": response, "response_style": "fallback"}

    def _process_capsules(self, user_input: str, left_result: Dict) -> List:
        """处理胶囊创建"""
        capsules = []

        if not self._left_initialized or not self.capsule_factory:
            return capsules

        try:
            emotion_output = left_result.get("emotion_output")
            if emotion_output:
                result = self.capsule_factory.create_multiple(user_input, emotion_output)
                if result and result.should_capsule:
                    capsules = result.capsules
        except Exception as e:
            print(f"⚠️ 胶囊处理异常: {e}")

        return capsules

    def _update_relationship(self, user_input: str, left_result: Dict, right_result: Dict):
        """更新关系"""
        try:
            from limbic.relationship_manager import Interaction
            from datetime import datetime

            interaction = Interaction(
                timestamp=datetime.now().isoformat(),
                intent_type=right_result.get("intent_type", "casual_chat"),
                emotion_type=left_result.get("emotion_type", "neutral"),
                emotion_score=left_result.get("emotion_score", 0.3),
                capsules_created=0,
                memory_recalled=0,
                duration_seconds=0,
                is_night=22 <= datetime.now().hour or datetime.now().hour < 6,
                care_provided=False,
                care_accepted=False,
                special_flags=[]
            )

            self.relationship_manager.record_interaction(interaction)
        except Exception as e:
            print(f"⚠️ 关系更新异常: {e}")


# ============ 临时 Mock 类(供 Executor/Monitor/Fusion 使用)============
# 【说明】这些是兼容层,用于桥接旧的非接口实现
# 当所有模块都迁移到接口协议后,这些可以移除

class MockLeft:
    def __init__(self, data: Dict):
        self.emotion_score = data.get("emotion_score", 0.3)
        self.empathy_phrases = data.get("empathy_phrases", [])
        for k, v in data.items():
            setattr(self, k, v)


class MockRight:
    def __init__(self, data: Dict):
        self.intent_type = data.get("intent_type", "casual_chat")
        self.confidence = data.get("confidence", 0.5)
        self.needs_tools = data.get("needs_tools", [])
        self.best_solution = data.get("best_solution")
        self.logic_output = data.get("logic_output")
        self.solution_output = data.get("solution_output")
        for k, v in data.items():
            setattr(self, k, v)


class MockTemporal:
    def __init__(self, data: Dict):
        self.retrieved_capsules = data.get("retrieved_capsules", [])


class MockMonitorOutput:
    def __init__(self, data: Dict):
        self.approved_plan = data.get("approved_plan")
        self.final_weights = data.get("final_weights")
        self.override_log = data.get("override_log", "")
        self.conflict_score = data.get("conflict_score", 0.0)


# ============ 单例 ============
_processor_instance: Optional[InputProcessor] = None

def get_instance() -> InputProcessor:
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = InputProcessor()
    return _processor_instance


def process(user_input: str, context: Dict = None) -> NeuroAgentOutput:
    """快捷处理"""
    return get_instance().process(user_input, context)


# ============ 测试 ============
if __name__ == "__main__":
    from datetime import datetime

    processor = InputProcessor()

    print("=== 输入处理器测试 ===\n")

    test_cases = [
        ("你好啊,今天怎么样?", {"hour": 10}),
        ("工作好累啊,老板又骂我了", {"hour": 14}),
        ("帮我查一下天气", {"hour": 9}),
    ]

    for text, ctx in test_cases:
        print(f"【{text}】")
        result = processor.process(text, ctx)
        print(f"  回应: {result.response[:50]}...")
        print(f"  Agent情绪: {result.agent_emotion}")
        print(f"  元数据: {result.metadata}")
        print()
