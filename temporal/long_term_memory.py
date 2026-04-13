"""
temporal/long_term_memory.py
=============================

Neuro-Agent 长期记忆库
负责：情绪胶囊的 SQLite 持久化存储、查询、更新、遗忘

依赖：
    - emotion_types.md（参考）
    - references/relationship_stages.md（参考）

数据目录：
    ~/.openclaw/workspace/neuro_claw/capsules/long_term/
"""

import sqlite3
import json
import os
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

# ============ 路径配置 ============
DATA_DIR = Path.home() / ".openclaw" / "workspace" / "neuro_claw" / "capsules" / "long_term"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "memory.db"

# ============ 遗忘曲线常量 ============
DECAY_K = 1.0  # 巩固系数初始值，每次被提及+0.5
DORMANT_THRESHOLD = 0.3  # R < 0.3 进入休眠
DELETE_THRESHOLD = 0.1  # R < 0.1 可被删除


# ============ 数据结构 ============
@dataclass
class EmotionCapsule:
    """
    情绪胶囊数据结构
    
    属性说明：
        - id: 唯一标识，格式 capsule_{timestamp}_{random}
        - timestamp: 创建时间 ISO 格式
        - type: 类型 preference/emotion/fact/secret
        - content: 内容摘要和原始触发
        - emotion: 情绪标签和强度
        - tags: 标签列表
        - decay_rate: 衰减率
        - access_count: 被访问次数
        - memory_strength: 记忆强度 0.0-1.0
        - is_dormant: 是否休眠
        - sensitivity: 敏感度 normal/high/critical
        - last_accessed: 最后访问时间
    """
    id: str
    timestamp: str
    type: str  # preference | emotion | fact | secret
    content: Dict[str, str]  # {summary, original_trigger, detail}
    emotion: Dict[str, Any]  # {label, intensity}
    tags: List[str]
    decay_rate: float
    access_count: int
    memory_strength: float
    is_dormant: bool
    sensitivity: str  # normal | high | critical
    last_accessed: str
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'EmotionCapsule':
        return cls(**d)


@dataclass
class RelationshipEdge:
    """
    关系边数据结构
    用于概念图谱中的概念关联
    """
    id: str
    concept_a: str
    concept_b: str
    relation_type: str  # causes | triggers | contradicts | similar | belongs_to
    strength: float
    created_at: str


# ============ 遗忘曲线计算 ============
def calculate_retention(s: float, k: float, t_days: float) -> float:
    """
    计算记忆保留率
    
    公式: R = e^(-t / (S × K))
    
    参数:
        s: 初始情绪强度 (0.3-1.0)
        k: 巩固系数 (初始1.0，每次被提及+0.5)
        t_days: 距创建时间（天）
    
    返回:
        R: 记忆保留率 (0.0-1.0)
    """
    if s <= 0:
        return 0.0
    exponent = -t_days / (s * k)
    return math.exp(exponent)


def calculate_decay_rate(emotion_intensity: float, sensitivity: str) -> float:
    """
    根据情绪强度和敏感度计算衰减率
    
    参数:
        emotion_intensity: 情绪强度 0.0-1.0
        sensitivity: 敏感度 normal/high/critical
    
    返回:
        decay_rate: 衰减率
    """
    base = 1.0 - emotion_intensity
    
    # 敏感记忆衰减更慢（更难忘记）
    sensitivity_multiplier = {
        "normal": 1.0,
        "high": 0.7,     # 衰减更慢
        "critical": 0.5  # 衰减最慢
    }
    
    return base * sensitivity_multiplier.get(sensitivity, 1.0)


