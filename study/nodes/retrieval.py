
from langgraph.runtime import Runtime

from study.db.milvus_client import collection_name, client
from study.db.model import embed_model
from study.state import MainState





#=====================搜索相关文档=========================
def jiansuo_node(state:MainState,runtime:Runtime)->MainState:
    stream_writer = runtime.stream_writer
    stream_writer("开始从知识库里面检索")
    #准备工作
    query=state["rewritten_question"]
    query_vector = embed_model.embed_query(query)
    #开始查询
    res = client.search(
        collection_name=collection_name,
        data=[query_vector],
        limit=10,
        output_fields=["id","block_id","chapter_id","article_id","is_kuan","content"],
    )
    return {"raw_docs": res[0] if res else []}




#=================去重、过滤、截断===================
def process_docs_node(state: MainState, runtime: Runtime) -> MainState:
    stream_writer = runtime.stream_writer
    stream_writer("开始对相关文档进行筛选")
    #拿到原始数据
    does=state["raw_docs"]
    print(f"[process] raw_docs: {len(does)} 条")

    key_set=set()
    quchong=[]
    #去重
    for i in does:
        key=i["entity"]["content"][:100]# 前 100 字做 key
        if key not in key_set:
            quchong.append(i)
            key_set.add(key)
    print(f"[process] 去重后: {len(quchong)} 条")
    SCORE_THRESHOLD = 0.7  # COSINE，按效果调
    filtered = [d for d in quchong if d["distance"] >= SCORE_THRESHOLD]
    print(f"[process] 阈值过滤后: {len(filtered)} 条")  # ← 加
    print(f"[process] 分数分布: {[f'{d['distance']:.3f}' for d in quchong]}")  # ← 加
    top5=filtered[:5]
    print(f"[process] 最终 docs: {len(top5)} 条")
    docs = [
        {
            "content": d["entity"]["content"],
            "score": d["distance"],
            "is_kuan": d["entity"]["is_kuan"],
            "block_id": d["entity"]["block_id"],
            "chapter_id": d["entity"]["chapter_id"],
            "article_id": d["entity"]["article_id"],
        }
        for d in top5
    ]
    return {
        "docs" : docs
    }

