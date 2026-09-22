from dotenv import load_dotenv
from langchain_deepseek import ChatDeepSeek
from langchain_ollama import ChatOllama
from langchain.embeddings import init_embeddings
import os

from study.tool.query_tool import search_zhang, search_kuan

load_dotenv(override=True)


#deepseek
model = ChatDeepSeek(
    model="deepseek-v4-flash",
    extra_body={
        "thinking": {
            "type": "disabled"
        }
    }
)

#本地小模型
ollamamodel=ChatOllama(
    model="deepseek-r1:1.5b",
    base_url="http://localhost:11434",
)

#嵌入模型
embed_model = init_embeddings(
    model="qwen3.7-text-embedding",
    provider="openai",
    api_key=os.getenv("QIANWEN_ENBEDDING_KEY"),
    base_url=os.getenv("QIANWEN_ENBEDDING_URL"),
    check_embedding_ctx_length=False
)


tools=[search_kuan,search_zhang]
mainModel=model.bind_tools(tools)
