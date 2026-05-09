# RegFlow Precheck

基于 `GraphRAG + FastAPI + LangGraph` 的企业登记与经营范围预审助手。

项目目标不是做通用聊天前端，而是把知识库问答能力收敛成一个更适合垂直场景的后端能力：围绕企业登记注册、营业执照和经营范围相关资料，输入登记事项与已有材料，输出缺项、风险和下一步动作，支持登记前材料核对与依据检索。

## 当前能力

- 使用 `GraphRAG` 索引企业登记法规、办事指南、示例材料与关系
- 基于知识库生成登记办理建议与材料核对结论
- 针对“登记事项 + 已具备材料”执行预审
- 输出缺项、经营范围风险提示、下一步动作
- 展示来源片段、引用审计和工作流步骤
- 记录交互历史与索引任务历史
- 支持文档上传、预览与索引重建

## 当前聚焦场景

- 公司设立登记材料预审
- 个体工商户设立登记材料核对
- 公司变更登记材料核对
- 营业执照相关登记事项问答
- 经营范围登记与许可经营项目判断辅助

## 输入语料组织

`input/` 是当前主线知识语料目录：

- `anchor_laws/`：公司法、公司登记管理条例、企业法人登记规则、经营范围登记规则
- `supporting_guides/`：企业登记注册与营业执照办理指南、登记答复口径等辅助资料
- `samples/`：个体工商户办理流程等样例材料

历史资料、旧产物和已废弃测试会迁移到 `garbage/` 归档，不参与当前主索引和默认测试范围。

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，填写模型与 API 配置：

```bash
cp .env.example .env
```

PowerShell 可用：

```powershell
Copy-Item .env.example .env
```

核心配置项：

```bash
GRAPHRAG_API_KEY=your-deepseek-api-key
GRAPHRAG_API_KEY_EMBEDDING=your-siliconflow-api-key
GRAPHRAG_LLM_MODEL=deepseek-chat
GRAPHRAG_EMBEDDING_MODEL=BAAI/bge-m3
API_BASE=https://api.deepseek.com/v1
API_BASE_EMBEDDING=https://api.siliconflow.cn/v1
PORT=8012
```

### 3. 准备知识库并构建索引

将 `.md` / `.txt` / `.pdf` 文档放入 `input/`（支持子目录），然后执行：

```bash
uv run reggraph-assistant index
```

### 4. 启动服务

```bash
uv run reggraph-assistant serve
```

访问 `http://localhost:8012/`

## CLI 命令

- `uv run reggraph-assistant serve`：启动 FastAPI 服务
- `uv run reggraph-assistant index`：重建 GraphRAG 索引
- `uv run reggraph-assistant status`：输出当前索引状态
- `uv run reggraph-assistant eval`：运行评测

## 核心接口

- `GET /api/health`：健康检查
- `GET /api/health/index`：索引健康状态
- `GET /api/index/status`：索引状态兼容端点
- `POST /api/index/rebuild`：重建索引
- `GET /api/index/task`：当前索引任务
- `GET /api/index/task/latest`：最近索引任务
- `GET /api/index/task/{task_id}`：指定索引任务详情
- `GET /api/history/index-tasks`：索引任务历史
- `GET /api/history/interactions`：交互历史
- `GET /api/documents`：文档列表
- `POST /api/documents/upload`：上传文档
- `GET /api/documents/preview`：预览文档
- `POST /api/workflow/run`：统一工作流入口
- `POST /api/eval/run`：运行评测

### 预审请求示例

```json
{
  "task": "公司设立登记前，需要先核对哪些材料？",
  "submitted_materials": [
    "公司章程",
    "法定代表人身份证明",
    "住所使用证明"
  ],
  "context": "有限责任公司首次设立，拟登记一般经营项目。"
}
```

## 项目结构

```text
src/reggraph_assistant/
├── app.py                  # FastAPI 应用与路由
├── cli.py                  # CLI 入口
├── settings.py             # Pydantic 配置加载
├── paths.py                # 目录路径解析
├── workflow.py             # LangGraph 工作流编排
├── workflow_state.py       # 工作流状态定义
├── service_context.py      # 领域范围与边界处理
├── schemas.py              # API / workflow 数据模型
├── indexing.py             # 索引管理对外接口
├── index_builder.py        # GraphRAG 索引构建与发布
├── index_tasks.py          # 索引任务状态管理
├── document_manager.py     # 文档上传、扫描、预览
├── retrieval.py            # 检索统一导出层
├── retrieval/              # GraphRAG / BM25 / Vector / Fusion 实现
├── agents/                 # planner / retriever / generator / reviewer / critic
├── persistence.py          # SQLite 状态存储
├── evaluation.py           # 评测入口
├── error_handlers.py       # 全局错误处理
├── logging_config.py       # 日志配置
├── preprocess.py           # 文档标准化预处理
├── citation_audit.py       # 引用审计
├── evidence.py             # 证据组织
├── llm_client.py           # LLM API 调用
└── graphrag_config.py      # GraphRAG 项目配置生成
```

## 运行流程

1. `app.py` 接收 `/api/workflow/run` 请求
2. `workflow.py` 进入 LangGraph 多 Agent 工作流
3. `PlannerAgent` 识别任务意图、范围和查询变体
4. `RetrieverAgent` 执行 `GraphRAG + BM25 + Vector` 多源检索并融合
5. `GeneratorAgent` 生成答案或预审结论
6. `ReviewerAgent / CriticAgent` 执行质量审查与反思迭代
7. 返回答案、来源、引用审计、工作流步骤与服务上下文

## 技术栈

- 后端：`FastAPI`
- 工作流：`LangGraph`
- 知识构建：`GraphRAG`
- 文档数据：`Pandas + Parquet`
- 向量增强：`FAISS + Embedding API`
- 前端：原生 `HTML/CSS/JavaScript`
- 运行工具：`uv`

## 测试

运行当前默认测试集：

```bash
uv run pytest
```

说明：

- 默认测试目录是 `tests/`
- 已明显落后于当前实现的旧测试会归档到 `garbage/tests/`
- `garbage/` 不参与 pytest 默认收集

## 当前限制

- 预审结论依赖知识库覆盖度，不替代正式窗口受理意见
- 地方差异、版本差异目前主要通过提示体现，尚未做显式规则层
- 两份原始法规 PDF 若存在加密或抽取质量问题，需替换为可解析版本
- 自动化测试仍在向当前工作流结构持续对齐

## 后续可继续演进

- 增加地方登记规则差异比对
- 增加经营范围规范目录与许可项目规则层
- 增加针对设立 / 变更 / 注销的评测集
- 接入 OpenWebUI Pipe / Pipeline

## 许可证

MIT License
