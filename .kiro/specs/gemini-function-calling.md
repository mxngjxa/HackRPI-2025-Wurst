---
status: draft
---

# Gemini Function Calling 架构实现

## Overview

为现有的 RAG 聊天机器人添加 Gemini Function Calling 功能，让 AI 可以主动调用工具函数来获取数据，而不是被动接收预先检索的上下文。保留所有现有功能，支持在 RAG 模式和 Function Calling 模式之间切换。

## Goals

- 实现 Gemini Function Calling 架构
- AI 可以主动调用工具函数（semantic_search, list_documents, keyword_search）
- 保留所有现有功能（文档上传、向量搜索、RAG 模式）
- 支持模式切换（通过配置）
- 数据库连接方式不变（Python 直接连接 PostgreSQL）

## Non-Goals

- 不使用 MCP (Model Context Protocol) - 那是 Claude 的协议
- 不改变数据库连接方式
- 不需要额外的 Server
- 不删除现有的 RAG 实现
- 不修改 UI（除非必要）

## Background

### 当前架构（RAG）

```
用户提问 → Python 检索 → 格式化上下文 → 传给 Gemini → Gemini 生成答案
```

### 新架构（Function Calling）

```
用户提问 → Gemini 决定需要什么 → 调用工具函数 → Python 执行 → 返回结果 → Gemini 生成答案
```

### 关键区别

- **RAG**: 我们决定给 AI 什么信息
- **Function Calling**: AI 决定需要什么信息

## Detailed Design

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Gradio UI                        │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              chat_service.py                        │
│                                                     │
│  if USE_FUNCTION_CALLING:                          │
│      → GeminiFunctionCallingClient                 │
│  else:                                             │
│      → GeminiLLMClient (RAG)                       │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
┌───────────────────┐      ┌──────────────────────┐
│ RAG Mode          │      │ Function Calling     │
│ (existing)        │      │ Mode (new)           │
│                   │      │                      │
│ 1. Retrieve       │      │ 1. Send to Gemini    │
│ 2. Format         │      │    with tools        │
│ 3. Send to AI     │      │ 2. AI calls tools    │
│                   │      │ 3. Execute tools     │
│                   │      │ 4. Return results    │
│                   │      │ 5. AI generates      │
└───────────────────┘      └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │  function_handler.py │
                           │  (FunctionHandler)   │
                           └──────────┬───────────┘
                                      │
                                      ▼
                           ┌──────────────────────┐
                           │  function_tools.py   │
                           │                      │
                           │  - semantic_search   │
                           │  - list_documents    │
                           │  - keyword_search    │
                           └──────────┬───────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ retrieval.py │  │    db.py     │  │    db.py     │
            │ (vector)     │  │ (SQL query)  │  │ (SQL ILIKE)  │
            └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                   │                 │                 │
                   └─────────────────┼─────────────────┘
                                     ▼
                              ┌──────────────┐
                              │  PostgreSQL  │
                              │  + pgvector  │
                              └──────────────┘
```

### Components

#### 1. Configuration (`backend/config.py`)

新增配置变量：

```python
# Function Calling Configuration
USE_FUNCTION_CALLING: bool
ENABLE_SEMANTIC_SEARCH_TOOL: bool
ENABLE_KEYWORD_SEARCH_TOOL: bool
ENABLE_DOCUMENT_QUERY_TOOL: bool
MAX_FUNCTION_CALLS: int
```

#### 2. Function Tools (`backend/function_tools.py`) - NEW

定义 AI 可以调用的工具函数。

**工具列表**:

1. **semantic_search**
   - 描述: 使用向量相似度搜索相关内容
   - 参数: `query` (string), `top_k` (integer)
   - 实现: 调用 `get_context_chunks()`
   - 返回: JSON 格式的文本块列表

2. **list_documents**
   - 描述: 列出可用的文档
   - 参数: `include_preloaded` (boolean)
   - 实现: SQL 查询 documents 表
   - 返回: JSON 格式的文档列表

3. **keyword_search**
   - 描述: 关键词搜索
   - 参数: `keywords` (string), `limit` (integer)
   - 实现: SQL ILIKE 查询
   - 返回: JSON 格式的匹配结果

**关键函数**:
- `get_available_tools()` → List[Dict]: 返回工具定义（Gemini 格式）
- `execute_tool(name, args, session_id)` → str: 执行工具并返回结果

#### 3. Function Handler (`backend/function_handler.py`) - NEW

处理 Gemini Function Calling 的循环逻辑。

**类**: `FunctionHandler`

**方法**:
- `__init__()`: 初始化 Gemini 模型和工具
- `generate_answer(question, session_id, max_iterations)`: 主入口
- `_prepare_tools()`: 转换工具为 Gemini 格式
- `_build_system_instruction(session_id)`: 构建系统提示

**Function Calling 循环**:
1. 发送问题给 Gemini（带工具定义）
2. 检查响应是否包含函数调用
3. 如果有：执行函数，返回结果，继续循环
4. 如果没有：提取最终答案
5. 最多循环 `max_iterations` 次

#### 4. LLM Client (`backend/llm_client.py`)

**修改**:

1. 修改抽象类 `LLMClient`，添加 `session_id` 参数
2. 更新 `MockLLMClient` 和 `GeminiLLMClient`（添加参数）
3. 新增 `GeminiFunctionCallingClient` 类
4. 更新 `get_llm_client()` 工厂函数

**新类**: `GeminiFunctionCallingClient`
- 使用 `FunctionHandler` 处理函数调用
- 需要 `session_id` 参数
- 忽略 `context` 参数（AI 自己获取数据）

#### 5. Chat Service (`backend/chat_service.py`)

**修改**: `handle_question()` 函数

```python
if USE_FUNCTION_CALLING:
    # Function Calling 模式
    answer = llm_client.generate_answer("", question, session_id)
