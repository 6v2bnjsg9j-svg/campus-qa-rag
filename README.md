# 校园制度智能问答系统

基于 **LangGraph + RAG** 的校园制度问答助手，支持多轮对话、语义检索与工具调用。

## 📖 项目背景

校园制度文档条目多达上千条，学生查询时依赖关键词搜索，命中率低、理解成本高。
本项目通过 Milvus 向量语义检索 + PostgreSQL 条款存储 + 大模型生成 的方式，让学生用自然语言提问即可获得准确的制度条款回答。



✨ 核心功能
🔍 语义检索：Milvus 向量库负责召回相关条款

📚 条款正文存储：PostgreSQL 保存制度条款的完整正文，按需精确调取

🔄 查询改写与重试：检索效果差时自动改写问题，最多 3 次

🤖 ReAct 工具调用：模型可自主调用工具，从 PostgreSQL 查询详细条款

💬 多轮对话记忆：保留最近 3 轮真实用户提问，支持上下文追问

🛡️ 幻觉控制：检索不到时明确返回"查不到"，不编造

## 🏗️ 架构

![架构图](docs/graph.png)

### 工作流节点说明

| 节点 | 职责 |
|---|---|
| `caijian_node` | 裁剪对话历史，保留最近 3 轮真实提问 |
| `buquan_node` | 补全/改写用户问题，使其独立完整 |
| `jiansuo_node` | Milvus 向量检索，召回相关文档 |
| `process_docs_node` | 去重、分数过滤、截断 |
| `is_have_node` | 判断是否有检索结果 |
| `press_sc_node` | 拼接 RAG 上下文与提示词 |
| `sc_node` | 调用主模型生成回答（可触发工具调用） |
| `tool_node` | 执行工具调用（查询详细条款） |
| `final_sc_node` | 工具调用超限时，用无工具模型兜底总结 |

## 🛠️ 技术栈

- **框架**：LangGraph / LangChain
- **向量库**：Milvus
- **大模型**：DeepSeek / Ollama（本地）
- **Embedding**：通义千问 Embedding
- **数据库**：PostgreSQL（条款详情）
- **语言**：Python 3.10+

## 🚀 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
conda create -n langgraph python=3.10
conda activate langgraph

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动 Milvus

```bash
docker run -d --name milvus-standalone \
  -p 19530:19530 -p 9091:9091 \
  milvusdb/milvus:v2.4.0 standalone
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，填入你自己的配置：

```bash
cp .env.example .env
# 编辑 .env，填入 API Key、数据库连接信息
```

### 4. 灌数据

#### 如果你想用自己的逻辑修改请提前删除vector_1247.pkl文件（我把我自己切的已经存了起来，程序是先读取这个的）

```bash
python scripts/ingest.py
```

### 5. 运行

```python
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from study.graph import builder

graph = builder.compile(checkpointer=InMemorySaver())
config = {"configurable": {"thread_id": "test"}}

for chunk in graph.stream(
    {
        "messages": [HumanMessage(content="如何办理转学？")],
        "original_question": "如何办理转学？",
    },
    config=config,
    stream_mode=["updates", "custom"],
):
    print(chunk)
