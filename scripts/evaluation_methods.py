#!/usr/bin/env python3
"""
Deep Research 评估方法演示与对比工具

演示和对比不同的评估方法：
1. 精确匹配 (Exact Match) - GAIA 风格
2. Quasi-Exact Match - 归一化后匹配
3. LLM-as-Judge - 语义等价判断
4. 三级评分 - CORRECT/INCORRECT/NOT_ATTEMPTED
5. 多维度 Rubric 评分 - ResearchRubrics 风格
6. 成对比较 - DeepConsult 风格

包含完整可运行的演示代码和评分函数。

用法:
    python evaluation_methods.py                   # 默认演示所有方法
    python evaluation_methods.py --method em       # 仅演示精确匹配
    python evaluation_methods.py --method llm_judge # 仅演示 LLM Judge
    python evaluation_methods.py --method rubric   # 仅演示 Rubric 评分
    python evaluation_methods.py --method pairwise # 仅演示成对比较
    python evaluation_methods.py --method all      # 演示所有方法
    python evaluation_methods.py --benchmark       # 运行内置 benchmark
    python evaluation_methods.py --export-metrics  # 导出评估指标定义
"""

import json
import re
import argparse
import sys
from dataclasses import dataclass, field
from typing import Any, Callable
from enum import Enum

# Fix Windows GBK encoding issues
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# 评估结果等级定义
# ============================================================

class Grade(Enum):
    CORRECT = "CORRECT"
    INCORRECT = "INCORRECT"
    NOT_ATTEMPTED = "NOT_ATTEMPTED"
    PARTIALLY_CORRECT = "PARTIALLY_CORRECT"


@dataclass
class EvalResult:
    grade: Grade
    score: float  # 0.0 - 1.0
    reasoning: str = ""
    details: dict = field(default_factory=dict)


# ============================================================
# 方法 1: 精确匹配 (Exact Match)
# ============================================================

def exact_match(predicted: str, ground_truth: str) -> EvalResult:
    """最严格的精确匹配——大小写、空格、标点完全一致"""
    is_match = predicted.strip() == ground_truth.strip()
    return EvalResult(
        grade=Grade.CORRECT if is_match else Grade.INCORRECT,
        score=1.0 if is_match else 0.0,
        reasoning=f"精确匹配: '{predicted}' vs '{ground_truth}' → {'匹配' if is_match else '不匹配'}",
    )


# ============================================================
# 方法 2: Quasi-Exact Match (GAIA 风格)
# ============================================================

def normalize_answer(s: str) -> str:
    """GAIA 风格的答案归一化"""
    s = s.lower().strip()
    # 移除引号
    s = s.replace('"', '').replace("'", '')
    # 移除末尾句号
    s = s.rstrip('.')
    # 标准化逗号分隔的数字
    s = re.sub(r'(\d),(\d)', r'\1\2', s)
    # 标准化货币符号
    s = s.replace('$', '').replace('€', '').replace('¥', '')
    # 标准化 "million"/"billion" 等
    s = s.replace('million', '000000').replace('billion', '000000000')
    # 移除多余空格
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def quasi_exact_match(predicted: str, ground_truth: str) -> EvalResult:
    """GAIA 风格的准精确匹配——归一化后比对"""
    pred_norm = normalize_answer(predicted)
    gt_norm = normalize_answer(ground_truth)
    is_match = pred_norm == gt_norm

    return EvalResult(
        grade=Grade.CORRECT if is_match else Grade.INCORRECT,
        score=1.0 if is_match else 0.0,
        reasoning=f"归一化后: '{pred_norm}' vs '{gt_norm}' → {'匹配' if is_match else '不匹配'}",
        details={"normalized_pred": pred_norm, "normalized_gt": gt_norm},
    )


# ============================================================
# 方法 3: LLM-as-Judge (模拟——实际使用时替换为真实 LLM 调用)
# ============================================================

