from dataclasses import dataclass, field
from typing import Optional, List, Literal

NodeType = Literal["block", "chapter", "article", "ts"]
@dataclass
class LawNode:
    # 节点类型: BLOCK块 / CHAPTER章 / ARTICLE条/特殊ts
    node_type: NodeType

    # 层级id
    block_id: int = 0#块id
    block_name: Optional[str] = None#块名字
    chapter_id: int = 0#章id
    article_id: int = 0#条id

    content: Optional[str] = None

@dataclass
class milusNode:
    node_type: NodeType

    # 层级id
    block_id: int = 0  # 块id
    chapter_id: int = 0  # 章id
    article_id: int = 0  # 条id

    content: Optional[str] = None

    is_kuan: bool=False  #如果下面有款是True
    embedding: Optional[list] = None