```

## 📁 项目结构

```
study/
├── study/                  # 主包
│   ├── graph.py            # 工作流编排
│   ├── state.py            # 状态定义
│   ├── prompt.py           # 提示词模板
│   ├── db/                 # 数据层（Milvus、模型）
│   ├── nodes/              # 工作流节点
│   │   ├── preprocess.py   # 预处理（裁剪、改写）
│   │   ├── retrieval.py    # 检索（搜索、过滤）
│   │   ├── generate.py     # 生成（RAG、模型调用）
│   │   └── router.py       # 条件路由
│   └── tool/               # 工具定义
├── scripts/                # 一次性脚本（灌数据、调试）
├── docs/                   # 文档与架构图
└── requirements.txt
```

## 🎯 关键设计

### 切分逻辑
学生手册有天然的四级结构：**块 → 章 → 条 → 款**。
切分就按这个结构走，而不是用通用文本切分器硬切——硬切会把
"第X条"拦腰截断，正文和上下文一起报废。

切分结果是"**结构进 SQL、向量进 Milvus、id 做对齐**"：

| 单元 | 存哪 | 用途 |
|---|---|---|
| **条** | 正文进 PostgreSQL，向量进 Milvus | 主力检索单元，一个 `clause_id` 两边共用 |
| **款** | 进 PostgreSQL | 条下的细分内容，按 `clause_id` 精确召回 |
| **章** | 整章进 PostgreSQL，向量进 Milvus | 应对"这一章讲了什么"这类概览型问题 |

两个关键点：

- **`clause_id` 是 SQL 与 Milvus 对齐的唯一钥匙**。向量命中后凭
  这个 id 回 SQL 取正文，不会张冠李戴。
- **章级内容也走向量 + 工具召回**。学生问"第三章整体讲了什么"时，
  条级检索召不回整章，必须单独为章建一条向量入口。

### 1. 查询改写 + 重试循环

当检索结果不足（< 3 条）时，自动改写问题重新检索，最多 3 次。
避免因用户提问模糊导致的检索失败。

### 2. 对话历史裁剪

按 `HumanMessage` 计数而非按位置裁剪，保留最近 3 轮真实用户提问。
避免 RAG 注入的临时消息污染裁剪逻辑。

> 不做长期记忆：本场景属于科普型问答，多轮上下文依赖弱，
> 记忆越长越容易把无关历史带进 prompt，反而诱发幻觉。

### 3. 工具调用限制

通过 `tool_used` 标记限制单轮对话最多调用一次工具，
防止模型无限循环调用。

### 4. RAG 与工具的分工

- **RAG**：快速定位相关条款位置
- **工具**：按需查询详细条款正文
两者结合，兼顾响应速度与回答完整性。

## 📊 效果

测试集约 50 条，覆盖四类场景：单条查询（30）、章级概览（8）、多轮追问（8）、知识库外问题（8）。
测试方法：从知识库条款反向生成问题并绑定标准条款 id；忠实度/相关性/改写质量用 LLM-as-Judge 打 1-5 分；
性能按节点计时。完整数据见 `eval_data/report/report_latest.md`（优化前基线存于 `eval_data/results_baseline_0926/`）。

### 优化前 → 优化后

| 指标 | 优化前 | 优化后 |
|---|---|---|
| 单轮检索 Hit@5 | 93.3% | 93.3%（不退化） |
| 改写质量（裁判评分） | 2.92 / 5 | **4.67 / 5** |
| 改写关键约束保留率 | 41.7% | **91.7%** |
| 多轮追问 忠实度 | 3.38 | **4.5** |
| 多轮追问 相关性 | 3.12 | **4.5** |
| 多轮追问 误拒答 | 7 / 8 | **1 / 8** |
| 知识库外拒答准确率 | 8 / 8 | **8 / 8**（零强行作答） |
| 端到端平均延迟 | 17.3s | 21.4s（见优化方向 ①） |

### 这轮优化做了什么

测试定位出**查询改写节点是延迟与多轮准确率的双重瓶颈**：占全链路 82% 耗时，
且多轮 Hit@5 仅 12.5%——本地 1.5b 小模型做指代消解失败（复读上一轮、跑偏、
指代词原样保留），追问场景 8 条里 7 条被误杀成"查不到"。

优化措施：

1. **更换改写模型**：deepseek-r1:1.5b（Ollama 本地）→ qwen3.7-plus（API）
2. **重构改写提示词**：把"最新提问"从对话历史中拆出单独占位（弱模型不用在长历史里
   自己找改写对象）、few-shot 示例、明确禁止复读与编造
3. **顺带修复**：`prompt_final_template` 挂错提示词、工具消息孤儿导致 API 400
   （`final_sc_node` 现将 AI(tool_calls) 与 ToolMessage 成对清理，工具查回的条款正文拼入 context）

## 🔮 后续优化方向

- [ ] **接入 Rerank**：目前纯向量召回在某些长尾问题上还是会召回无关条款，打算加一层重排序（BGE-Rerank）过滤。
- [ ] **切分策略优化**：目前特殊文档（如表格、附件）还没处理得太好，打算单独做一个解析通道。
- [ ] **FastAPI 接口化**：目前只能命令行跑，下一步想封装成 Web API 给前端调用。
- [ ] **测试**：补充一些边界情况的单元测试（比如空检索、超长上下文）。
- [ ] **降低改写延迟**：当前 qwen3.7-plus 改写单次约 9s，疑似默认开启思考模式，
 计划传入参数关闭 thinking 验证；同时考虑把重试上限从 3 次降到 2 次
 （改写质量已达 4.67，重试的边际收益变小）
- [ ] **0.7 相似度阈值误杀**：测试发现阈值会误杀 3 条金标（集中在概览/多轮场景），
  计划降到 0.65 或按 docs 数量动态调整
- [ ] **引用规范**：仅约 47% 的回答带"第X条"式引用，计划在生成提示词中强化引用要求
- [ ] **single 忠实度复核**：3.8/5 存在裁判口径误伤（单条金标 vs 多文档合理回答），
  需人工复核 badcase 区分真幻觉与误判

## 🕳️ 踩坑与解决记录

1. **文档结构不规范的切分问题**
   - *问题*：学校文件编号格式极度不统一，用通用文本切分器会把“第X条”硬生生切断。
   - *解决*：放弃了通用切分，改用正则按“第X条”切，识别不了的走 fallback 逻辑；宁可切大也不切碎。
2. **RAG 临时消息污染历史对话**
   - *问题*：检索结果和工具调用记录会塞满 messages，如果按位置裁剪，真正的用户提问会被挤掉。
   - *解决*：改为按 `HumanMessage` 计数裁剪，只保留最近 3 轮真实提问，并结合改写节点补全指代。
3. **模型无限调用工具 / 调完不收尾**
   - *问题*：模型拿到工具结果后有时会陷入循环，或者迟迟不生成最终回答。
   - *解决*：加了 `tool_used` 状态标记限制单轮只调一次，并加了 `final_sc_node` 无工具模型兜底强行收尾。
4. **工具消息孤儿导致 API 400**
   - *问题*：`final_sc_node` 兜底时只删了带 `tool_calls` 的 AI 消息，对应的
     `ToolMessage` 变成孤儿，模型 API 校验报
     "Messages with role 'tool' must be a response to a preceding message with 'tool_calls'"。
   - *解决*：AI(tool_calls) 与 ToolMessage **成对清理**，工具查回的条款正文
     拼入 context 再兜底生成，工具结果不浪费。


## 👤 作者

王晨阳
邮箱：3107485668@qq.com