JUDGE_PROMPT_TEMPLATE = """You are an evaluation assistant. Determine if the predicted
answer is equivalent to the labeled answer.

Question: {question}
Labeled Answer: {correct_answer}
Predicted Answer: {response}

Rules:
1. Semantic equivalence matters, not exact wording
2. Minor formatting differences should be ignored
3. If the predicted answer contains the correct information
   among other text, count it as CORRECT

Respond with ONLY "Correct" or "Incorrect"."""


def llm_judge(
    question: str,
    predicted: str,
    ground_truth: str,
    *,
    judge_fn: Callable | None = None,
) -> EvalResult:
    """
    LLM-as-Judge 评估。

    在实际使用中，`judge_fn` 应该是调用 LLM API 的函数。
    这里提供一个启发式模拟实现用于演示。
    """
    if judge_fn is not None:
        prompt = JUDGE_PROMPT_TEMPLATE.format(
            question=question,
            correct_answer=ground_truth,
            response=predicted,
        )
        result = judge_fn(prompt)
        return result

    # 启发式模拟（实际使用时替换）
    pred_norm = normalize_answer(predicted)
    gt_norm = normalize_answer(ground_truth)

    # 模拟 LLM Judge 的逻辑
    if pred_norm == gt_norm:
        return EvalResult(Grade.CORRECT, 1.0, "语义等价——归一化后匹配")
    elif gt_norm in pred_norm or pred_norm in gt_norm:
        return EvalResult(Grade.CORRECT, 1.0, "语义等价——包含关系")
    elif "cannot" in predicted.lower() or "unable" in predicted.lower():
        return EvalResult(Grade.NOT_ATTEMPTED, 0.0, "模型表示无法回答")
    else:
        return EvalResult(Grade.INCORRECT, 0.0, "语义不等价")


# ============================================================
# 方法 4: 三级评分 (FRAMES 风格)
# ============================================================

def three_level_scoring(
    question: str,
    predicted: str,
    ground_truth: str,
    *,
    judge_fn: Callable | None = None,
) -> EvalResult:
    """
    三级评分：CORRECT / INCORRECT / NOT_ATTEMPTED。
    用于 FRAMES 和 SimpleQA 等 benchmark。
    """
    # 首先检查是否未尝试
    not_attempted_markers = [
        "cannot answer", "unable to", "i don't know",
        "无法回答", "不知道", "no information",
        "not found", "未找到",
    ]
    if any(marker in predicted.lower() for marker in not_attempted_markers):
        return EvalResult(
            Grade.NOT_ATTEMPTED, 0.0,
            "模型明确表示无法回答",
        )

    # 然后进行语义等价判断
    return llm_judge(question, predicted, ground_truth, judge_fn=judge_fn)


# ============================================================
# 方法 5: 多维度 Rubric 评分 (ResearchRubrics 风格)
# ============================================================

@dataclass
class RubricDimension:
    name: str
    description: str
    weight: float
    score_range: tuple[int, int]  # (min, max)


RESEARCH_RUBRICS_DIMENSIONS = [
    RubricDimension("factual_grounding", "事实是否被来源支持", 0.30, (1, 5)),
    RubricDimension("comprehensiveness", "是否全面覆盖主题", 0.25, (1, 5)),
    RubricDimension("reasoning_validity", "推理逻辑是否严谨", 0.20, (1, 5)),
    RubricDimension("clarity", "表达是否清晰", 0.10, (1, 5)),
    RubricDimension("citation_quality", "引用是否正确和充分", 0.10, (1, 5)),
    RubricDimension("structural_coherence", "结构是否连贯", 0.05, (1, 5)),
]