# ============ 核心类 ============
class LongTermMemory:
    """
    长期记忆库管理器
    
    功能：
        - SQLite 持久化存储情绪胶囊
        - 查询、筛选、更新访问记录
        - 遗忘曲线计算和休眠管理
        - 记忆晋升（短期 → 长期）
        - 概念关系管理
    """
    
    def __init__(self, db_path: str = None):
        """
        初始化长期记忆库
        
        参数:
            db_path: 数据库路径，默认 ~/.openclaw/.../long_term/memory.db
        """
        self.db_path = db_path or str(DB_PATH)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 情绪胶囊表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS capsules (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                type TEXT NOT NULL,
                summary TEXT,
                original_trigger TEXT,
                detail TEXT,
                emotion_label TEXT,
                emotion_intensity REAL,
                tags TEXT,
                sensitivity TEXT DEFAULT 'normal',
                memory_strength REAL DEFAULT 1.0,
                access_count INTEGER DEFAULT 0,
                is_dormant INTEGER DEFAULT 0,
                last_accessed TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # 概念关系表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS relationships (
                id TEXT PRIMARY KEY,
                concept_a TEXT NOT NULL,
                concept_b TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                strength REAL DEFAULT 0.5,
                created_at TEXT NOT NULL
            )
        """)
        
        # 创建索引加速查询
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_capsules_type ON capsules(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_capsules_emotion ON capsules(emotion_label)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_capsules_dormant ON capsules(is_dormant)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_concepts ON relationships(concept_a, concept_b)")
        
        conn.commit()
        conn.close()
    
    # ============ 胶囊操作 ============
    
    def save_capsule(self, capsule: EmotionCapsule) -> bool:
        """
        保存情绪胶囊到数据库
        
        参数:
            capsule: EmotionCapsule 对象
        
        返回:
            bool: 是否保存成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO capsules (
                    id, timestamp, type, summary, original_trigger, detail,
                    emotion_label, emotion_intensity, tags, sensitivity,
                    memory_strength, access_count, is_dormant, last_accessed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                capsule.id,
                capsule.timestamp,
                capsule.type,
                capsule.content.get("summary", ""),
                capsule.content.get("original_trigger", ""),
                capsule.content.get("detail", ""),
                capsule.emotion.get("label", "neutral"),
                capsule.emotion.get("intensity", 0.5),
                json.dumps(capsule.tags, ensure_ascii=False),
                capsule.sensitivity,
                capsule.memory_strength,
                capsule.access_count,
                1 if capsule.is_dormant else 0,
                capsule.last_accessed,
                capsule.timestamp
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"[LongTermMemory] 保存胶囊失败: {e}")
            return False
    
    def get_capsule(self, capsule_id: str) -> Optional[EmotionCapsule]:
        """
        根据 ID 获取胶囊
        
        参数:
            capsule_id: 胶囊 ID
        
        返回:
            EmotionCapsule 或 None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM capsules WHERE id = ?", (capsule_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return self._row_to_capsule(row)
    
    def retrieve(
        self,
        query: str = None,
        capsule_type: str = None,
        emotion_label: str = None,
        sensitivity: str = None,
        include_dormant: bool = False,
        limit: int = 20
    ) -> List[EmotionCapsule]:
        """
        检索胶囊
        
        参数:
            query: 文本查询（匹配 summary/original_trigger）
            capsule_type: 按类型筛选
            emotion_label: 按情绪标签筛选
            sensitivity: 按敏感度筛选
            include_dormant: 是否包含休眠胶囊
            limit: 返回数量上限
        
        返回:
            List[EmotionCapsule]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = "SELECT * FROM capsules WHERE 1=1"
        params = []
        
        if capsule_type:
            sql += " AND type = ?"
            params.append(capsule_type)
        
        if emotion_label:
            sql += " AND emotion_label = ?"
            params.append(emotion_label)
        
        if sensitivity:
            sql += " AND sensitivity = ?"
            params.append(sensitivity)
        
        if not include_dormant:
            sql += " AND is_dormant = 0"
        
        if query:
            sql += " AND (summary LIKE ? OR original_trigger LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        
        sql += " ORDER BY memory_strength DESC, access_count DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_capsule(row) for row in rows]
    
    def update_access(self, capsule_id: str) -> bool:
        """
        更新胶囊访问记录
        
        触发条件：胶囊被检索或被提及
        
        效果：
            - access_count += 1
            - last_accessed = now()
            - memory_strength += 0.1（正向强化，上限1.0）
        
        参数:
            capsule_id: 胶囊 ID
        
        返回:
            bool: 是否更新成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 先获取当前值
            cursor.execute(
                "SELECT access_count, memory_strength FROM capsules WHERE id = ?",
                (capsule_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return False
            
            new_access_count = row[0] + 1
            new_memory_strength = min(1.0, row[1] + 0.1)
            
            cursor.execute("""
                UPDATE capsules 
                SET access_count = ?, memory_strength = ?, last_accessed = ?, is_dormant = 0
                WHERE id = ?
            """, (new_access_count, new_memory_strength, now, capsule_id))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"[LongTermMemory] 更新访问记录失败: {e}")
            return False
    
    def get_all_capsules(self, include_dormant: bool = False) -> List[EmotionCapsule]:
        """
        获取所有胶囊
        
        参数:
            include_dormant: 是否包含休眠胶囊
        
        返回:
            List[EmotionCapsule]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if include_dormant:
            sql = "SELECT * FROM capsules ORDER BY created_at DESC"
        else:
            sql = "SELECT * FROM capsules WHERE is_dormant = 0 ORDER BY created_at DESC"
        
        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_capsule(row) for row in rows]
    
    # ============ 遗忘管理 ============
    
    def apply_decay(self) -> Dict[str, List[str]]:
        """
        应用遗忘曲线
        
        遍历所有胶囊，计算当前保留率
        - R < 0.3 → 进入休眠
        - R < 0.1 → 标记可删除
        
        返回:
            Dict: {dormant_ids: [...], deletable_ids: [...]}
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM capsules")
        rows = cursor.fetchall()
        
        dormant_ids = []
        deletable_ids = []
        
        for row in rows:
            capsule = self._row_to_capsule(row)
            
            # 计算保留率
            created = datetime.fromisoformat(capsule.timestamp)
            t_days = (datetime.now() - created).total_seconds() / 86400
            
            # 巩固系数：每被访问一次+0.5
            k = DECAY_K + (capsule.access_count * 0.5)
            s = capsule.emotion.get("intensity", 0.5)
            
            r = calculate_retention(s, k, t_days)
            
            # 判断是否需要休眠或删除
            if r < DELETE_THRESHOLD:
                deletable_ids.append(capsule.id)
            elif r < DORMANT_THRESHOLD and not capsule.is_dormant:
                cursor.execute(
                    "UPDATE capsules SET is_dormant = 1 WHERE id = ?",
                    (capsule.id,)
                )
                dormant_ids.append(capsule.id)
        
        conn.commit()
        conn.close()
        
        return {
            "dormant_ids": dormant_ids,
            "deletable_ids": deletable_ids
        }
    
    def delete_capsule(self, capsule_id: str) -> bool:
        """
        删除胶囊
        
        参数:
            capsule_id: 胶囊 ID
        
        返回:
            bool: 是否删除成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM capsules WHERE id = ?", (capsule_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[LongTermMemory] 删除胶囊失败: {e}")
            return False
    
    def cleanup_deletable(self) -> int:
        """
        清理可删除的胶囊（R < 0.1）
        
        返回:
            int: 清理的胶囊数量
        """
        result = self.apply_decay()
        count = 0
        for capsule_id in result["deletable_ids"]:
            if self.delete_capsule(capsule_id):
                count += 1
        return count
    
    # ============ 统计 ============
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取记忆库统计
        
        返回:
            Dict: 统计数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 总数
        cursor.execute("SELECT COUNT(*) FROM capsules")
        total = cursor.fetchone()[0]
        
        # 休眠数
        cursor.execute("SELECT COUNT(*) FROM capsules WHERE is_dormant = 1")
        dormant = cursor.fetchone()[0]
        
        # 按类型统计
        cursor.execute("""
            SELECT type, COUNT(*) 
            FROM capsules 
            GROUP BY type
        """)
        by_type = dict(cursor.fetchall())
        
        # 按情绪统计
        cursor.execute("""
            SELECT emotion_label, COUNT(*) 
            FROM capsules 
            GROUP BY emotion_label
        """)
        by_emotion = dict(cursor.fetchall())
        
        # 平均访问次数
        cursor.execute("SELECT AVG(access_count) FROM capsules")
        avg_access = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_capsules": total,
            "dormant_capsules": dormant,
            "active_capsules": total - dormant,
            "by_type": by_type,
            "by_emotion": by_emotion,
            "avg_access_count": round(avg_access, 2)
        }
    
    # ============ 关系管理 ============
    
    def add_relationship(
        self,
        concept_a: str,
        concept_b: str,
        relation_type: str,
        strength: float = 0.5
    ) -> bool:
        """
        添加概念关系
        
        参数:
            concept_a: 概念A
            concept_b: 概念B
            relation_type: 关系类型
            strength: 关系强度 0.0-1.0
        
        返回:
            bool: 是否添加成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            relationship_id = f"rel_{concept_a}_{concept_b}_{datetime.now().timestamp()}"
            
            cursor.execute("""
                INSERT INTO relationships (id, concept_a, concept_b, relation_type, strength, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                relationship_id,
                concept_a,
                concept_b,
                relation_type,
                strength,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"[LongTermMemory] 添加关系失败: {e}")
            return False
    
    def get_related_concepts(self, concept: str) -> List[RelationshipEdge]:
        """
        获取与某概念相关的所有概念
        
        参数:
            concept: 概念名称
        
        返回:
            List[RelationshipEdge]
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM relationships 
            WHERE concept_a = ? OR concept_b = ?
            ORDER BY strength DESC
        """, (concept, concept))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_relationship(row) for row in rows]
    
    # ============ 辅助方法 ============
    
    def _row_to_capsule(self, row: tuple) -> EmotionCapsule:
        """将数据库行转换为 EmotionCapsule"""
        return EmotionCapsule(
            id=row[0],
            timestamp=row[1],
            type=row[2],
            content={
                "summary": row[3],
                "original_trigger": row[4],
                "detail": row[5]
            },
            emotion={
                "label": row[6],
                "intensity": row[7]
            },
            tags=json.loads(row[8]) if row[8] else [],
            sensitivity=row[9],
            memory_strength=row[10],
            access_count=row[11],
            is_dormant=bool(row[12]),
            last_accessed=row[13],
        )
    
    def _row_to_relationship(self, row: tuple) -> RelationshipEdge:
        """将数据库行转换为 RelationshipEdge"""
        return RelationshipEdge(
            id=row[0],
            concept_a=row[1],
            concept_b=row[2],
            relation_type=row[3],
            strength=row[4],
            created_at=row[5]
        )