else:
    # RAG 模式
    chunks = get_context_chunks(question, session_id)
    context = format_context(chunks)
    answer = llm_client.generate_answer(context, question, session_id)
```

### Data Flow

#### RAG Mode (Existing)
```
Question → get_context_chunks() → format_context() 
→ GeminiLLMClient.generate_answer(context, question) 
→ Gemini API → Answer
```

#### Function Calling Mode (New)
```
Question → GeminiFunctionCallingClient.generate_answer(question, session_id)
→ FunctionHandler.generate_answer()
→ Gemini API (with tools)
→ Function Call: semantic_search
→ execute_tool() → get_context_chunks()
→ Return to Gemini
→ Gemini analyzes → Answer
```

### Error Handling

1. **工具执行错误**: 捕获异常，返回错误信息给 AI
2. **达到最大迭代次数**: 返回友好提示
3. **Gemini API 错误**: 捕获并记录，返回降级消息
4. **无效工具调用**: 验证工具名称，返回错误

### Testing Strategy

#### Unit Tests
- 测试每个工具函数
- 测试 FunctionHandler（mock Gemini 响应）
- 测试工具执行

#### Integration Tests
- 完整的 Function Calling 流程
- RAG 和 Function Calling 模式切换
- 错误场景

#### Manual Tests
- 上传文档并提问
- 验证 AI 调用正确的工具
- 比较两种模式的答案质量

---

## Implementation Plan

### Phase 1: 配置和基础设施
- Task 1: 更新 `backend/config.py`
- Task 2: 更新 `.env.example`

### Phase 2: 工具函数
- Task 3: 创建 `backend/function_tools.py`

### Phase 3: Function Handler
- Task 4: 创建 `backend/function_handler.py`

### Phase 4: LLM Client
- Task 5: 修改 `backend/llm_client.py`

### Phase 5: Service Layer
- Task 6: 修改 `backend/chat_service.py`

### Phase 6: 测试和文档
- Task 7: 测试两种模式
- Task 8: 更新 README.md

---

## Tasks

### Task 1: 更新配置文件
**File**: `backend/config.py`
**Priority**: High
**Estimated Time**: 15 minutes

在文件末尾添加 Function Calling 配置：

```python
# Function Calling Configuration
USE_FUNCTION_CALLING: bool = os.getenv("USE_FUNCTION_CALLING", "false").lower() in ("true", "yes", "1")

# Tool toggles
ENABLE_SEMANTIC_SEARCH_TOOL: bool = os.getenv("ENABLE_SEMANTIC_SEARCH_TOOL", "true").lower() in ("true", "yes", "1")
ENABLE_KEYWORD_SEARCH_TOOL: bool = os.getenv("ENABLE_KEYWORD_SEARCH_TOOL", "true").lower() in ("true", "yes", "1")
ENABLE_DOCUMENT_QUERY_TOOL: bool = os.getenv("ENABLE_DOCUMENT_QUERY_TOOL", "true").lower() in ("true", "yes", "1")

# Parameters
MAX_FUNCTION_CALLS: int = int(os.getenv("MAX_FUNCTION_CALLS", "5"))
```

在 `validate_config()` 中添加验证：

```python
if MAX_FUNCTION_CALLS <= 0:
    errors.append(f"MAX_FUNCTION_CALLS must be positive, got: {MAX_FUNCTION_CALLS}")
```

**Acceptance Criteria**:
- [ ] 配置变量已添加
- [ ] 验证逻辑已添加
- [ ] 可以导入: `python -c "from backend.config import USE_FUNCTION_CALLING"`
- [ ] 没有语法错误

---

### Task 2: 更新环境配置示例
**File**: `.env.example`
**Priority**: High
**Estimated Time**: 10 minutes

在文件末尾添加：

```bash
# ============================================
# Function Calling Configuration
# ============================================