def rubric_scoring(
    report: str,
    dimensions: list[RubricDimension] | None = None,
    *,
    judge_fn: Callable | None = None,
) -> dict[str, Any]:
    """
    多维度 Rubric 评分。

    返回每个维度的得分和加权总分。
    实际使用时，每个维度的评分应由 LLM 完成。
    """
    dims = dimensions or RESEARCH_RUBRICS_DIMENSIONS

    results = {}
    weighted_sum = 0.0
    total_weight = sum(d.weight for d in dims)

    for dim in dims:
        # 模拟评分（实际使用时调用 LLM）
        # 这里基于报告长度的简单启发式——仅用于演示
        score = min(5, max(1, len(report.split()) // 50))
        weighted_sum += score * dim.weight
        results[dim.name] = {
            "score": score,
            "weight": dim.weight,
            "weighted": score * dim.weight,
            "description": dim.description,
        }

    final_score = weighted_sum / total_weight if total_weight > 0 else 0

    return {
        "dimensions": results,
        "weighted_total": round(weighted_sum, 2),
        "normalized_score": round(final_score / 5.0, 3),  # 归一化到 0-1
        "dimension_count": len(dims),
    }


# ============================================================
# 方法 6: 成对比较 (DeepConsult 风格)
# ============================================================

@dataclass
class PairwiseDimension:
    name: str
    description: str
    weight: float = 0.25


DEEPCONSULT_DIMENSIONS = [
    PairwiseDimension("instruction_following", "是否遵循用户所有要求"),
    PairwiseDimension("comprehensiveness", "是否全面覆盖主题"),
    PairwiseDimension("completeness", "所有子主题是否充分探索"),
    PairwiseDimension("writing_quality", "结构是否清晰、表达是否流畅"),
]


def pairwise_comparison(
    query: str,
    report_a: str,
    report_b: str,
    dimensions: list[PairwiseDimension] | None = None,
    *,
    judge_fn: Callable | None = None,
    flip_positions: bool = True,
) -> dict[str, Any]:
    """
    成对比较两个系统的输出。

    核心设计:
    1. 多维度分别比较
    2. 位置偏差缓解——翻转 A/B 顺序取平均
    """
    dims = dimensions or DEEPCONSULT_DIMENSIONS

    def compare_single(query, a, b):
        """单次比较——模拟实现"""
        results = {}
        for dim in dims:
            # 模拟：基于长度和关键词覆盖的启发式
            len_a = len(a.split())
            len_b = len(b.split())

            if len_a > len_b * 1.2:
                winner = "A"
            elif len_b > len_a * 1.2:
                winner = "B"
            else:
                winner = "TIE"

            results[dim.name] = {
                "winner": winner,
                "description": dim.description,
                "weight": dim.weight,
            }
        return results

    # 第一轮：A vs B
    results_ab = compare_single(query, report_a, report_b)

    # 第二轮：B vs A（位置偏差缓解）
    if flip_positions:
        results_ba = compare_single(query, report_b, report_a)
        # 翻转 B vs A 的结果以对齐
        flipped = {}
        for dim_name, r in results_ba.items():
            flipped[dim_name] = r.copy()
            if r["winner"] == "A":
                flipped[dim_name]["winner"] = "B"
            elif r["winner"] == "B":
                flipped[dim_name]["winner"] = "A"
            # TIE 不变

        # 合并两轮结果
        merged = {}
        for dim_name in results_ab:
            w1 = results_ab[dim_name]["winner"]
            w2 = flipped[dim_name]["winner"]

            if w1 == w2:
                merged[dim_name] = {**results_ab[dim_name], "consistent": True}
            else:
                merged[dim_name] = {
                    **results_ab[dim_name],
                    "winner": "TIE",
                    "consistent": False,
                    "round1": w1,
                    "round2": w2,
                }
        results_ab = merged

    # 总体评分
    a_wins = sum(
        1 for r in results_ab.values()
        if r["winner"] == "A"
    )
    b_wins = sum(
        1 for r in results_ab.values()
        if r["winner"] == "B"
    )
    ties = sum(
        1 for r in results_ab.values()
        if r["winner"] == "TIE"
    )

    if a_wins > b_wins:
        overall = "A is better"
    elif b_wins > a_wins:
        overall = "B is better"
    else:
        overall = "TIE"

    return {
        "overall_verdict": overall,
        "a_wins": a_wins,
        "b_wins": b_wins,
        "ties": ties,
        "dimensions": results_ab,
        "position_bias_mitigated": flip_positions,
    }


# ============================================================
# 综合评测跑分器
# ============================================================

@dataclass
class TestCase:
    """评测用例"""
    question: str
    ground_truth: str
    correct_prediction: str
    incorrect_prediction: str
    not_attempted_prediction: str
    partially_correct_prediction: str


BENCHMARK_CASES = [
    TestCase(
        question="Barack Obama has how many children?",
        ground_truth="2",
        correct_prediction="2",
        incorrect_prediction="3",
        not_attempted_prediction="I cannot answer this question",
        partially_correct_prediction="He has two daughters, Malia and Sasha",
    ),
    TestCase(
        question="What is the capital of France?",
        ground_truth="Paris",
        correct_prediction="Paris",
        incorrect_prediction="London",
        not_attempted_prediction="I don't know",
        partially_correct_prediction="The capital of France is Paris, located on the Seine River",
    ),
    TestCase(
        question="What was the price of Bitcoin on January 1, 2024?",
        ground_truth="$45,000",
        correct_prediction="$45,000",
        incorrect_prediction="$30,000",
        not_attempted_prediction="Unable to determine",
        partially_correct_prediction="approximately $45k",
    ),
    TestCase(
        question="Who won the 2023 FIFA Women's World Cup?",
        ground_truth="Spain",
        correct_prediction="Spain",
        incorrect_prediction="England",
        not_attempted_prediction="I couldn't find this information",
        partially_correct_prediction="The Spanish women's national team",
    ),
    TestCase(
        question="How many planets are in our solar system?",
        ground_truth="8",
        correct_prediction="8",
        incorrect_prediction="9",
        not_attempted_prediction="Not found in search results",
        partially_correct_prediction="There are 8 planets in the solar system: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, Neptune",
    ),
]


def run_benchmark() -> None:
    """运行内置 benchmark 比较各评估方法"""
    print(f"\n{'='*80}")
    print("评估方法 Benchmark — 比较各方法在不同场景下的表现")
    print(f"{'='*80}\n")

    methods = {
        "Exact Match": lambda pred, gt, q: exact_match(pred, gt),
        "Quasi-Exact Match": lambda pred, gt, q: quasi_exact_match(pred, gt),
        "LLM Judge (heuristic)": lambda pred, gt, q: llm_judge(q, pred, gt),
        "Three-Level Scoring": lambda pred, gt, q: three_level_scoring(q, pred, gt),
    }

    # 按预测类型汇总
    pred_types = {
        "正确预测": "correct_prediction",
        "错误预测": "incorrect_prediction",
        "未尝试": "not_attempted_prediction",
    }

    for pred_label, pred_attr in pred_types.items():
        print(f"\n── 场景: {pred_label} ──")
        print(f"| {'方法':<22} | {'平均分':<8} | {'正确数':<8} | {'不正确':<8} | {'未尝试':<8} |")
        print(f"|{'─'*22}|{'─'*8}|{'─'*8}|{'─'*8}|{'─'*8}|")

        for method_name, method_fn in methods.items():
            correct = 0
            incorrect = 0
            not_attempted = 0

            for case in BENCHMARK_CASES:
                pred = getattr(case, pred_attr)
                result = method_fn(pred, case.ground_truth, case.question)

                if result.grade == Grade.CORRECT:
                    correct += 1
                elif result.grade == Grade.NOT_ATTEMPTED:
                    not_attempted += 1
                else:
                    incorrect += 1

            total = len(BENCHMARK_CASES)
            avg = correct / total if total > 0 else 0
            print(
                f"| {method_name:<22} | {avg:.2%}   | "
                f"{correct}/{total}  | {incorrect}/{total}  | {not_attempted}/{total}  |"
            )

    # 部分正确场景
    print(f"\n── 场景: 部分正确的语义等价预测 ──")
    print(f"| {'方法':<22} | {'Q0':<6} | {'Q1':<6} | {'Q2':<6} | {'Q3':<6} | {'Q4':<6} |")
    print(f"|{'─'*22}|{'─'*6}|{'─'*6}|{'─'*6}|{'─'*6}|{'─'*6}|")

    for method_name, method_fn in methods.items():
        results = []
        for i, case in enumerate(BENCHMARK_CASES):
            result = method_fn(
                case.partially_correct_prediction,
                case.ground_truth,
                case.question,
            )
            results.append("PASS" if result.grade == Grade.CORRECT else "FAIL")
        print(f"| {method_name:<22} | {'  | '.join(results)} |")


def demo_all_methods() -> None:
    """演示所有评估方法"""
    case = BENCHMARK_CASES[0]  # 使用 Obama 问题作为示例

    print(f"\n{'='*80}")
    print("评估方法演示")
    print(f"{'='*80}")
    print(f"\n示例问题: {case.question}")
    print(f"标准答案: {case.ground_truth}")
    print(f"预测答案: {case.correct_prediction}")
    print()

    # 1. Exact Match
    print("─── 方法 1: 精确匹配 (Exact Match) ───")
    r = exact_match(case.correct_prediction, case.ground_truth)
    print(f"  结果: {r.grade.value} (score={r.score})")
    print(f"  推理: {r.reasoning}")

    # 2. Quasi-Exact Match
    print("\n─── 方法 2: Quasi-Exact Match (GAIA 风格) ───")
    r = quasi_exact_match(case.partially_correct_prediction, case.ground_truth)
    print(f"  原始预测: '{case.partially_correct_prediction}'")
    print(f"  归一化后: '{r.details['normalized_pred']}'")
    print(f"  结果: {r.grade.value} (score={r.score})")
    print(f"  推理: {r.reasoning}")

    # 3. LLM Judge
    print("\n─── 方法 3: LLM-as-Judge ───")
    r = llm_judge(case.question, case.correct_prediction, case.ground_truth)
    print(f"  Prompt (截取): {JUDGE_PROMPT_TEMPLATE[:100]}...")
    print(f"  结果: {r.grade.value} (score={r.score})")
    print(f"  推理: {r.reasoning}")

    # 4. Three-Level Scoring
    print("\n─── 方法 4: 三级评分 (FRAMES 风格) ───")
    for label, pred in [
        ("正确预测", case.correct_prediction),
        ("错误预测", case.incorrect_prediction),
        ("未尝试", case.not_attempted_prediction),
    ]:
        r = three_level_scoring(case.question, pred, case.ground_truth)
        print(f"  {label}: {r.grade.value} (score={r.score}) → {r.reasoning}")

    # 5. Rubric Scoring
    print("\n─── 方法 5: 多维度 Rubric 评分 (ResearchRubrics 风格) ───")
    sample_report = (
        "Barack Obama has two children. Malia Obama was born in 1998 "
        "and Sasha Obama was born in 2001. Both are daughters of Barack "
        "and Michelle Obama. This information is verified through multiple "
        "official sources including White House archives [1], biographical "
        "records [2], and recent news reports [3]."
    )
    r = rubric_scoring(sample_report)
    print(f"  维度得分:")
    for dim_name, dim_result in r["dimensions"].items():
        print(f"    {dim_name}: {dim_result['score']}/5 (权重={dim_result['weight']})")
    print(f"  加权总分: {r['weighted_total']}")
    print(f"  归一化分数: {r['normalized_score']}")

    # 6. Pairwise
    print("\n─── 方法 6: 成对比较 (DeepConsult 风格) ───")
    report_a = "Barack Obama has two daughters."
    report_b = (
        "Barack Obama has two children, Malia (born 1998) and Sasha (born 2001). "
        "Both are daughters of Barack and Michelle Obama. Malia graduated from "
        "Harvard University and Sasha attended the University of Michigan."
    )
    r = pairwise_comparison("How many children does Obama have?", report_a, report_b)
    print(f"  总体判断: {r['overall_verdict']}")
    print(f"  A 胜: {r['a_wins']}, B 胜: {r['b_wins']}, 平: {r['ties']}")
    for dim_name, dim_result in r["dimensions"].items():
        print(f"    {dim_name}: {dim_result['winner']} wins")


def export_metrics() -> None:
    """导出评估指标定义"""
    metrics = {
        "evaluation_methods": {
            "exact_match": {
                "description": "严格精确匹配（大小写、空格、标点完全一致）",
                "use_case": "答案为固定格式的场景",
                "score_range": [0, 1],
                "python_function": "exact_match(predicted, ground_truth)",
            },
            "quasi_exact_match": {
                "description": "归一化后的近似精确匹配",
                "use_case": "答案为标准化短答案的场景（GAIA 风格）",
                "score_range": [0, 1],
                "normalization_steps": [
                    "小写化",
                    "去除引号和末尾句号",
                    "标准化千位分隔符",
                    "移除货币符号",
                    "标准化 million/billion",
                    "压缩多余空格",
                ],
                "python_function": "quasi_exact_match(predicted, ground_truth)",
            },
            "llm_judge": {
                "description": "使用 LLM 判断语义等价",
                "use_case": "开放性答案、长文本评估",
                "score_range": {"Correct": 1.0, "Incorrect": 0.0},
                "prompt_template": JUDGE_PROMPT_TEMPLATE,
                "python_function": "llm_judge(question, predicted, ground_truth, judge_fn=...)",
            },
            "three_level": {
                "description": "三级评分 (CORRECT/INCORRECT/NOT_ATTEMPTED)",
                "use_case": "需要区分错误和未尝试的场景（FRAMES 风格）",
                "grades": [
                    {"CORRECT": "语义等价"},
                    {"INCORRECT": "语义不等价"},
                    {"NOT_ATTEMPTED": "模型无法回答"},
                ],
                "python_function": "three_level_scoring(question, predicted, ground_truth)",
            },
            "rubric": {
                "description": "多维度标准评分",
                "use_case": "长篇研究报告评估（ResearchRubrics 风格）",
                "dimensions": [
                    {"name": d.name, "weight": d.weight, "description": d.description}
                    for d in RESEARCH_RUBRICS_DIMENSIONS
                ],
                "python_function": "rubric_scoring(report, dimensions=...)",
            },
            "pairwise": {
                "description": "成对比较两个系统的输出",
                "use_case": "两系统对比评估（DeepConsult 风格）",
                "features": ["位置偏差缓解", "多维度分别比较", "支持 ELO 锦标赛"],
                "python_function": "pairwise_comparison(query, report_a, report_b)",
            },
        }
    }

    print(json.dumps(metrics, ensure_ascii=False, indent=2))


# ============================================================
# 主入口
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="Deep Research 评估方法演示与对比工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                     # 默认演示所有方法
  %(prog)s --method em         # 仅演示精确匹配
  %(prog)s --method llm_judge  # 仅演示 LLM Judge
  %(prog)s --method rubric     # 仅演示 Rubric 评分
  %(prog)s --method pairwise   # 仅演示成对比较
  %(prog)s --method all        # 演示所有方法
  %(prog)s --benchmark         # 运行 benchmark 比较
  %(prog)s --export-metrics    # 导出评估指标定义 (JSON)
        """,
    )
    parser.add_argument(
        "--method", "-m",
        choices=["em", "quasi_em", "llm_judge", "three_level", "rubric", "pairwise", "all"],
        default="all",
        help="演示的评估方法 (默认: all)",
    )
    parser.add_argument(
        "--benchmark", "-b",
        action="store_true",
        help="运行内置 benchmark 比较各方法",
    )
    parser.add_argument(
        "--export-metrics",
        action="store_true",
        help="导出评估指标定义 (JSON)",
    )

    args = parser.parse_args()

    if args.export_metrics:
        export_metrics()
    elif args.benchmark:
        run_benchmark()
    else:
        demo_all_methods()


if __name__ == "__main__":
    main()
