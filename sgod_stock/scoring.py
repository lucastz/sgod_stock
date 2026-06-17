"""Serenity 风格瓶颈候选公司的评分模型。

评分模型用于排序和暴露风险，不构成投资建议。每个分项都要求调用方提供 0-5 的
明确输入，避免系统从空白处猜测公司强弱。
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .models import CandidateCompany, ScoredCandidate, ScoreBreakdown


@dataclass(frozen=True)
class CandidateScoreInput:
    """候选公司评分输入。

    0-5 分字段必须来自人工研究或可追溯数据源；CLI 会要求 CSV 明确提供这些列。
    """

    candidate: CandidateCompany
    demand_certainty: float
    cost_shock: float
    failure_cost_jump: float
    mandatory_adoption: float
    bottleneck_strength: float
    evidence_strength: float
    pure_play: float
    expansion_difficulty: float
    customer_validation: float
    old_label_mismatch: float
    market_attention_gap: float
    timing_score: float
    crowding_risk: float
    a_share_crowding_risk: float
    dilution_risk: float
    financial_risk: float
    technical_substitution_risk: float
    evidence_gap_risk: float
    financing_dependence: str
    counterparty_quality: str
    execution_accessibility: str


POSITIVE_WEIGHTS = {
    "demand_certainty": 12.0,
    "cost_shock": 6.0,
    "failure_cost_jump": 8.0,
    "mandatory_adoption": 8.0,
    "bottleneck_strength": 16.0,
    "evidence_strength": 12.0,
    "pure_play": 8.0,
    "expansion_difficulty": 8.0,
    "customer_validation": 8.0,
    "old_label_mismatch": 5.0,
    "market_attention_gap": 5.0,
    "timing_score": 4.0,
}

PENALTY_WEIGHTS = {
    "crowding_risk": 10.0,
    "a_share_crowding_risk": 10.0,
    "dilution_risk": 8.0,
    "financial_risk": 8.0,
    "technical_substitution_risk": 10.0,
    "evidence_gap_risk": 10.0,
}

HARD_GATE_ALLOWED_VALUES = {
    "financing_dependence": ("LOW", "MED", "HIGH"),
    "counterparty_quality": ("LOW", "MED", "HIGH"),
    "execution_accessibility": ("ACCESSIBLE", "LIMITED", "INACCESSIBLE"),
}


def _validate_zero_to_five(name: str, value: float) -> None:
    """校验人工评分字段。

    直接抛出错误，不自动裁剪分数，避免把输入错误静默变成模型判断。
    """

    if value < 0 or value > 5:
        raise ValueError(f"{name} must be between 0 and 5, got {value}")


def recent_gain_penalty(recent_gain_pct: Optional[float]) -> float:
    """计算近期涨幅惩罚。

    MarsCarsChipDip 文章的关键启发是：真瓶颈也可能因为涨幅过大而失去入场优势。
    用户要求 300% 以上只触发中等惩罚，500% 以上才进入重罚；`> 800%` 仍按
    “只跟踪不挖掘”处理。
    """

    if recent_gain_pct is None:
        return 0.0
    if recent_gain_pct <= 100:
        return 0.0
    if recent_gain_pct <= 300:
        return (recent_gain_pct - 100) / 200 * 12.0
    if recent_gain_pct <= 500:
        return 20.0
    if recent_gain_pct <= 800:
        return 40.0
    return 70.0


def _normalize_hard_gate(name: str, value: str) -> str:
    """校验硬门槛字段。

    硬门槛是研究结论的前置约束，不用模糊文本兜底；CSV 必须填写允许值。
    """

    normalized = value.strip().upper()
    allowed = HARD_GATE_ALLOWED_VALUES[name]
    if normalized not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {value}")
    return normalized


def _hard_gate_score_cap(item: CandidateScoreInput, review_flags: List[str]) -> Optional[float]:
    """应用融资、交易对手和可交易性硬门槛。

    返回 None 表示不封顶；返回数字表示最终总分不能超过该上限。不可交易标的直接归零。
    """

    financing = _normalize_hard_gate("financing_dependence", item.financing_dependence)
    counterparty = _normalize_hard_gate("counterparty_quality", item.counterparty_quality)
    accessibility = _normalize_hard_gate("execution_accessibility", item.execution_accessibility)

    caps = []  # type: List[float]
    if financing == "HIGH":
        caps.append(35.0)
        review_flags.append("融资依赖 HIGH：即使产业逻辑强，也封顶为 Lottery/观察级别")
    if counterparty == "LOW":
        caps.append(50.0)
        review_flags.append("交易对手或 backlog 质量 LOW：合同/订单可靠性不足，分数封顶")
    if accessibility == "LIMITED":
        caps.append(60.0)
        review_flags.append("交易可达性 LIMITED：流动性、账户权限或市场准入限制仓位")
    if accessibility == "INACCESSIBLE":
        review_flags.append("交易可达性 INACCESSIBLE：当前账户无法执行，候选分数归零")
        return 0.0
    if not caps:
        return None
    return min(caps)


def score_candidate(item: CandidateScoreInput) -> ScoredCandidate:
    """对单个候选公司打分。

    正分来自瓶颈、证据、纯度、扩产难度、客户验证和市场未定价；负分来自近期涨幅、
    稀释风险和财务风险。输出保留 review_flags，提示人工复核。
    """

    numeric_fields = {
        "demand_certainty": item.demand_certainty,
        "cost_shock": item.cost_shock,
        "failure_cost_jump": item.failure_cost_jump,
        "mandatory_adoption": item.mandatory_adoption,
        "bottleneck_strength": item.bottleneck_strength,
        "evidence_strength": item.evidence_strength,
        "pure_play": item.pure_play,
        "expansion_difficulty": item.expansion_difficulty,
        "customer_validation": item.customer_validation,
        "old_label_mismatch": item.old_label_mismatch,
        "market_attention_gap": item.market_attention_gap,
        "timing_score": item.timing_score,
        "crowding_risk": item.crowding_risk,
        "a_share_crowding_risk": item.a_share_crowding_risk,
        "dilution_risk": item.dilution_risk,
        "financial_risk": item.financial_risk,
        "technical_substitution_risk": item.technical_substitution_risk,
        "evidence_gap_risk": item.evidence_gap_risk,
    }
    for name, value in numeric_fields.items():
        _validate_zero_to_five(name, value)

    positive_score = sum(
        numeric_fields[name] / 5.0 * weight for name, weight in POSITIVE_WEIGHTS.items()
    )
    penalty_score = sum(
        numeric_fields[name] / 5.0 * weight for name, weight in PENALTY_WEIGHTS.items()
    )
    gain_penalty = recent_gain_penalty(item.candidate.recent_gain_pct)
    penalty_score += gain_penalty

    review_flags = []  # type: List[str]
    if item.candidate.recent_gain_pct is None:
        review_flags.append("缺少近期涨幅数据，无法判断是否已经过度拥挤")
    elif item.candidate.recent_gain_pct > 800:
        review_flags.append("近期涨幅超过 800%，按文章纪律只跟踪不挖掘")
    elif item.candidate.recent_gain_pct > 500:
        review_flags.append("近期涨幅超过 500%，进入重罚区，需要等待新证据或回撤")
    elif item.candidate.recent_gain_pct > 300:
        review_flags.append("近期涨幅超过 300%，触发中等涨幅惩罚")
    if item.crowding_risk >= 4:
        review_flags.append("拥挤度风险高，必须检查是否已经成为市场共识交易")
    if item.a_share_crowding_risk >= 4:
        review_flags.append("A 股拥挤度风险高，必须检查换手率、龙虎榜和公司风险提示")
    if item.dilution_risk >= 4:
        review_flags.append("稀释风险高，必须检查 ATM/增发/可转债")
    if item.financial_risk >= 4:
        review_flags.append("财务风险高，必须检查现金流、债务和持续经营风险")
    if item.technical_substitution_risk >= 4:
        review_flags.append("技术替代风险高，必须验证路线是否可能被绕开")
    if item.evidence_gap_risk >= 4:
        review_flags.append("证据断裂风险高，必须补齐 S/A 级证据")
    if not item.candidate.evidence_links:
        review_flags.append("缺少证据链接，不能作为正式候选结论")

    total_score = max(0.0, positive_score - penalty_score)
    score_cap = _hard_gate_score_cap(item, review_flags)
    if score_cap is not None:
        total_score = min(total_score, score_cap)
    fields = {
        **numeric_fields,
        "recent_gain_penalty": gain_penalty,
        "score_cap": score_cap if score_cap is not None else -1.0,
    }
    return ScoredCandidate(
        candidate=item.candidate,
        score=ScoreBreakdown(
            total_score=round(total_score, 2),
            positive_score=round(positive_score, 2),
            penalty_score=round(penalty_score, 2),
            fields={key: round(value, 2) for key, value in fields.items()},
            review_flags=tuple(review_flags),
        ),
    )


def load_candidates_csv(path: Path) -> List[CandidateScoreInput]:
    """从 CSV 加载候选公司和评分输入。

    CSV 必须包含 schema 文档列名；缺列会直接抛错，避免使用隐式默认值。
    """

    required_columns = {
        "ticker",
        "company_name",
        "exchange",
        "industry_theme",
        "supply_chain_node",
        "demand_shock",
        "bottleneck_evidence",
        "evidence_links",
        "demand_certainty",
        "cost_shock",
        "failure_cost_jump",
        "mandatory_adoption",
        "bottleneck_strength",
        "evidence_strength",
        "pure_play",
        "expansion_difficulty",
        "customer_validation",
        "old_label_mismatch",
        "market_attention_gap",
        "timing_score",
        "crowding_risk",
        "a_share_crowding_risk",
        "dilution_risk",
        "financial_risk",
        "technical_substitution_risk",
        "evidence_gap_risk",
        "financing_dependence",
        "counterparty_quality",
        "execution_accessibility",
    }
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required_columns - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"candidate CSV missing columns: {sorted(missing)}")
        return [_row_to_score_input(row) for row in reader]


def _optional_float(value: Optional[str]) -> Optional[float]:
    """解析可选数字字段。

    空字符串表示公开数据暂缺；非空但无法解析会直接抛 ValueError。
    """

    if value is None or value.strip() == "":
        return None
    return float(value)


def _required_float(row: Dict[str, str], name: str) -> float:
    """解析必填数字字段。"""

    value = row.get(name, "")
    if value.strip() == "":
        raise ValueError(f"candidate CSV column {name} cannot be empty")
    return float(value)


def _row_to_score_input(row: Dict[str, str]) -> CandidateScoreInput:
    """把 CSV 行转换为评分对象。"""

    evidence_links = tuple(
        link.strip() for link in row["evidence_links"].split("|") if link.strip()
    )
    candidate = CandidateCompany(
        ticker=row["ticker"].strip(),
        company_name=row["company_name"].strip(),
        exchange=row["exchange"].strip(),
        industry_theme=row["industry_theme"].strip(),
        supply_chain_node=row["supply_chain_node"].strip(),
        demand_shock=row["demand_shock"].strip(),
        bottleneck_evidence=row["bottleneck_evidence"].strip(),
        evidence_links=evidence_links,
        recent_gain_pct=_optional_float(row.get("recent_gain_pct")),
        market_cap_usd=_optional_float(row.get("market_cap_usd")),
        notes=(row.get("notes") or "").strip() or None,
    )
    return CandidateScoreInput(
        candidate=candidate,
        demand_certainty=_required_float(row, "demand_certainty"),
        cost_shock=_required_float(row, "cost_shock"),
        failure_cost_jump=_required_float(row, "failure_cost_jump"),
        mandatory_adoption=_required_float(row, "mandatory_adoption"),
        bottleneck_strength=_required_float(row, "bottleneck_strength"),
        evidence_strength=_required_float(row, "evidence_strength"),
        pure_play=_required_float(row, "pure_play"),
        expansion_difficulty=_required_float(row, "expansion_difficulty"),
        customer_validation=_required_float(row, "customer_validation"),
        old_label_mismatch=_required_float(row, "old_label_mismatch"),
        market_attention_gap=_required_float(row, "market_attention_gap"),
        timing_score=_required_float(row, "timing_score"),
        crowding_risk=_required_float(row, "crowding_risk"),
        a_share_crowding_risk=_required_float(row, "a_share_crowding_risk"),
        dilution_risk=_required_float(row, "dilution_risk"),
        financial_risk=_required_float(row, "financial_risk"),
        technical_substitution_risk=_required_float(row, "technical_substitution_risk"),
        evidence_gap_risk=_required_float(row, "evidence_gap_risk"),
        financing_dependence=row["financing_dependence"].strip(),
        counterparty_quality=row["counterparty_quality"].strip(),
        execution_accessibility=row["execution_accessibility"].strip(),
    )
