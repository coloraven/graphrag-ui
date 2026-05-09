from __future__ import annotations

from typing import Literal

from .schemas import ServiceContext


OUT_OF_SCOPE_KEYWORDS = (
    "股票",
    "彩票",
    "天气",
    "情感",
    "写代码",
    "论文",
    "小红书",
    "广告文案",
    "医疗诊断",
    "投诉举报",
    "投诉",
    "举报",
    "产品质量",
    "检验检测",
)
PERMIT_ADJACENT_KEYWORDS = (
    "食品经营许可",
    "餐饮店",
    "药品经营许可证",
    "公共场所卫生许可",
)
MATTER_KEYWORDS = (
    "公司设立登记",
    "公司变更登记",
    "公司注销登记",
    "企业登记",
    "企业登记注册",
    "个体工商户设立登记",
    "个体工商户",
    "营业执照",
    "经营范围",
    "公司登记",
)
SUBJECT_KEYWORDS = ("个体工商户", "企业", "公司", "分公司", "申请人", "经营者", "股东", "法定代表人")
SCENARIO_KEYWORDS = ("线上办理", "线下窗口", "变更", "注销", "新办", "材料补正", "设立", "经营范围变更")
CHANNEL_KEYWORDS = ("一网通办", "政务服务网", "线上", "线下", "窗口", "e窗通")
MATERIAL_HINTS = ("材料", "清单", "准备", "核对", "申请书", "章程", "住所证明")
PROCESS_HINTS = ("办理", "流程", "时限", "多久", "渠道", "窗口", "提交", "登记")
CONSULTATION_HINTS = ("咨询", "答复", "口径", "依据", "说明", "解释", "法条")
DOMAIN_KEYWORDS = MATTER_KEYWORDS + SUBJECT_KEYWORDS + SCENARIO_KEYWORDS + CHANNEL_KEYWORDS + MATERIAL_HINTS + PROCESS_HINTS
ServiceTaskType = Literal["consultation_reply", "material_check", "process_guide", "out_of_scope"]


def _first_match(text: str, keywords: tuple[str, ...]) -> str:
    return next((keyword for keyword in keywords if keyword in text), "")


def _extract_slots(text: str) -> dict[str, str]:
    slots: dict[str, str] = {}
    matter = _first_match(text, MATTER_KEYWORDS)
    subject = _first_match(text, SUBJECT_KEYWORDS)
    scenario = _first_match(text, SCENARIO_KEYWORDS)
    channel = _first_match(text, CHANNEL_KEYWORDS)
    if matter:
        slots["事项"] = matter
    if subject:
        slots["主体"] = subject
    if scenario:
        slots["情形"] = scenario
    if channel:
        slots["渠道"] = channel
    return slots


def _is_registration_adjacent(text: str) -> bool:
    return any(keyword in text for keyword in ("经营范围", "营业执照", "公司登记", "企业登记", "设立登记", "变更登记", "注销登记"))


def _has_domain_signal(text: str) -> bool:
    return _is_registration_adjacent(text) or any(keyword in text for keyword in DOMAIN_KEYWORDS)


def _classify_task_type(text: str) -> ServiceTaskType:
    if any(keyword in text for keyword in ("咨询", "答复", "口径")):
        return "consultation_reply"
    if any(keyword in text for keyword in MATERIAL_HINTS):
        return "material_check"
    if any(keyword in text for keyword in PROCESS_HINTS):
        return "process_guide"
    if any(keyword in text for keyword in CONSULTATION_HINTS):
        return "consultation_reply"
    return "consultation_reply"


def _missing_slots(task_type: ServiceTaskType, slots: dict[str, str]) -> list[str]:
    if task_type in {"material_check", "process_guide"} and "事项" not in slots:
        return ["事项"]
    return []


def build_service_context(task: str, context: str = "") -> ServiceContext:
    text = f"{task}\n{context}".strip()
    slots = _extract_slots(text)
    out_of_scope_keyword = _first_match(text, OUT_OF_SCOPE_KEYWORDS)
    permit_adjacent_keyword = _first_match(text, PERMIT_ADJACENT_KEYWORDS)
    if out_of_scope_keyword:
        return ServiceContext(
            task_type="out_of_scope",
            in_scope=False,
            handoff_required=True,
            slots=slots,
            boundary_reason=f"问题包含当前企业登记与经营范围资料库不支持的关键词：{out_of_scope_keyword}",
        )
    if permit_adjacent_keyword and not _is_registration_adjacent(text):
        return ServiceContext(
            task_type="out_of_scope",
            in_scope=False,
            handoff_required=True,
            slots=slots,
            boundary_reason=f"当前资料库不直接覆盖专项许可办理要求：{permit_adjacent_keyword}。",
        )
    if not _has_domain_signal(text):
        return ServiceContext(
            task_type="out_of_scope",
            in_scope=False,
            handoff_required=True,
            slots=slots,
            boundary_reason="该问题不属于当前企业登记、营业执照或经营范围资料库支持范围。",
        )

    task_type = _classify_task_type(text)
    missing_slots = _missing_slots(task_type, slots)
    return ServiceContext(
        task_type=task_type,
        in_scope=True,
        handoff_required=bool(missing_slots),
        slots=slots,
        missing_slots=missing_slots,
        boundary_reason="",
    )


def build_out_of_scope_answer(task: str, service_context: ServiceContext) -> str:
    reason = service_context.boundary_reason or "该问题不属于当前企业登记与经营范围资料库支持范围。"
    return (
        "## 暂不能直接答复\n\n"
        f"{reason}\n\n"
        "当前系统主要支持企业登记注册、营业执照、经营范围、设立/变更/注销材料核对与依据核查。"
    )
