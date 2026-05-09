"""Generator Agent - 答案生成"""
from __future__ import annotations

from typing import Any

from .base import BaseAgent
from .state_types import GeneratorState
from ..schemas import Citation
from ..settings import Settings


class GeneratorAgent(BaseAgent):
    """生成 Agent - 负责基于检索结果生成答案"""

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        """执行生成逻辑（同步接口，实际调用异步方法）

        Args:
            state: 输入状态

        Returns:
            输出状态
        """
        import asyncio
        return asyncio.run(self.generate(
            task=state["task"],
            context=state.get("context", ""),
            intent=state["intent"],
            sources=state["sources"],
        ))

    async def generate(
        self,
        task: str,
        context: str,
        intent: str,
        sources: list[Citation],
    ) -> GeneratorState:
        """生成答案

        职责：
        1. 根据意图选择生成策略
        2. 材料清单：结构化清单 + 风险提示
        3. 政策解释：带引用的政策答复
        4. 绑定引用标记
        """
        if intent == "checklist":
            answer = await self._generate_checklist(task, context, sources)
        else:
            answer = await self._generate_policy_answer(task, context, sources)

        return GeneratorState(
            task=task,
            context=context,
            intent=intent,
            sources=sources,
            answer=answer,
        )

    async def _generate_checklist(self, task: str, context: str, sources: list[Citation]) -> str:
        """生成材料清单 - 基于已检索的 sources"""
        from ..citation_audit import bind_citation_markers

        # 构建来源文本
        sources_text = self._build_sources_text(sources)

        prompt = (
            "你是企业登记办理清单助手。请基于以下检索到的知识库内容，"
            "为用户生成适合执行的登记/准备清单。\n\n"
            "输出格式：\n"
            "## 清单标题\n\n"
            "**适用范围**：适用场景说明\n\n"
            "**任务摘要**：简要说明\n\n"
            "### 办理清单\n"
            "1. **材料名称**：详细说明\n"
            "2. **材料名称**：详细说明\n\n"
            "### 风险提示\n"
            "- 风险项\n\n"
            f"检索到的相关资料：\n{sources_text}\n\n"
            f"用户任务：{task}"
        )
        if context.strip():
            prompt += f"\n补充背景：{context.strip()}"

        # 调用 LLM 生成答案
        answer = await self.llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        return bind_citation_markers(answer, sources)

    async def generate_precheck(
        self,
        task: str,
        context: str,
        submitted_materials: list[str],
        sources: list[Citation],
    ) -> GeneratorState:
        """生成材料预审结果 - 基于已检索的 sources"""
        from ..citation_audit import bind_citation_markers

        # 构建来源文本
        sources_text = self._build_sources_text(sources)
        materials_list = "\n".join(f"- {m}" for m in submitted_materials)

        prompt = (
            "你是企业登记材料预审助手。请基于以下知识库内容，核对用户已提交的材料。\n\n"
            "输出格式：\n"
            "## 材料预审结果\n\n"
            "### ✅ 已提交材料\n"
            "- 材料名称\n\n"
            "### ❌ 缺项材料\n"
            "- 缺失的材料名称及说明\n\n"
            "### ⚠️ 风险提示\n"
            "- 风险项\n\n"
            "### 📋 下一步操作\n"
            "- 具体操作建议\n\n"
            f"检索到的相关资料：\n{sources_text}\n\n"
            f"用户任务：{task}\n\n"
            f"已提交材料：\n{materials_list}"
        )
        if context.strip():
            prompt += f"\n\n补充背景：{context.strip()}"

        # 调用 LLM 生成答案
        answer = await self.llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        answer = bind_citation_markers(answer, sources)

        return GeneratorState(
            task=task,
            context=context,
            intent="material_check",
            sources=sources,
            answer=answer,
        )

    async def _generate_policy_answer(self, task: str, context: str, sources: list[Citation]) -> str:
        """生成政策答复 - 基于已检索的 sources"""
        from ..citation_audit import bind_citation_markers

        # 构建来源文本
        sources_text = self._build_sources_text(sources)

        prompt = (
            "你是企业登记政策资料助手。请基于以下知识库资料回答用户问题。\n\n"
            "输出 Markdown，先给结论，再列关键依据和注意事项。"
            "不要输出 GraphRAG 内部 Data 引用，只保留面向办事人员可理解的依据表述。\n\n"
            f"检索到的相关资料：\n{sources_text}\n\n"
            f"用户问题：{task}"
        )
        if context.strip():
            prompt += f"\n补充背景：{context.strip()}"

        # 调用 LLM 生成答案
        answer = await self.llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        return bind_citation_markers(answer, sources)

    async def generate_with_feedback(
        self,
        task: str,
        context: str,
        intent: str,
        sources: list[Citation],
        feedback: str
    ) -> GeneratorState:
        """根据反馈重新生成答案（用于 Reflection Loop）

        Args:
            task: 用户任务
            context: 补充上下文
            intent: 任务意图
            sources: 引用来源
            feedback: 改进反馈（来自 Critic Agent）

        Returns:
            GeneratorState: 生成结果
        """
        # 将反馈融入生成提示
        enhanced_context = f"{context}\n\n改进要求：\n{feedback}" if context else f"改进要求：\n{feedback}"

        if intent == "checklist":
            answer = await self._generate_checklist(task, enhanced_context, sources)
        else:
            answer = await self._generate_policy_answer_with_feedback(
                task, enhanced_context, sources, feedback
            )

        return GeneratorState(
            task=task,
            context=enhanced_context,
            intent=intent,
            sources=sources,
            answer=answer,
        )

    async def _generate_policy_answer_with_feedback(
        self,
        task: str,
        context: str,
        sources: list[Citation],
        feedback: str
    ) -> str:
        """根据反馈生成改进的政策答复"""
        from ..citation_audit import bind_citation_markers

        # 构建来源文本
        sources_text = self._build_sources_text(sources)

        # 构建包含反馈的提示
        prompt = (
            "你是企业登记政策资料助手。请基于以下知识库资料回答用户问题。\n\n"
            "输出 Markdown，先给结论，再列关键依据和注意事项。"
            "不要输出 GraphRAG 内部 Data 引用，只保留面向办事人员可理解的依据表述。\n\n"
            f"检索到的相关资料：\n{sources_text}\n\n"
            f"用户问题：{task}\n\n"
            f"改进要求：\n{feedback}"
        )

        if context.strip() and feedback not in context:
            prompt += f"\n补充背景：{context.strip()}"

        # 调用 LLM 生成答案
        answer = await self.llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        return bind_citation_markers(answer, sources)

    def _build_sources_text(self, sources: list[Citation]) -> str:
        """构建来源文本

        Args:
            sources: 引用来源列表

        Returns:
            格式化的来源文本
        """
        if not sources:
            return "（未找到相关资料）"

        lines = []
        for source in sources:
            lines.append(f"[{source.index}] {source.document_name}")
            lines.append(source.snippet)
            lines.append("")  # 空行分隔

        return "\n".join(lines)
