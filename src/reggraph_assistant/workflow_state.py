"""工作流状态定义

定义 LangGraph Multi-Agent 工作流的状态结构
"""
from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from .agents.state_types import GeneratorState, PlannerState, RetrieverState, ReviewerState
from .schemas import WorkflowStep


class CoreState(TypedDict):
    """核心必需状态字段"""
    task: str
    steps: Annotated[list[WorkflowStep], lambda x, y: x + y]


class ReflectionState(TypedDict, total=False):
    """Reflection 控制状态"""
    reflection_iteration: int
    max_reflection_iterations: int
    quality_threshold: float
    enable_reflection: bool
    improvement_suggestions: list[str]


class OptionalState(TypedDict, total=False):
    """其他可选状态字段"""
    context: str
    submitted_materials: list[str]


class AgentState(CoreState, PlannerState, RetrieverState, GeneratorState, ReviewerState, ReflectionState, OptionalState):
    """Multi-Agent 工作流状态

    组合所有状态字段，核心字段必需，其他字段可选
    """
    pass


def create_step(key: str, title: str, detail: str, status: Literal["pending", "running", "completed", "failed"] = "completed") -> WorkflowStep:
    """创建执行步骤

    Args:
        key: 步骤键
        title: 步骤标题
        detail: 步骤详情
        status: 步骤状态

    Returns:
        WorkflowStep 对象
    """
    return WorkflowStep(key=key, title=title, detail=detail, status=status)


def append_step(state: AgentState, key: str, title: str, detail: str) -> dict:
    """添加执行步骤到状态

    Args:
        state: 当前状态
        key: 步骤键
        title: 步骤标题
        detail: 步骤详情

    Returns:
        包含新步骤的状态更新字典
    """
    return {"steps": [create_step(key, title, detail)]}