# Enable Function Calling mode (AI actively calls functions to get data)
# When enabled: AI decides what information it needs and calls tools
# When disabled: Uses traditional RAG mode (retrieve then generate)
# Default: false (RAG mode)
USE_FUNCTION_CALLING=false

# Maximum number of function calls AI can make per question
# Prevents infinite loops and controls API costs
# Default: 5
MAX_FUNCTION_CALLS=5

# Tool Toggles (only used when USE_FUNCTION_CALLING=true)
# Enable/disable specific tools that AI can call

# Semantic search using vector similarity
ENABLE_SEMANTIC_SEARCH_TOOL=true

# Traditional keyword search
ENABLE_KEYWORD_SEARCH_TOOL=true

# Query document metadata
ENABLE_DOCUMENT_QUERY_TOOL=true
```

**Acceptance Criteria**:
- [ ] 配置已添加到 `.env.example`
- [ ] 注释清晰
- [ ] 默认值合理

---

### Task 3: 创建工具函数模块
**File**: `backend/function_tools.py` (NEW)
**Priority**: High
**Estimated Time**: 1.5 hours

创建新文件，实现三个工具函数。

**Implementation**: 参考 `backend/mcp_tools.py`（如果存在），但使用正确的配置变量名。

**Key Functions**:
1. `get_available_tools()` - 返回工具定义列表
2. `execute_tool(name, args, session_id)` - 执行工具
3. `_semantic_search(args, session_id)` - 语义搜索实现
4. `_list_documents(args, session_id)` - 列出文档实现
5. `_keyword_search(args, session_id)` - 关键词搜索实现

**Acceptance Criteria**:
- [ ] 文件已创建
- [ ] 三个工具已实现
- [ ] 工具返回 JSON 格式
- [ ] 错误处理完善
- [ ] 可以导入: `python -c "from backend.function_tools import get_available_tools; print(len(get_available_tools()))"`
- [ ] 输出应该是 `3`

---

### Task 4: 创建 Function Handler
**File**: `backend/function_handler.py` (NEW)
**Priority**: High
**Estimated Time**: 2 hours

创建新文件，实现 `FunctionHandler` 类。

**Class**: `FunctionHandler`

**Methods**:
- `__init__()`: 初始化 Gemini 模型和工具
- `generate_answer(question, session_id, max_iterations=5)`: 主方法
- `_prepare_tools()`: 准备工具定义
- `_build_system_instruction(session_id)`: 构建系统提示

**Function Calling Loop**:
```python
while iteration < max_iterations:
    # 发送消息
    response = chat.send_message(...)
    
    # 检查函数调用
    if has_function_calls:
        # 执行函数
        results = execute_tool(...)
        # 返回结果
        response = chat.send_message(results)
    else:
        # 提取最终答案
        return answer
```

**Acceptance Criteria**:
- [ ] 文件已创建
- [ ] `FunctionHandler` 类已实现
- [ ] Function calling 循环正确
- [ ] 错误处理完善
- [ ] 可以导入: `python -c "from backend.function_handler import FunctionHandler"`

---

### Task 5: 修改 LLM Client
**File**: `backend/llm_client.py`
**Priority**: High
**Estimated Time**: 1 hour

**Step 5.1**: 修改抽象类

```python
class LLMClient(ABC):
    @abstractmethod
    def generate_answer(self, context: str, question: str, session_id: str = None) -> str:
        pass
```

**Step 5.2**: 更新现有客户端

为 `MockLLMClient` 和 `GeminiLLMClient` 添加 `session_id` 参数（保持向后兼容）。

**Step 5.3**: 添加新客户端

```python
class GeminiFunctionCallingClient(LLMClient):
    def __init__(self):
        from backend.function_handler import FunctionHandler
        self.function_handler = FunctionHandler()
    
    def generate_answer(self, context: str, question: str, session_id: str = None) -> str:
        if not session_id:
            return "Error: Session ID is required."
        return self.function_handler.generate_answer(question, session_id)
```

**Step 5.4**: 更新工厂函数

```python
def get_llm_client() -> LLMClient:
    if USE_MOCK_LLM:
        return MockLLMClient()
    elif USE_FUNCTION_CALLING:
        return GeminiFunctionCallingClient()
    else:
        return GeminiLLMClient()
