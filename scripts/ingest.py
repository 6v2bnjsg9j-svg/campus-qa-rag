from os import set_blocking

import fitz  # pymupdf
import re,os

import psycopg2
from dotenv import load_dotenv
import os, pickle
from study.db.model import embed_model
from scripts.chunk import LawNode, milusNode
db_name="rag"
load_dotenv(override=True)
CN = r'[一二三四五六七八九十百零〇]+'
END_PUNCT = "。！？；：”』】）)》"
pattern = r"^第一章.*"
re_patten=r"^jkl第一章.*"
RE_PAGE    = re.compile(r'^[-—\s]*\d{1,4}[-—\s]*$')
RE_CHAPTER = re.compile(rf'^第{CN}章')
RE_ARTICLE = re.compile(rf'^第{CN}条')
RE_CLAUSE  = re.compile(rf'[（(]{CN}[）)]')
RE_NUM_ITEM = re.compile(r'^\d+[、.．]')

def is_structural(line):
    return bool(
        RE_CHAPTER.match(line) or
        RE_ARTICLE.match(line) or RE_CLAUSE.match(line) or
        RE_NUM_ITEM.match(line)
    )

import re
CN = r"[一二三四五六七八九十百千万]+"

def remove_chapter_article_prefix(raw: str) -> str:
    # 2. 删除所有【第X条】字样
    raw = re.sub(rf"第{CN}条", "", raw)
    # 3. 清理多余换行、空格
    raw = re.sub(r"\n{2,}", "\n", raw).strip()
    return raw

def remove_cchapter(raw: str) -> str:
    # 1. 删除【第X章 + 后面所有文字，直到遇到第X条】适配粘连行场景
    raw = re.sub(rf"第{CN}章.*?(?=第{CN}条|\n|$)", "", raw)
    return raw

#--------------------人工操作，删除目录，整理不符合批量处理的提取，然后优化格式----------------------

doc = fitz.open("docs/studentTextlast78.pdf")

docs = []

for idex in range(len(doc)):
    page=doc[idex]
    text = page.get_text("text")
    if not text:
        continue
    docs.append({
        "page":idex+1,
        "text":text
    })
doc.close()

res=[]
for i in range(len(docs)):
    text=docs[i]["text"]
    lines=text.split("\n")
    clean=[]
    for j in lines:
        s=j.strip()
        #如果为空
        if not s:
            continue
        #如果是页码
        if RE_PAGE.match(s):
            continue
        clean.append(s)
    #合并断行
    merged = []
    buf = ""
    for j in clean:
        if is_structural(j):
            #该提交了
            if buf:#上一次的有东西提交
                merged.append(buf)
                buf=""
            merged.append(j)
            continue
        #为空时候不需要判断
        if not buf:
            buf = j
        else:
            # 判断末尾是否可以提交
            if buf[-1] in END_PUNCT:
                merged.append(buf)
                buf = j
            else:
                buf = buf + j
    if buf:
        merged.append(buf)
    string_text=""
    for j in merged:
        string_text=string_text+j+"\n"
    res.append({
        "page":docs[i]["page"],
        "text": string_text
    })







#按照第一章去分割就是把
res2=[]
for i in range(0,len(res)):
    text=res[i]["text"]
    lines=text.split("\n")
    merged = []
    #把那个第一章前面加标记
    for line in lines:
        if re.match(pattern,line.strip()):
            line="jkl"+line
        merged.append(line)
    s=""
    for j in merged:
       s=s+j+"\n"
    res2.append({
        "page":res[i]["page"],
        "text":s
    })

#把目录给它删了

#-------------目录已经人工删除了----------------
# res0=[]
# 中华人民共和国高等教育法
# x=0
# for i in range(0,len(res2)):
#     text=res2[i]["text"]
#     lines=text.split("\n")
#     #这是所有的开始
#     for j in lines:
#         if j.strip()=="中华人民共和国高等教育法":
#             x=i
#             break
#     if x!=0:
#         break
#
# text=res2[x]["text"]
# lines=text
# pin=[]
# q=""
# for j in range(0,len(lines)):
#     if lines[j].strip() == "中华人民共和国高等教育法":
#         for k in range(j,len(lines)):
#             pin.append(lines[k])
#         for k in pin:
#             q=q+k+"\n"
#         res0.append({
#             "page":x,
#             "text":q
#         })
#         break
# for i in range(x+1,len(res2)):
#     res0.append({
#         "page": res2[i]["page"],
#         "text": res2[i]["text"]
#     })


#因为已经处理很多了分不清页码了现在进行汇总
ans=""
for i in range(0,len(res2)):
    text=res2[i]["text"].strip()
    ans=ans+text+"\n"
# print(ans)


#按照章分块吧
#现在我在每个第一章前面加了jkl
ans2=[]
a=0
lines=ans.split("\n")
for i in range(0,len(lines)):
    if lines[i].strip().startswith("jkl"):
        idex=i
        ans2.append(idex)
        a=a+1
