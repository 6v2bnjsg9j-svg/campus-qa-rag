# evalrag --adapter my_eval:adapter --generate documents.json
from dotenv import load_dotenv
load_dotenv(override=True)
import os
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="qwen3.7-plus",
    api_key=os.getenv("QIANWEN_ENBEDDING_KEY"),
    base_url=os.getenv("QIANWEN_ENBEDDING_URL"),
)
print(model.invoke("你好"))