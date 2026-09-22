from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from study.db.model import tools
from study.nodes.generate import press_sc_node, sc_node, final_sc_node
from study.nodes.preprocess import caijian_node, buquan_node
from study.nodes.retrieval import jiansuo_node, process_docs_node
from study.nodes.router import is_have_node, router_rewriter, router_tool, is_have_router
from study.state import MainState

builder=StateGraph(state_schema=MainState)
#加入点
builder.add_node("caijian_node",caijian_node)#裁剪消息
builder.add_node("buquan_node",buquan_node)#改写问题
builder.add_node("jiansuo_node",jiansuo_node)#检索
builder.add_node("process_docs_node",process_docs_node)#去重排序
builder.add_node("press_sc_node",press_sc_node)
builder.add_node("sc_node",sc_node)#大模型生成
builder.add_node("is_have_node",is_have_node)
builder.add_node("tool_node", ToolNode(tools=tools))#工具
builder.add_node("final_sc_node",final_sc_node)
builder.add_node("router_tool",router_tool)
#添加边

builder.add_edge(START,"caijian_node")
builder.add_edge("caijian_node","buquan_node")
builder.add_edge("buquan_node","jiansuo_node")
builder.add_edge("jiansuo_node","process_docs_node")


builder.add_conditional_edges(
    "process_docs_node",
    router_rewriter,
    {
        "buquan_node": "buquan_node",
        "is_have_node": "is_have_node",
    },
)
builder.add_conditional_edges("is_have_node",is_have_router,path_map={
    "press_sc_node":"press_sc_node",
    "__end__":"__end__"
})

builder.add_edge("press_sc_node", "sc_node")

builder.add_edge("sc_node","router_tool")

builder.add_edge("tool_node", "sc_node")

builder.add_edge("final_sc_node",END)