#-----------------------------a是来简单判断分了多少块（自测的）（可以忽略）-------------
cunchu_pdf=[]
fenkuai_x=[]
a=1
for i in range(0,len(ans2)):
    name=lines[ans2[i]-1].strip()
    text=""
    if i==(len(ans2)-1):
        for j in range(ans2[i],len(lines)):
            text = text + lines[j] + "\n"
    else:
        for j in range(ans2[i], ans2[i + 1]):
            text = text + lines[j] + "\n"
    cunchu_pdf.append(LawNode(block_name=name,block_id=a,node_type="block",content=text[3:]))
    # print(text[3:])
    # print("========================================")
    fenkuai_x.append(text)
    a=a+1
# print("========================================")
print(f"======================共{a}块==============================")


#-----------------开始具体分章-------------------------------
# RE_CHAPTER = re.compile(rf'^第{CN}章')
total_sum=0
block=0
for i in fenkuai_x:
    #存储块里面的每一章
    block+=1
    lines=i.split("\n")
    a = 1
    fenkuai_y=""
    # print("---------------------------------------------")
    for j in lines:
        #去掉加上的标记jkl
        if re.match(re_patten,j.strip()):
            text=j.strip()
            fenkuai_y=text[3:]
            continue
        if RE_CHAPTER.match(j.strip()):
            #推送
            cunchu_pdf.append(LawNode(
                 block_id=block, node_type="chapter", chapter_id=a,content=remove_cchapter(fenkuai_y)
            ))
            total_sum+=1
            # print(remove_cchapter(fenkuai_y))
            # print("===============================")
            a+=1
            fenkuai_y=j.strip()

            continue
        fenkuai_y=fenkuai_y+j+"\n"
    if fenkuai_y:
        cunchu_pdf.append(LawNode(block_id=block, node_type="chapter", chapter_id=a, content=remove_cchapter(fenkuai_y)))
        total_sum+=1
        # print(fenkuai_y)
print(f"======================共{total_sum}章==============================")

# RE_ARTICLE = re.compile(rf'^第{CN}条')
total_sum=0
cunchu_tiao=[]
set_block_id=set()
for i in range(0,len(cunchu_pdf)):
    fentiao_y=""
    if cunchu_pdf[i].block_id!=0 and cunchu_pdf[i].chapter_id!=0:
        if cunchu_pdf[i].block_id not in set_block_id:
            tiao_id = 1
            set_block_id.add(cunchu_pdf[i].block_id)
        lines=cunchu_pdf[i].content.split("\n")
        for line in lines:
            text=line.strip()
            m = RE_ARTICLE.match(text)
            if RE_ARTICLE.match(text):
                if fentiao_y:
                    # 先暂时存储循环结束后统一提交（防止主循环出错）
                    # print("----------------------------------------------------------")
                    if fentiao_y.strip():
                        cunchu_tiao.append(LawNode(
                            block_id=cunchu_pdf[i].block_id, node_type="article", chapter_id=cunchu_pdf[i].chapter_id,
                            article_id=tiao_id, content=remove_chapter_article_prefix(fentiao_y)
                        ))
                        # print(f"第{cunchu_pdf[i].block_id}块")
                        # print(f"第{cunchu_pdf[i].chapter_id}章")
                        # print(f"第{tiao_id}条")
                        # print(remove_chapter_article_prefix(fentiao_y))
                        total_sum+=1
                        tiao_id += 1
                fentiao_y = text + "\n"
            else:
                fentiao_y=fentiao_y+text+"\n"
        #推送最后一条
        if fentiao_y:
            # print("----------------------------------------------------------")
            cunchu_tiao.append(LawNode(
                block_id=cunchu_pdf[i].block_id, node_type="article", chapter_id=cunchu_pdf[i].chapter_id,
                article_id=tiao_id, content=remove_chapter_article_prefix(fentiao_y)
            ))
            # print(f"第{cunchu_pdf[i].block_id}块")
            # print(f"第{cunchu_pdf[i].chapter_id}章")
            # print(f"第{tiao_id}条")
            # print(remove_chapter_article_prefix(fentiao_y))
            total_sum += 1
print(f"================================共计{total_sum}条======================================")