```

**Acceptance Criteria**:
- [ ] 抽象类已修改
- [ ] 现有客户端已更新
- [ ] 新客户端已添加
- [ ] 工厂函数已更新
- [ ] 可以导入: `python -c "from backend.llm_client import GeminiFunctionCallingClient"`
- [ ] 没有破坏现有功能

---

### Task 6: 修改 Chat Service
**File**: `backend/chat_service.py`
**Priority**: High
**Estimated Time**: 30 minutes

修改 `handle_question()` 函数：

```python
def handle_question(question: str, session_id: str) -> str:
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")
    
    logger.info(f"Handling question for session {session_id}: {question[:50]}...")
    
    try:
        llm_client = get_llm_client()
        
        from backend.config import USE_FUNCTION_CALLING
        
        if USE_FUNCTION_CALLING:
            # Function Calling mode
            logger.info("Using Function Calling mode")
            answer = llm_client.generate_answer("", question, session_id)
        else:
            # RAG mode
            logger.info("Using RAG mode")
            chunks = get_context_chunks(question, session_id)
            
            if not chunks:
                return "I don't have any documents to reference. Please upload some documents first."
            
            context = format_context(chunks)
            answer = llm_client.generate_answer(context, question, session_id)
        
        logger.info(f"Successfully generated answer (length: {len(answer)})")
        return answer
        
    except ValueError as e:
        raise
    except Exception as e:
        logger.error(f"Error generating answer: {str(e)}", exc_info=True)
        return "I apologize, but I encountered an error. Please try again."
```

**Acceptance Criteria**:
- [ ] 函数已修改
- [ ] 支持两种模式
- [ ] `session_id` 正确传递
- [ ] 错误处理完善
- [ ] 日志记录清晰

---

### Task 7: 测试
**Priority**: High
**Estimated Time**: 2 hours

**Test Plan**:

1. **RAG Mode** (`USE_FUNCTION_CALLING=false`)
   - [ ] 启动应用
   - [ ] 上传文档
   - [ ] 提问并验证答案
   - [ ] 检查日志显示 "RAG mode"
   - [ ] 功能正常

2. **Function Calling Mode** (`USE_FUNCTION_CALLING=true`)
   - [ ] 修改 `.env`: `USE_FUNCTION_CALLING=true`
   - [ ] 重启应用
   - [ ] 上传文档
   - [ ] 提问并验证答案
   - [ ] 检查日志显示 "Function Calling mode"
   - [ ] 检查日志显示工具调用
   - [ ] 功能正常

3. **工具调用验证**
   - [ ] 验证 AI 调用 `semantic_search`
   - [ ] 验证 AI 调用 `list_documents`
   - [ ] 验证 AI 调用 `keyword_search`

4. **错误测试**
   - [ ] 空问题
   - [ ] 无文档时提问
   - [ ] API 错误处理

**Acceptance Criteria**:
- [ ] 两种模式都正常工作
- [ ] 可以切换模式
- [ ] 没有回归问题
- [ ] 工具调用正确

---

### Task 8: 更新文档
**File**: `README.md`
**Priority**: Medium
**Estimated Time**: 30 minutes

在 README 中添加 Function Calling 说明：

1. 在 "Features" 部分后添加 "Architecture Modes" 部分
2. 解释 RAG 和 Function Calling 的区别
3. 添加配置示例
4. 更新环境变量表格

**Acceptance Criteria**:
- [ ] README 已更新
- [ ] 说明清晰
- [ ] 配置示例正确

---

## Dependencies

- Gemini API 必须支持 function calling (gemini-1.5-flash 支持)
- `google-generativeai` SDK 版本需支持 function calling
- 所有现有依赖保持不变

## Risks and Mitigations

**Risk 1**: Gemini function calling 可能不稳定
- **Mitigation**: 保留 RAG 模式作为默认和备选

**Risk 2**: 性能可能较慢（多次 API 调用）
- **Mitigation**: 设置合理的 `MAX_FUNCTION_CALLS`

**Risk 3**: 破坏现有功能
- **Mitigation**: 保持 RAG 模式不变，充分测试

**Risk 4**: API 成本增加
- **Mitigation**: 默认使用 RAG 模式，Function Calling 可选

## Success Metrics

- [ ] Function Calling 模式成功实现
- [ ] 可以通过配置切换模式
- [ ] 所有现有测试通过
- [ ] 文档完整
- [ ] RAG 模式性能不受影响
- [ ] Function Calling 模式产生高质量答案

## Open Questions

1. ~~应该修改 LLMClient 接口吗？~~ → 是的，添加 `session_id` 参数
2. ~~默认使用哪种模式？~~ → RAG 模式（`USE_FUNCTION_CALLING=false`）
3. ~~是否需要更多工具？~~ → 暂时不需要，三个工具足够
4. ~~如何处理长工具响应？~~ → 截断或限制，记录在日志中

## References

- Gemini Function Calling: https://ai.google.dev/gemini-api/docs/function-calling
- 当前 RAG 实现: `backend/retrieval.py`, `backend/llm_client.py`
- 实现文档: `FUNCTION_CALLING_IMPLEMENTATION.md`
