from langchain_core.messages import RemoveMessage, HumanMessage, AIMessage
from langgraph.runtime import Runtime

from study.db.model import ollamamodel
from study.prompt import prompt_re_template
from study.state import MainState



#======================裁剪信息============================
#设计思路是保存近三论的对话，你可以发现aimesssages可以有很多但是HumanMessage每一轮只有一个所以我采用标记HumanMessages来切割
def caijian_node(state:MainState,runtime:Runtime)->MainState:
    stream_writer = runtime.stream_writer
    stream_writer("正在裁剪对话")
    messages=state["messages"]
    Human_key=[]
    for i in range(0,len(messages)):
        if isinstance(messages[i], HumanMessage):
            Human_key.append(i)
    #长度不够直接往下走
    if len(Human_key) < 3:
        return {
            "tool_used": False,
            "rewrite_count": 0,
            "context": "",
            "prompt": []
        }
    #去除多余的对话
    cut_from = Human_key[-3]
    to_remove = [RemoveMessage(id=m.id) for m in messages[:cut_from]]

    return {
        "tool_used": False,
        "rewrite_count": 0,
        "messages": to_remove,
        "context": "",
        "prompt": []
    }



#================================补全本次问题=============================
#设计是用户会出现各种不明确的问题（它是什么？一类）#这时候就需要大模型来补全问题了
def buquan_node(state:MainState,runtime:Runtime)->MainState:
    stream_writer = runtime.stream_writer
    stream_writer("补全问题，使问题更加清晰易懂")
    history_lines = []
    for m in state["messages"]:
        if isinstance(m, HumanMessage):
            history_lines.append(f"用户：{m.content}")
        elif isinstance(m, AIMessage) and m.content:
            history_lines.append(f"助手：{m.content}")
        # ToolMessage / 带 tool_calls 的 AI 一律跳过
    text = "\n".join(history_lines) or "（无）"
    promptmessages=prompt_re_template.format_messages(
        history=text
    )
    #调用本地大模型生成
    rewritten_question=ollamamodel.invoke(promptmessages).content.strip()
    #重写次数加一
    re = state.get("rewrite_count", 0)
    return {
        "rewritten_question":rewritten_question,
        "rewrite_count" : re+1
    }