#开始入库
DB_DSN=os.getenv("DB_DSN")
print(DB_DSN)
def batch_insert_law_nodes(nodes: list[LawNode]):
    sql = """
        INSERT INTO law_node(node_type, block_id, block_name, chapter_id, article_id, content)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    params = []
    for node in nodes:
        params.append((node.node_type, node.block_id, node.block_name,
                       node.chapter_id, node.article_id, node.content))
    with psycopg2.connect(DB_DSN) as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, params)
    print(f"入库完成，共 {len(params)} 条")

# batch_insert_law_nodes(cunchu_pdf)
# batch_insert_law_nodes(cunchu_tiao)


def split_long_text(text: str, max_len: int = 350, overlap: int = 30):
    text = text.strip()
    if len(text) <= max_len:
        return [text]

    # 按句末标点 + 编号切（多加了 1. 2. 这种）
    sentences = re.split(r'(?<=[。；;！？])|(?=\d+\.\s)', text)
    sentences = [s for s in sentences if s and s.strip()]

    chunks, buf = [], ""
    for s in sentences:
        if len(buf) + len(s) <= max_len:
            buf += s
        else:
            if buf:
                chunks.append(buf)
                buf = buf[-overlap:] + s if overlap > 0 else s
            else:
                for j in range(0, len(s), max_len - overlap):
                    chunks.append(s[j:j + max_len])
                buf = ""
    if buf.strip():
        chunks.append(buf)
    return chunks

# 进入向量数据库
RE_CLAUSE  = re.compile(rf'^[（(]{CN}[）)]')
a=0
b=0
vector=[]
no_vector=[]
for i in cunchu_tiao:
    # print("----------------------------")
    # print(i.content)
    #依旧分析，判断是否下面有条款（默认条款不存）
    lines=i.content
    lines=lines.split("\n")
    w=0
    content=""
    for line in lines:
        text=line.strip()
        if RE_CLAUSE.search(text):
            w=1
            break
    if w==1:
        #去除下面所有的
        content=""
        for line in lines:
            text=line.strip()
            match = RE_CLAUSE.search(text)
            if match:
                before = text[:match.start()].strip()
                content+=before
                #先存进数组
                # ves=embed_model.embed_query(content)
                vector.append(milusNode(
                    node_type="article",
                    block_id=i.block_id,
                    chapter_id=i.chapter_id,
                    article_id=i.article_id,
                    content=content,
                    is_kuan=True,
                    # embedding=ves
                ))
                a+=1
                break
            else:
                content += text

    if w==0:
        #直接切分入库
        #去除多余换行符号
        # content=""
        # for line in lines:

        content = "".join(
            ln.strip() for ln in i.content.split("\n") if ln.strip()
        )
        if content:
            if len(content)>400:
                for piece in split_long_text(content):
                    vector.append(milusNode(
                        node_type="article",
                        block_id=i.block_id,
                        chapter_id=i.chapter_id,
                        article_id=i.article_id,
                        content=piece,
                        is_kuan=False,
                    ))
            else:
                vector.append(milusNode(
                    node_type="article",
                    block_id=i.block_id,
                    chapter_id=i.chapter_id,
                    article_id=i.article_id,
                    content=content,
                    is_kuan=False,
                    # embedding=ves
                ))

        # print("===================================")
        b+=1
        # print(content)

print(f"======================={a}个有条款的==============")
print(f"======================={b}个没有条款的==============")

empty = [n for n in vector if not n.content or not n.content.strip()]
print(f"空内容节点: {len(empty)}")   # 应该是 0
# 1. 收集节点（纯 CPU，不花钱，随便跑）
List_embeding = []
PKL = "vector_1247.pkl"
if os.path.exists(PKL):
    with open(PKL, "rb") as f:
        vector = pickle.load(f)
    print(f"从缓存加载 {len(vector)} 条")
else:
    BATCH = 20
    i = 0
    while i < len(vector):
        vector2 = [vector[j].content for j in range(i, min(i+20, len(vector)))]
        # Listvector = embed_model.embed_documents(vector2)
        # List_embeding.extend(Listvector)
        i += 20
        print(f"编码 {min(i, len(vector))}/{len(vector)}")

    for node, emb in zip(vector, List_embeding):
        node.embedding = emb

    with open(PKL, "wb") as f:
        pickle.dump(vector, f)
    print(f"已保存 {PKL}")
from pymilvus import MilvusClient

client = MilvusClient("http://localhost:19530",db_name=db_name)

# 建库
db_name = "rag"
if db_name not in client.list_databases():
    client.create_database(db_name=db_name)
client.use_database(db_name=db_name)

# 建表
collection_name = "docs"
if not client.has_collection(collection_name):
    client.create_collection(
        collection_name=collection_name,
        dimension=1024,
        metric_type="COSINE",
    )
else:
    try:
        client.delete(collection_name=collection_name, filter="id >= 0")
        print("已清空旧数据")
    except Exception as e:
        print(f"清空跳过：{e}")

# ★ 转换：milusNode → Milvus data
data = [
    {
        "id": idx,
        "vector": node.embedding,        # ← embedding → vector
        "node_type": node.node_type,
        "block_id": node.block_id,
        "chapter_id": node.chapter_id,
        "article_id": node.article_id,
        "content": node.content,
        "is_kuan": node.is_kuan,
    }
    for idx, node in enumerate(vector)
]

# 批量 upsert
BATCH = 500
for k in range(0, len(data), BATCH):
    client.upsert(collection_name=collection_name, data=data[k:k+BATCH])
    print(f"写入 {min(k+BATCH, len(data))}/{len(data)}")

client.flush(collection_name=collection_name)
print(f"完成，共 {len(data)} 条 ✅")



print(f"vector 条数:  {len(vector)}")
print(f"vector 条数:  {len(vector)}")
print(f"向量维度:     {len(vector[0].embedding)}")






