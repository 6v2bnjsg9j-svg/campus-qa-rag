from typing import List

from langgraph.graph import MessagesState

class MainState(MessagesState):
    #原始问题
    original_question: str = ""
    #改写之后的问题
    rewritten_question: str = ""
    #改写次数
    rewrite_count: int = 0
    #原始查找的数据
    raw_docs: list[dict] = []
    #经过处理的数据
    docs: list[dict] = []
    #推送的上下文
    context: str=""
    #最终回答
    final_ans: str = ""
    #是否没有查出来
    is_not_have: int = 0
    #提示词
    prompt: List=[]
    #是否调用过工具
    tool_used: bool = False

