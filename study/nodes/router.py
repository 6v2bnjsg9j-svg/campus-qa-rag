from typing import Literal
from langchain_core.messages import AIMessage
from study.state import MainState
from langgraph.runtime import Runtime
from langgraph.types import Command


def is_have_node(state: MainState, runtime: Runtime) -> MainState:
    deduped = state["docs"]
    if not deduped:
        return {
            "final_ans": "抱歉，我的知识库里面查询不到相应的内容",
            "is_not_have": 1,
            "messages": [AIMessage(content="抱歉，我的知识库里面查询不到相应的内容")]
        }
    else:
        return {
            "is_not_have": 0
        }



def router_rewriter(state: MainState) -> Literal["buquan_node","is_have_node"]:
    w=len(state["docs"])
    re=state["rewrite_count"]
    #如果改写次数已经到达上限
    if re>=3:
        return "is_have_node"
    if w<3 :
        return "buquan_node"
    else:
        return "is_have_node"



def is_have_router(state: MainState)->Literal[ "press_sc_node" ,  "__end__"]:
    is_not_have=state["is_not_have"]
    if is_not_have==0:
        return "press_sc_node"
    if is_not_have==1:
        return "__end__"

def router_tool(state: MainState) -> Command[Literal["tool_node", "final_sc_node","__end__"]]:
    msgs = state.get("messages") or []
    if msgs and getattr(msgs[-1], "tool_calls", None):
        if state["tool_used"] == True:
            return Command(
                goto="final_sc_node"
            )
        return Command(
            goto="tool_node",
            update={
                "tool_used":True
            }
        )
    return Command(
        goto= "__end__"
    )