from langchain_core.messages import RemoveMessage, HumanMessage, AIMessage
from langgraph.runtime import Runtime

from study.db.model import ollamamodel, qwenmodel
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
def buquan_node(state: MainState, runtime: Runtime) -> MainState:
    stream_writer = runtime.stream_writer
    stream_writer("补全问题，使问题更加清晰易懂")

    messages = state["messages"]

    # ---- 拆分：最后一条 Human 是"最新提问"，其余是"历史" ----
    last_human_idx = -1
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            last_human_idx = i
            break
    latest_question = messages[last_human_idx].content

    # 历史部分：最后一条 Human 之前的对话（跳过工具消息，AI 只取有正文的）
    history_lines = []
    for m in messages[:last_human_idx]:
        if isinstance(m, HumanMessage):
            history_lines.append(f"用户：{m.content}")
        elif isinstance(m, AIMessage) and m.content:
            content = m.content if len(m.content) <= 200 else m.content[:200] + "…"
            history_lines.append(f"助手：{content}")
    older_history = "\n".join(history_lines) if history_lines else "（无）"

    # ---- 组装并调用 ----
    promptmessages = prompt_re_template.format_messages(
        latest_question=latest_question,
        older_history=older_history,
    )
    raw_output = qwenmodel.invoke(promptmessages).content

    re = state.get("rewrite_count", 0)
    return {
        "rewritten_question": raw_output,
        "rewrite_count": re + 1,
    }