# ============ 单例模式 ============
_memory_instance: Optional[LongTermMemory] = None

def get_instance() -> LongTermMemory:
    """获取 LongTermMemory 单例"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = LongTermMemory()
    return _memory_instance


# ============ 快捷函数 ============
def save_capsule(capsule: EmotionCapsule) -> bool:
    """快捷保存胶囊"""
    return get_instance().save_capsule(capsule)

def retrieve_capsules(
    query: str = None,
    capsule_type: str = None,
    emotion_label: str = None,
    limit: int = 20
) -> List[EmotionCapsule]:
    """快捷检索胶囊"""
    return get_instance().retrieve(
        query=query,
        capsule_type=capsule_type,
        emotion_label=emotion_label,
        limit=limit
    )

def get_all_memories(include_dormant: bool = False) -> List[EmotionCapsule]:
    """快捷获取所有记忆"""
    return get_instance().get_all_capsules(include_dormant=include_dormant)


# ============ 测试 ============
if __name__ == "__main__":
    # 简单测试
    ltm = LongTermMemory()
    
    # 测试保存
    test_capsule = EmotionCapsule(
        id="capsule_test_001",
        timestamp=datetime.now().isoformat(),
        type="preference",
        content={
            "summary": "用户喜欢吃辣",
            "original_trigger": "我喜欢吃辣，越辣越开心",
            "detail": ""
        },
        emotion={"label": "joy", "intensity": 0.7},
        tags=["food", "spicy", "偏好"],
        decay_rate=0.3,
        access_count=0,
        memory_strength=1.0,
        is_dormant=False,
        sensitivity="normal",
        last_accessed=datetime.now().isoformat()
    )
    
    print(f"保存胶囊: {ltm.save_capsule(test_capsule)}")
    print(f"检索结果: {len(ltm.retrieve(capsule_type='preference'))} 条")
    print(f"统计: {ltm.get_statistics()}")
