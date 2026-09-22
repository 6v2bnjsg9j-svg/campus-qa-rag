from pymilvus import MilvusClient

db_name="rag"
collection_name="docs"
client = MilvusClient("http://localhost:19530",db_name=db_name)