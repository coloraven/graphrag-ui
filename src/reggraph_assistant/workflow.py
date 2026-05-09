"""LangGraph Multi-Agent 工作流

基于 LangGraph 的 Multi-Agent 架构：
- 状态管理（TypedDict）
- 可视化（Mermaid 图）
- 持久化（Checkpoint）
- 条件路由（动态分支）
- Reflection Loop（自我改进）

架构：
- Planner Agent: 任务规划
- Retriever Agent: 多源检索（GraphRAG + BM25 + Vector）
- Generator Agent: 答案生成
- Reviewer Agent: 质量审查
- Critic Agent: 质量评估
- Reflection Loop: 自我改进循环

工作流：

START
  ↓
planner_node (任务规划)
  ↓
route_by_scope (范围判断)
  ├─ 越界 → out_of_scope_node → END
  └─ 范围内 ↓
retriever_node (多源检索)
  ↓
generator_node (答案生成)
  ↓
reviewer_node (质量审查)
  ↓
route_by_reflection (是否需要反思)
  ├─ 质量达标 → END
  ├─ 达到最大迭代次数 → END
  └─ 需要改进 ↓
reflection_counter_node (计数)
  ↓
critic_node (质量评估)
  ↓
generator_node (重新生成) ← 形成循环
"""
from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from .agents.critic import CriticAgent
from .agents.generator import GeneratorAgent
from .agents.planner import PlannerAgent
from .agents.retriever import RetrieverAgent
from .agents.reviewer import ReviewerAgent
from .schemas import CitationAuditReport, EvidencePack, RiskFlag, ServiceContext, WorkflowResponse
from .service_context import build_out_of_scope_answer
from .settings import Settings
from .workflow_state import AgentState, create_step


# ============ 常量配置 ============

DEFAULT_QUALITY_THRESHOLD = 0.8
DEFAULT_MAX_REFLECTION_ITERATIONS = 3


# ============ 路由函数 ============

def route_by_scope(state: AgentState) -> str:
    """根据范围判断路由

    Args:
        state: 当前工作流状态

    Returns:
        下一个节点名称
    """
    service_context = state["service_context"]
    if service_context.in_scope:
        return "retriever_node"
    else:
        return "out_of_scope_node"


def route_by_reflection(state: AgentState) -> str:
    """根据 Reflection 配置和质量分数决定是否重试

    决策逻辑：
    1. 如果未启用 Reflection → 直接结束
    2. 如果质量达标 → 直接结束
    3. 如果达到最大迭代次数 → 直接结束
    4. 否则 → 进入 Reflection Loop

    Args:
        state: 当前工作流状态

    Returns:
        下一个节点名称或 END
    """
    # 检查是否启用 Reflection
    if not state.get("enable_reflection", True):
        return END

    # 检查质量是否达标
    quality_score = state.get("quality_score", 0.0)
    quality_threshold = state.get("quality_threshold", DEFAULT_QUALITY_THRESHOLD)
    if quality_score >= quality_threshold:
        return END

    # 检查是否达到最大迭代次数
    iteration = state.get("reflection_iteration", 0)
    max_iterations = state.get("max_reflection_iterations", DEFAULT_MAX_REFLECTION_ITERATIONS)
    if iteration >= max_iterations:
        return END

    # 进入 Reflection Loop
    return "reflection_counter_node"


# ============ 节点函数 ============

def planner_node(state: AgentState, settings: Settings) -> dict:
    """Planner Agent 节点：任务规划

    Args:
        state: 当前工作流状态
        settings: 应用配置

    Returns:
        状态更新字典
    """
    if all(
        key in state
        for key in ("service_context", "intent", "scenario_tags", "query_variants", "retrieval_plan")
    ):
        plan_state = {
            "service_context": state["service_context"],
            "intent": state["intent"],
            "scenario_tags": state["scenario_tags"],
            "query_variants": state["query_variants"],
            "retrieval_plan": state["retrieval_plan"],
        }
        detail_prefix = "复用预规划结果"
    else:
        planner = PlannerAgent(settings)
        plan_state = planner.analyze_task(state["task"], state.get("context", ""))
        detail_prefix = "完成任务规划"

    detail = (
        f"{detail_prefix}；意图：{plan_state['intent']}；"
        f"场景：{', '.join(plan_state['scenario_tags']) or '通用'}；"
        f"查询变体：{len(plan_state['query_variants'])} 个"
    )

    return {
        "service_context": plan_state["service_context"],
        "intent": plan_state["intent"],
        "scenario_tags": plan_state["scenario_tags"],
        "query_variants": plan_state["query_variants"],
        "retrieval_plan": plan_state["retrieval_plan"],
        "steps": [create_step("planner", "任务规划", detail)],
    }


