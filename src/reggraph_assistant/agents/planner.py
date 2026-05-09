"""Planner Agent - 任务规划和查询分解"""
from __future__ import annotations

from typing import Any

from .base import BaseAgent
from .state_types import PlannerState
from ..schemas import ServiceContext
from ..settings import Settings


class PlannerAgent(BaseAgent):
    """规划 Agent - 负责任务分析和检索策略规划"""

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """执行规划逻辑

        Args:
            state: 输入状态

        Returns:
            输出状态
        """
        return self.analyze_task(state["task"], state.get("context", ""))

    def analyze_task(self, task: str, context: str = "") -> PlannerState:
        """分析任务并生成执行计划

        职责：
        1. 理解用户意图（材料清单 vs 政策解释）
        2. 识别业务场景标签
        3. 生成查询变体
        4. 规划检索策略（GraphRAG + BM25 + Vector）
        """
        from ..service_context import build_service_context
        from ..evidence import extract_scenario_tags, build_query_variants

        # 1. 构建服务上下文
        service_context = build_service_context(task, context)

        # 2. 识别意图
        intent = self._detect_intent(task, service_context)

        # 3. 提取场景标签
        scenario_tags = extract_scenario_tags(task, [context] if context else [])

        # 4. 生成查询变体
        query_variants = build_query_variants(task, scenario_tags)

        # 5. 规划检索策略
        retrieval_plan = self._plan_retrieval_strategy(intent, scenario_tags)

        return PlannerState(
            task=task,
            context=context,
            service_context=service_context,
            intent=intent,
            scenario_tags=scenario_tags,
            query_variants=query_variants,
            retrieval_plan=retrieval_plan,
        )

    def _detect_intent(self, task: str, service_context: ServiceContext) -> str:
        """检测用户意图（使用 LLM few-shot 分类）"""
        # 首先检查是否越界
        if service_context.task_type == "out_of_scope" or not service_context.in_scope:
            return "out_of_scope"

        if service_context.task_type in {"material_check", "process_guide"}:
            return "checklist"

        # 使用 LLM 进行意图分类（few-shot）
        return self._llm_intent_classification(task)

    def _llm_intent_classification(self, task: str) -> str:
        """使用 LLM 进行意图分类（few-shot）"""
        prompt = f"""你是一个意图分类助手。请判断用户的任务属于以下哪一类：

1. policy_answer（政策咨询）：用户想了解政策规定、法律条文、办事口径、解释说明
2. checklist（材料清单）：用户想知道需要准备什么材料、办理流程、操作步骤

示例：
- "如何办理营业执照？" → checklist
- "营业执照的法律依据是什么？" → policy_answer
- "公司设立登记需要准备什么材料？" → checklist
- "经营范围变更的依据是什么？" → policy_answer
- "我想办理个体工商户设立登记" → checklist
- "公司登记事项包括哪些内容？" → policy_answer

用户任务：{task}

请只回答 policy_answer 或 checklist，不要有其他内容。"""

        try:
            # 使用统一的 LLM 客户端（异步转同步）
            import asyncio
            result = asyncio.run(self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=20,
                timeout=5.0,
            ))

            # 验证返回值
            intent = result.strip().lower()
            if "checklist" in intent:
                return "checklist"
            elif "policy" in intent:
                return "policy_answer"

        except Exception as e:
            # LLM 调用失败，回退到关键词匹配
            from logging import getLogger
            logger = getLogger(__name__)
            logger.warning(f"LLM intent classification failed, falling back to keyword matching: {e}")

        # 回退方案：使用关键词匹配
        STRONG_POLICY_HINTS = tuple(self.settings.intent.policy_hints)
        CHECKLIST_HINTS = tuple(self.settings.intent.checklist_hints)

        if any(hint in task for hint in STRONG_POLICY_HINTS):
            return "policy_answer"
        if any(hint in task for hint in CHECKLIST_HINTS):
            return "checklist"

        return "policy_answer"

    def _plan_retrieval_strategy(self, intent: str, scenario_tags: list[str]) -> dict:
        """规划检索策略

        三路检索默认全部启用：
        - GraphRAG：知识图谱社区检索
        - BM25：关键词精确匹配
        - Vector：语义相似度检索（FAISS）
        - 融合方法：RRF（Reciprocal Rank Fusion）
        """
        strategy = {
            "use_graphrag": True,
            "use_bm25": True,
            "use_vector": True,  # 默认启用向量检索
            "fusion_method": "rrf",
            "intent": intent,  # 传递意图给检索器，用于自适应权重
            "priority": "graphrag" if intent == "checklist" else "semantic",
        }

        return strategy
