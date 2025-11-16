# Function Calling 功能说明

## 什么是 Function Calling？

Function Calling 允许 AI 模型在回答问题时**主动调用函数**来获取所需信息，而不是预先提供所有上下文。

### 两种模式对比

**传统 RAG 模式（默认）：**
```
用户提问 → 系统检索相关文档 → 将文档作为上下文提供给 AI → AI 生成答案
```

**Function Calling 模式：**
```
用户提问 → AI 决定需要什么信息 → AI 调用工具查询数据库 → AI 基于结果生成答案
```

## 核心组件

### 1. 配置开关（backend/config.py）

```python
# 启用 Function Calling 模式
USE_FUNCTION_CALLING = True  # 在 .env 中设置

# 最大函数调用次数（防止无限循环）
MAX_FUNCTION_CALLS = 5

# 工具开关
ENABLE_SEMANTIC_SEARCH_TOOL = True   # 语义搜索
ENABLE_KEYWORD_SEARCH_TOOL = True    # 关键词搜索
ENABLE_DOCUMENT_QUERY_TOOL = True    # 文档列表查询
```

### 2. LLM 客户端（backend/llm_client.py）

```python
class GeminiFunctionCallingClient(LLMClient):
    """支持 Function Calling 的 Gemini 客户端"""
    
    def generate_answer(self, context: str, question: str, session_id: str) -> str:
        # context 参数被忽略
        # AI 会通过调用工具来获取所需信息
        return self.function_handler.generate_answer(question, session_id)
```

### 3. 函数处理器（backend/function_handler.py）

负责：
- 初始化 Gemini 模型并注册工具
- 处理 AI 的函数调用请求
- 执行工具并返回结果给 AI
- 管理多轮对话循环

关键方法：
```python
def generate_answer(self, question: str, session_id: str) -> str:
    """
    1. 发送用户问题给 AI
    2. 检查 AI 是否要调用函数
    3. 执行函数并返回结果
    4. 重复直到 AI 生成最终答案
    """
```

### 4. 工具定义（backend/mcp_tools.py）

提供三个工具供 AI 调用：

#### semantic_search
```python
{
    "name": "semantic_search",
    "description": "语义搜索，基于意义而非关键词查找相关文档",
    "parameters": {
        "query": "搜索查询",
        "top_k": "返回结果数量（默认5）"
    }
}
```

#### list_documents
```python
{
    "name": "list_documents",
    "description": "列出当前会话中的所有文档",
    "parameters": {
        "include_preloaded": "是否包含预加载文档（默认true）"
    }
}
```

#### keyword_search
```python
{
    "name": "keyword_search",
    "description": "关键词搜索，查找包含特定词语的文档",
    "parameters": {
        "keywords": "要搜索的关键词",
        "limit": "最大结果数（默认10）"
    }
}
```

## 工作流程示例

### 用户提问："总结一下文档内容"

**步骤 1：** AI 收到问题
```
System: 你有 semantic_search、list_documents、keyword_search 三个工具
User: 总结一下文档内容
```

**步骤 2：** AI 决定先查看有哪些文档
```
AI 调用: list_documents(include_preloaded=true)
返回: {"total": 2, "documents": [{"filename": "sample1.txt", ...}, ...]}
```

**步骤 3：** AI 决定搜索相关内容
```
AI 调用: semantic_search(query="文档主要内容", top_k=5)
返回: {"found": 5, "chunks": [...]}
```

**步骤 4：** AI 生成最终答案
```
AI: 根据文档内容，主要讨论了...
```

## 如何启用

### 1. 修改 .env 文件

```bash
# 启用 Function Calling
USE_FUNCTION_CALLING=true

# 关闭 Mock 模式（使用真实 API）
USE_MOCK_LLM=false

# 配置工具（可选）
ENABLE_SEMANTIC_SEARCH_TOOL=true
ENABLE_KEYWORD_SEARCH_TOOL=true
ENABLE_DOCUMENT_QUERY_TOOL=true

# 设置最大调用次数（可选）
MAX_FUNCTION_CALLS=5
```

### 2. 重启应用

```bash
python app.py
```

### 3. 测试

上传文档后提问，AI 会自动调用工具来获取信息。

## 数据库连接

所有工具都通过以下方式连接数据库：

```python
from backend.db import get_engine

engine = get_engine()  # 获取数据库连接池

with engine.connect() as conn:
    # 执行 SQL 查询
    result = conn.execute(query, params)
```

### 关键查询示例

**语义搜索（向量相似度）：**
```sql
SELECT dc.content, d.filename, 
       (dc.embedding <=> :query_embedding) AS distance
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
WHERE (d.is_preloaded = TRUE OR d.session_id = :session_id)
ORDER BY dc.embedding <=> :query_embedding
LIMIT :top_k
```

**关键词搜索：**
```sql
SELECT dc.content, d.filename
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
WHERE (d.is_preloaded = TRUE OR d.session_id = :session_id)
AND dc.content ILIKE :search_pattern
LIMIT :limit
```

## 优势

1. **更智能**：AI 自己决定需要什么信息
2. **更灵活**：可以多次调用不同工具
3. **更精确**：只获取真正需要的数据
4. **可扩展**：容易添加新工具

## 注意事项

1. **需要真实 API**：Function Calling 不支持 Mock 模式
2. **API 成本**：每次函数调用都会产生 API 费用
3. **Session ID 必需**：Function Calling 模式必须提供 session_id
4. **调用限制**：通过 MAX_FUNCTION_CALLS 防止无限循环

## 调试

查看日志了解 AI 的函数调用过程：

```bash
tail -f logs/app.log | grep -E "(Executing tool|Function calling)"
```

日志示例：
```
[INFO] Generating answer with function calling: 总结一下文档内容...
[INFO] Iteration 1: Processing 1 function call(s)
[INFO] Executing tool: list_documents
[INFO] Iteration 2: Processing 1 function call(s)
[INFO] Executing tool: semantic_search
[INFO] Generated final answer (length: 245)
```
