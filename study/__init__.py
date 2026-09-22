from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from study.graph import builder
#
#
check = InMemorySaver()
graph = builder.compile(checkpointer=check)
#
config = {"configurable": {"thread_id": "test"}}

for mode, data in graph.stream(
    {
        "messages": [HumanMessage(content="如何办理转学?")],
        "original_question": "如何办理转学？",
    },
    config=config,
    stream_mode=["updates", "custom"],
):
    if mode == "custom":
        print(f"📢 {data}")
    else:
        for node_name, output in data.items():
            print(f"\n▶ {node_name}")
            if isinstance(output, dict):
                for k, v in output.items():
                    if k == "messages":
                        print(f"   messages: {[type(m).__name__ for m in v]}")
                    else:
                        print(f"   {k}: {str(v)}")


def run(query:str)->str:
    ans=graph.invoke({
                  "messages": [HumanMessage(content=query)],
         "original_question": query},
        config=config
    )
    return ans.final_ans