
from langchain_core.messages import RemoveMessage, HumanMessage, AIMessage, ToolMessage
from study.db.model import ollamamodel, mainModel, model
from langgraph.runtime import Runtime
from study.prompt import prompt_template, prompt_re_template, prompt_final_template
from study.state import MainState



#===================在生成节点前的准备工作==============
def press_sc_node(state: MainState, runtime: Runtime) -> MainState:
    deduped = state["docs"]
    question = state["rewritten_question"]
    lines = []
    for i, d in enumerate(deduped, 1):
        lines.append(f"### 资料 {i}")
        lines.append(f"- block_id: {d['block_id']}")
        lines.append(f"- chapter_id: {d['chapter_id']}")
        lines.append(f"- article_id: {d['article_id']}")
        lines.append(f"- 类型: {'【含条款，需查详情】' if d['is_kuan'] else '【完整正文】'}")
        lines.append(f"- 相关度: {d['score']:.3f}")
        lines.append(f"- 内容: {d['content'][:200]}")
        lines.append("")
    context = "\n".join(lines)
    messages = prompt_template.format_messages(
        context=context,
        question=question
    )
    return {
        "context":context,
        "prompt":messages,
        "is_not_have": 0
    }



#=========拼接提示词然后调用大模型生成总结======
def sc_node(state, runtime):
    messages = state["messages"]
    rag_prompt = state["prompt"] or []
    if not state["tool_used"]:
        messages = messages + rag_prompt
    response = mainModel.invoke(messages)

    updates = {"messages": [response]}
    if not getattr(response, "tool_calls", None):
        updates["final_ans"] = response.content   # ← 只有最终回答才写
    return updates


#=====如果大模型调用了第二次工具就会进入这个节点======
def final_sc_node(state: MainState) -> MainState:
    question = state["original_question"]
    text=state["context"]
    clean_msgs = []
    tool_results = []
    for m in state["messages"]:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            continue
        if isinstance(m, ToolMessage):
            if m.content:
                tool_results.append(m.content)
            continue
        clean_msgs.append(m)

    if tool_results:
        text = text + "\n\n### 工具查询到的完整条款\n" + "\n\n".join(tool_results)

    prompt_msgs = prompt_final_template.format_messages(context=text,question=question)
    msgs = prompt_msgs + clean_msgs
    content = model.invoke(msgs).content

    return {
        "messages": [AIMessage(content=content)],
        "final_ans": content,
    }