def out_of_scope_node(state: AgentState) -> dict:
    """越界处理节点

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    service_context = state["service_context"]
    answer = build_out_of_scope_answer(state["task"], service_context)

    evidence_pack = EvidencePack(
        query=state["task"],
        intent="out_of_scope",
        retrieval_strategy="Boundary guardrail only",
        risk_flags=[
            RiskFlag(
                level="warning",
                message=service_context.boundary_reason or "问题超出当前客服知识库范围，需要人工复核。",
            )
        ],
    )

    return {
        "answer": answer,
        "sources": [],
        "evidence_pack": evidence_pack,
        "citation_audit": CitationAuditReport(),
        "quality_score": 0.0,
        "steps": [create_step("boundary_guard", "范围护栏", "命中越界问题，停止检索生成并返回边界引导。")],
    }


async def retriever_node(state: AgentState, settings: Settings) -> dict:
    """Retriever Agent 节点：多源并行检索

    Args:
        state: 当前工作流状态
        settings: 应用配置

    Returns:
        状态更新字典
    """
    retriever = RetrieverAgent(settings)
    retrieval_state = await retriever.retrieve(
        query=state["task"],
        query_variants=state["query_variants"],
        retrieval_plan=state["retrieval_plan"],
    )

    detail = (
        f"GraphRAG: {len(retrieval_state.get('graphrag_sources', []))} 条；"
        f"BM25: {len(retrieval_state.get('bm25_sources', []))} 条；"
        f"Vector: {len(retrieval_state.get('vector_sources', []))} 条；"
        f"融合: {len(retrieval_state.get('fused_sources', []))} 条"
    )

    return {
        "graphrag_sources": retrieval_state.get("graphrag_sources", []),
        "bm25_sources": retrieval_state.get("bm25_sources", []),
        "vector_sources": retrieval_state.get("vector_sources", []),
        "fused_sources": retrieval_state.get("fused_sources", []),
        "steps": [create_step("retriever", "多源检索", detail)],
    }


async def generator_node(state: AgentState, settings: Settings) -> dict:
    """Generator Agent 节点：答案生成

    Args:
        state: 当前工作流状态
        settings: 应用配置

    Returns:
        状态更新字典
    """
    generator = GeneratorAgent(settings)
    submitted_materials = state.get("submitted_materials", [])
    service_context = state.get("service_context")
    is_material_precheck = service_context is not None and service_context.task_type == "material_check"

    if is_material_precheck:
        generator_state = await generator.generate_precheck(
            task=state["task"],
            context=state.get("context", ""),
            submitted_materials=submitted_materials,
            sources=state["fused_sources"],
        )
        detail = f"生成 {len(generator_state['answer'])} 字预审结果，引用 {len(generator_state['sources'])} 个来源"
        return {
            "answer": generator_state["answer"],
            "sources": generator_state["sources"],
            "steps": [create_step("generator", "预审结果生成", detail)],
        }

    # 如果是 Reflection 迭代，使用带反馈的生成方法
    if state.get("reflection_iteration", 0) > 0:
        feedback = "\n".join(state.get("improvement_suggestions", []))
        generator_state = await generator.generate_with_feedback(
            task=state["task"],
            context=state.get("context", ""),
            intent=state["intent"],
            sources=state["fused_sources"],
            feedback=feedback,
        )
    else:
        generator_state = await generator.generate(
            task=state["task"],
            context=state.get("context", ""),
            intent=state["intent"],
            sources=state["fused_sources"],
        )

    detail = f"生成 {len(generator_state['answer'])} 字答案，引用 {len(generator_state['sources'])} 个来源"

    return {
        "answer": generator_state["answer"],
        "sources": generator_state["sources"],
        "steps": [create_step("generator", "答案生成", detail)],
    }


def reviewer_node(state: AgentState, settings: Settings) -> dict:
    """Reviewer Agent 节点：质量审查

    Args:
        state: 当前工作流状态
        settings: 应用配置

    Returns:
        状态更新字典
    """
    reviewer = ReviewerAgent(settings)
    review_state = reviewer.review(
        task=state["task"],
        intent=state["intent"],
        answer=state["answer"],
        sources=state["sources"],
        scenario_tags=state.get("scenario_tags", []),
        query_variants=state.get("query_variants", []),
    )

    detail = (
        f"质量分数：{review_state['quality_score']:.2f}；"
        f"引用覆盖率：{review_state['citation_audit'].citation_coverage:.1%}；"
        f"问题：{len(review_state.get('issues', []))} 个"
    )

    return {
        "evidence_pack": review_state["evidence_pack"],
        "citation_audit": review_state["citation_audit"],
        "quality_score": review_state["quality_score"],
        "steps": [create_step("reviewer", "质量审查", detail)],
    }


def critic_node(state: AgentState, settings: Settings) -> dict:
    """Critic Agent 节点：质量评估（Reflection 专用）

    Args:
        state: 当前工作流状态
        settings: 应用配置

    Returns:
        状态更新字典
    """
    critic = CriticAgent(settings)
    critique = critic.evaluate(
        task=state["task"],
        answer=state["answer"],
        sources=state["sources"],
        intent=state["intent"],
    )

    detail = (
        f"质量分数：{critique.score:.2f}；"
        f"是否达标：{'是' if critique.is_acceptable else '否'}；"
        f"问题：{len(critique.issues)} 个"
    )

    return {
        "quality_score": critique.score,
        "improvement_suggestions": critique.improvement_suggestions,
        "steps": [create_step("critic", "质量评估", detail)],
    }


def reflection_counter_node(state: AgentState) -> dict:
    """Reflection 计数器节点

    Args:
        state: 当前工作流状态

    Returns:
        状态更新字典
    """
    current_iteration = state.get("reflection_iteration", 0)
    new_iteration = current_iteration + 1

    detail = f"第 {new_iteration} 轮反思改进"

    return {
        "reflection_iteration": new_iteration,
        "steps": [create_step("reflection_counter", "Reflection 迭代", detail)],
    }


# ============ 图构建 ============

def build_agent_graph(settings: Settings) -> StateGraph:
    """构建 Multi-Agent LangGraph 工作流

    Returns:
        编译好的 StateGraph 实例
    """
    graph = StateGraph(AgentState)

    # 添加节点（使用 partial 绑定 settings）
    graph.add_node("planner_node", partial(planner_node, settings=settings))
    graph.add_node("out_of_scope_node", out_of_scope_node)
    graph.add_node("retriever_node", partial(retriever_node, settings=settings))
    graph.add_node("generator_node", partial(generator_node, settings=settings))
    graph.add_node("reviewer_node", partial(reviewer_node, settings=settings))
    graph.add_node("critic_node", partial(critic_node, settings=settings))
    graph.add_node("reflection_counter_node", reflection_counter_node)

    # 添加边
    graph.add_edge(START, "planner_node")
    graph.add_conditional_edges("planner_node", route_by_scope)
    graph.add_edge("out_of_scope_node", END)
    graph.add_edge("retriever_node", "generator_node")
    graph.add_edge("generator_node", "reviewer_node")
    graph.add_conditional_edges("reviewer_node", route_by_reflection)
    graph.add_edge("reflection_counter_node", "critic_node")
    graph.add_edge("critic_node", "generator_node")  # 形成循环

    return graph


# ============ 运行函数 ============

async def run_workflow(
    task: str,
    settings: Settings,
    context: str = "",
    submitted_materials: list[str] | None = None,
    enable_reflection: bool = True,
    quality_threshold: float = 0.8,
    max_reflection_iterations: int = 3,
    timeout: float = 120.0,
) -> WorkflowResponse:
    """运行 Multi-Agent 工作流

    Args:
        task: 用户任务
        settings: 系统配置
        context: 补充上下文
        submitted_materials: 已提交材料列表
        enable_reflection: 是否启用 Reflection Loop
        quality_threshold: 质量阈值（0-1）
        max_reflection_iterations: 最大反思迭代次数
        timeout: 工作流超时时间（秒），默认 120 秒

    Returns:
        WorkflowResponse: 包含答案、来源、审计报告等

    Raises:
        asyncio.TimeoutError: 工作流执行超时
    """
    import asyncio
    import logging

    logger = logging.getLogger(__name__)

    # 构建图
    graph = build_agent_graph(settings)
    workflow = graph.compile()

    # 初始状态（planner_node 会填充 service_context、intent 等字段）
    submitted_materials_list = submitted_materials or []

    initial_state: AgentState = {
        "task": task,
        "context": context,
        "submitted_materials": submitted_materials_list,
        "enable_reflection": enable_reflection,
        "quality_threshold": quality_threshold,
        "max_reflection_iterations": max_reflection_iterations,
        "reflection_iteration": 0,
        "steps": [],
    }

    # 执行工作流（异步，带超时保护）
    try:
        final_state = await asyncio.wait_for(
            workflow.ainvoke(initial_state),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"Workflow timeout after {timeout} seconds")
        # 返回降级响应
        return WorkflowResponse(
            intent="error",
            answer=f"## 处理超时\n\n工作流执行超过 {timeout} 秒，已自动终止。请简化问题或稍后重试。",
            sources=[],
            service_context=ServiceContext(),
            evidence_pack=EvidencePack(),
            citation_audit=CitationAuditReport(),
            steps=[],
            content_format="markdown",
        )

    # 获取结果
    answer = final_state.get("answer", "")
    sources = final_state.get("sources", [])

    # 构建响应
    return WorkflowResponse(
        intent=final_state.get("intent", "policy_answer"),
        answer=answer,
        sources=sources,
        service_context=final_state.get("service_context") or ServiceContext(),
        evidence_pack=final_state.get("evidence_pack") or EvidencePack(),
        citation_audit=final_state.get("citation_audit") or CitationAuditReport(),
        steps=final_state.get("steps", []),
        content_format="markdown",
    )
