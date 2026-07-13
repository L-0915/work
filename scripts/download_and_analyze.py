#!/usr/bin/env python3
"""
Deep Research 评测数据集下载与分析工具

从 HuggingFace 镜像下载真实评测数据集, 分析:
  1. 数据结构 (列名、类型、分布)
  2. 评估方法 (根据 answer 格式/列结构推断)
  3. Prompt 模式 (提取真实 question/prompt 文本, 分析模板特征)
  4. 领域/类别分布
  5. 推理 vs 评估的数据差异

输出: analysis_results/ 目录, 包含每个数据集的 JSON 分析报告 + 汇总

用法:
    python download_and_analyze.py                    # 分析所有可用数据集
    python download_and_analyze.py --list             # 列出可用的数据集
    python download_and_analyze.py --dataset deepsearchqa  # 分析单个
    python download_and_analyze.py --export-svg       # 分析后生成 SVG 图表
"""

import json
import os
import sys
import re
import math
import argparse
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Any

# Fix Windows encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Use HF mirror for faster access in China
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# ============================================================
# 数据集注册表 (带元数据)
# ============================================================

KNOWN_DATASETS = {
    "deepsearchqa": {
        "hf_path": "google/deepsearchqa",
        "name": "DeepSearchQA",
        "year": 2026,
        "publisher": "Google DeepMind",
        "description": "弥合全面性鸿沟, 900 prompts, 17 领域, 65% 集合答案",
        "split": "eval",
        "url": "https://huggingface.co/datasets/google/deepsearchqa",
    },
    "frames": {
        "hf_path": "google/frames-benchmark",
        "name": "FRAMES",
        "year": 2024,
        "publisher": "Google DeepMind",
        "description": "事实性/检索/推理综合评测, 824 多跳问题, 需要 2-15 篇 Wikipedia",
        "split": "test",
        "url": "https://huggingface.co/datasets/google/frames-benchmark",
    },
    "draco": {
        "hf_path": "perplexity-ai/draco",
        "name": "DRACO",
        "year": 2026,
        "publisher": "Perplexity AI",
        "description": "跨领域跨国家评测, 准确性/完整性/客观性/引用质量",
        "split": "test",
        "url": "https://huggingface.co/datasets/perplexity-ai/draco",
    },
    "physcibench": {
        "hf_path": "littletreee/PhySciBench",
        "name": "PhySciBench",
        "year": 2026,
        "publisher": "Community",
        "description": "物理+化学深度研究, 200 题, 6 任务类型, 最强 baseline 仅 33.5%",
        "split": "test",
        "url": "https://huggingface.co/datasets/littletreee/PhySciBench",
    },
    "k-browsecomp": {
        "hf_path": "prometheus-eval/k-browsecomp",
        "name": "K-BrowseComp",
        "year": 2026,
        "publisher": "prometheus-eval",
        "description": "韩语网页浏览 Agent 评测, 400 题, 最强模型仍低于 50%",
        "split": "test",
        "url": "https://huggingface.co/datasets/prometheus-eval/k-browsecomp",
    },
}

# ============================================================
# 核心: 数据集分析器
# ============================================================


@dataclass
class DatasetAnalysis:
    dataset_id: str
    name: str
    year: int
    publisher: str
    url: str
    num_rows: int
    columns: list
    column_details: dict  # {col_name: {dtype, unique_count, null_count, samples}}
    answer_format: str  # "single_string" | "set" | "number" | "structured_json" | "multi_choice"
    answer_format_distribution: dict
    evaluation_method: str  # 推断的评估方式
    evaluation_evidence: str  # 推断依据
    prompt_patterns: dict  # 提取的 prompt 模式
    domain_distribution: dict
    text_stats: dict  # {avg_question_len, avg_answer_len, ...}
    sample_entries: list  # 前 3 条样本


def infer_scoring_method(columns: list, answer_samples: list, answer_format: str) -> tuple:
    """根据数据结构推断评估方式"""
    evidence = []

    if answer_format == "set":
        method = "集合匹配 (Set Matching) — 评估「答全了没有」"
        evidence.append("答案为列表/集合格式, 每条记录答案项数 > 1")
    elif answer_format == "single_string" and all(len(str(a).split()) <= 5 for a in answer_samples[:50] if a):
        method = "精确匹配 (Exact Match) — 短答案归一化比对"
        evidence.append("答案平均长度短, 适合归一化后字符串匹配")
    elif answer_format == "number":
        method = "准精确匹配 (Quasi-Exact Match)"
        evidence.append("答案为数值格式")
    elif answer_format == "structured_json":
        method = "LLM-as-Judge — 结构化评分"
        evidence.append("JSON 格式答案需要语义等价判断")
    else:
        method = "LLM-as-Judge — 语义等价判断"
        evidence.append("答案较长/开放, 需要 LLM Judge 判断语义等价")

    # 检查是否有 rubrics 列
    if "rubrics" in columns or "rubric" in columns:
        method = "Rubric 评分 — 多维标准打分"
        evidence.append("数据集包含 rubrics 评分标准列")

    # 检查引用列
    ref_cols = [c for c in columns if "link" in c.lower() or "citation" in c.lower() or "reference" in c.lower()]
    if ref_cols:
        method += " + 引用验证"
        evidence.append(f"含引用列: {ref_cols}")

    return method, "; ".join(evidence)


def extract_prompt_patterns(questions: list) -> dict:
    """从真实问题文本中提取 prompt 模式"""
    patterns = {
        "instruction_verbs": Counter(),      # 指令动词 (Find/List/Calculate/...)
        "constraint_markers": Counter(),     # 约束标记 (at least/only/within/...)
        "question_starters": Counter(),      # 开头句式
        "has_numbered_list": 0,             # 是否含编号列表
        "has_example": 0,                   # 是否含示例
        "has_tool_hint": 0,                 # 是否提示使用工具
        "multi_hop_indicators": 0,          # 多跳推理标记
        "avg_questions_per_prompt": 0.0,
    }

    instruction_words = [
        "find", "list", "identify", "determine", "calculate", "compare",
        "analyze", "describe", "explain", "name", "what", "which", "who",
        "when", "where", "how many", "how much", "search", "collect",
    ]
    constraint_words = [
        "at least", "at most", "only", "exactly", "between", "before",
        "after", "within", "more than", "less than", "excluding", "including",
        "大于", "小于", "至少", "不超过", "之间",
    ]
    multi_hop_words = [
        "among", "which", "whose", "that has", "with the", "also",
        "同时", "并且", "其中", "哪些", "哪一个",
    ]

    total_sub_q = 0
    for q in questions:
        ql = str(q).lower()

        # 指令动词
        for w in instruction_words:
            if w in ql:
                patterns["instruction_verbs"][w] += 1

        # 约束标记
        for w in constraint_words:
            if w in ql:
                patterns["constraint_markers"][w] += 1

        # 开头句式
        first_word = str(q).strip().split()[0] if str(q).strip() else ""
        patterns["question_starters"][first_word] += 1

        # 编号列表
        if re.search(r'\b[1-9][.)]\s', str(q)):
            patterns["has_numbered_list"] += 1

        # 示例
        if "e.g." in ql or "for example" in ql or "例如" in ql:
            patterns["has_example"] += 1

        # 工具提示
        if "search" in ql or "browse" in ql or "use the" in ql or "using" in ql:
            patterns["has_tool_hint"] += 1

        # 多跳
        hop_count = sum(1 for w in multi_hop_words if w in ql)
        if hop_count >= 2:
            patterns["multi_hop_indicators"] += 1

        # 子问题计数
        sub_q = len(re.findall(r'[?？]', str(q)))
        total_sub_q += max(1, sub_q)

    patterns["avg_questions_per_prompt"] = round(total_sub_q / max(1, len(questions)), 2)

    # 只保留 top-10
    patterns["instruction_verbs"] = dict(patterns["instruction_verbs"].most_common(10))
    patterns["constraint_markers"] = dict(patterns["constraint_markers"].most_common(10))
    patterns["question_starters"] = dict(patterns["question_starters"].most_common(8))

    return patterns


def analyze_dataset(ds_config: dict) -> DatasetAnalysis:
    """下载并分析单个数据集"""
    from datasets import load_dataset

    hf_path = ds_config["hf_path"]
    split = ds_config.get("split", "test")

    print(f"  下载 {hf_path} (split={split})...")
    ds = load_dataset(hf_path, split=split)

    rows = len(ds)
    columns = list(ds.column_names)
    print(f"    -> {rows} rows, {len(columns)} columns")

    # 列详情
    column_details = {}
    for col in columns:
        vals = ds[col]
        # 统计
        non_null = [v for v in vals if v is not None]
        null_count = sum(1 for v in vals if v is None)

        # 样本
        samples = [str(v)[:200] for v in non_null[:3]]

        # 类型推断
        if all(isinstance(v, (int, float)) for v in non_null[:100]):
            dtype = "numeric"
        elif all(isinstance(v, list) for v in non_null[:20] if v is not None):
            dtype = "list"
        elif all(isinstance(v, dict) for v in non_null[:20] if v is not None):
            dtype = "json"
        else:
            dtype = "string"

        column_details[col] = {
            "dtype": dtype,
            "total": len(vals),
            "null_count": null_count,
            "unique_count": len(set(str(v)[:100] for v in non_null)),
            "samples": samples,
        }

    # --- 识别 question/prompt 列和 answer 列 ---
    question_col = None
    answer_col = None
    category_col = None

    # 精确或词边界匹配列名, 防止 "problem" 误匹配 "problem_category"
    def _col_match(col_name, keywords):
        cl = col_name.lower()
        for kw in keywords:
            # 优先精确匹配
            if cl == kw:
                return True
            # 然后词边界匹配 (kw 后面跟 _ 或前面有 _)
            if f"_{kw}" in cl or f"{kw}_" in cl:
                return True
        return False

    for col in columns:
        cl = col.lower()
        if _col_match(cl, ["question", "prompt", "problem", "query", "task"]):
            if question_col is None:  # 只取第一个匹配
                question_col = col
        if _col_match(cl, ["answer", "gold", "ground", "label", "solution"]):
            if answer_col is None:
                answer_col = col
        if _col_match(cl, ["category", "domain", "field", "topic", "type"]):
            if category_col is None:
                category_col = col

    # 回退: 宽泛匹配 (子串) 仅在前两轮匹配失败时使用
    if question_col is None:
        for col in columns:
            cl = col.lower()
            if any(kw in cl for kw in ["question", "prompt", "problem", "query", "task"]):
                question_col = col
                break
    if answer_col is None:
        for col in columns:
            cl = col.lower()
            if any(kw in cl for kw in ["answer", "gold", "ground", "label"]):
                answer_col = col
                break

    # 最后回退
    if question_col is None:
        question_col = columns[0]
    if answer_col is None:
        answer_col = columns[-1]

    questions = [str(q) for q in ds[question_col]] if question_col else []
    answers = [str(a) for a in ds[answer_col]] if answer_col else []

    # --- 推断答案格式 ---
    answer_format = "single_string"
    answer_format_dist = {"single_string": 0, "set": 0, "number": 0, "structured": 0}

    for a in answers[:200]:
        a_str = str(a).strip()
        if a_str.startswith("[") or a_str.startswith("{") or "\n" in a_str:
            answer_format_dist["structured"] += 1
        elif re.match(r'^[\d.,]+$', a_str):
            answer_format_dist["number"] += 1
        elif "," in a_str or ";" in a_str or "、," in a_str:
            answer_format_dist["set"] += 1
        else:
            answer_format_dist["single_string"] += 1

    max_fmt = max(answer_format_dist, key=answer_format_dist.get)
    if answer_format_dist[max_fmt] > len(answers[:200]) * 0.3:
        answer_format = max_fmt
    else:
        answer_format = "single_string"

    # --- 检查是否有显式格式列 ---
    for col in columns:
        if "answer_type" in col.lower():
            answer_format_dist = dict(Counter(str(v) for v in ds[col] if v))

    # --- 推断评估方式 ---
    eval_method, eval_evidence = infer_scoring_method(columns, answers, answer_format)

    # --- 提取 prompt 模式 ---
    prompt_patterns = extract_prompt_patterns(questions)

    # --- 领域分布 ---
    domain_dist = {}
    if category_col:
        domain_dist = dict(Counter(str(v) for v in ds[category_col] if v))

    # --- 文本统计 ---
    q_lens = [len(q) for q in questions if q] if questions else [0]
    a_lens = [len(a) for a in answers if a] if answers else [0]
    text_stats = {
        "avg_question_chars": round(sum(q_lens) / max(1, len(q_lens)), 1),
        "avg_answer_chars": round(sum(a_lens) / max(1, len(a_lens)), 1),
        "max_question_chars": max(q_lens) if q_lens else 0,
        "min_question_chars": min(q_lens) if q_lens else 0,
        "total_chars": sum(q_lens) + sum(a_lens),
    }

    # --- 样本 ---
    sample_entries = []
    for i in range(min(3, rows)):
        entry = {}
        for col in columns:
            val = ds[col][i]
            entry[col] = str(val)[:500] if val is not None else None
        sample_entries.append(entry)

    return DatasetAnalysis(
        dataset_id=ds_config.get("hf_path", ""),
        name=ds_config["name"],
        year=ds_config["year"],
        publisher=ds_config["publisher"],
        url=ds_config["url"],
        num_rows=rows,
        columns=columns,
        column_details=column_details,
        answer_format=answer_format,
        answer_format_distribution=answer_format_dist,
        evaluation_method=eval_method,
        evaluation_evidence=eval_evidence,
        prompt_patterns=prompt_patterns,
        domain_distribution=domain_dist,
        text_stats=text_stats,
        sample_entries=sample_entries,
    )


# ============================================================
# 跨数据集对比分析
# ============================================================


def cross_dataset_analysis(analyses: list[DatasetAnalysis]) -> dict:
    """跨数据集对比"""
    comparison = {
        "total_datasets": len(analyses),
        "total_samples": sum(a.num_rows for a in analyses),
        "by_year": {},
        "by_eval_method": {},
        "answer_format_comparison": {},
        "prompt_complexity_ranking": [],
        "dataset_size_vs_complexity": [],
    }

    for a in analyses:
        comparison["by_year"][str(a.year)] = comparison["by_year"].get(str(a.year), 0) + 1
        base_method = a.evaluation_method.split("—")[0].strip()
        comparison["by_eval_method"][base_method] = comparison["by_eval_method"].get(base_method, 0) + 1
        comparison["answer_format_comparison"][a.name] = {
            "format": a.answer_format,
            "distribution": a.answer_format_distribution,
        }
        comparison["prompt_complexity_ranking"].append({
            "name": a.name,
            "avg_question_len": a.text_stats["avg_question_chars"],
            "multi_hop_rate": round(a.prompt_patterns["multi_hop_indicators"] / max(1, a.num_rows) * 100, 1),
            "avg_sub_questions": a.prompt_patterns["avg_questions_per_prompt"],
        })
        comparison["dataset_size_vs_complexity"].append({
            "name": a.name,
            "year": a.year,
            "samples": a.num_rows,
            "avg_question_len": a.text_stats["avg_question_chars"],
            "answer_format": a.answer_format,
        })

    comparison["prompt_complexity_ranking"].sort(key=lambda x: x["avg_question_len"], reverse=True)
    return comparison


# ============================================================
# SVG 生成 (基于真实数据)
# ============================================================

THEME = {
    "bg": "#ffffff", "grid": "#e8ecf1", "text": "#1a1a2e",
    "text_light": "#6b7280", "text_muted": "#9ca3af",
    "exact_match": "#10b981", "llm_judge": "#f59e0b",
    "multi_level": "#06b6d4", "rubric": "#8b5cf6",
    "2024": "#3b82f6", "2025": "#8b5cf6", "2026": "#ef4444",
}


def _esc(s): return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _svg_header(w, h):
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"
     font-family="system-ui, -apple-system, sans-serif">
<rect width="{w}" height="{h}" fill="{THEME["bg"]}"/>
'''


def _text(x, y, content, size=12, color=None, bold=False, anchor="start"):
    c = color or THEME["text"]
    fw = ' font-weight="bold"' if bold else ""
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{c}" text-anchor="{anchor}"{fw}>{_esc(content)}</text>'


def _rect(x, y, w, h, fill="", rx=4, opacity=1.0):
    f = f' fill="{fill}"' if fill else ""
    o = f' fill-opacity="{opacity}"' if opacity < 1.0 else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"{f}{o}/>'


def _line(x1, y1, x2, y2, color=None, width=1.5, dash=""):
    c = color or THEME["grid"]
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="{width}"{d}/>'


def _circle(cx, cy, r, fill, stroke="#fff"):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'


def generate_svgs(analyses: list[DatasetAnalysis], comparison: dict, output_dir: str):
    """基于真实分析数据生成 SVG 图表"""
    os.makedirs(output_dir, exist_ok=True)

    # --- Chart 1: 数据集结构对比 ---
    _svg_structure_comparison(analyses, os.path.join(output_dir, "01_dataset_structure.svg"))

    # --- Chart 2: Prompt 复杂度分布 ---
    _svg_prompt_complexity(comparison, os.path.join(output_dir, "02_prompt_complexity.svg"))

    # --- Chart 3: 评估方法推断 ---
    _svg_eval_methods(analyses, os.path.join(output_dir, "03_evaluation_methods.svg"))

    # --- Chart 4: 答案格式分布 ---
    _svg_answer_formats(analyses, os.path.join(output_dir, "04_answer_formats.svg"))

    # --- Chart 5: 数据集全景散点图 ---
    _svg_landscape(comparison, os.path.join(output_dir, "05_dataset_landscape.svg"))


def _svg_structure_comparison(analyses, path):
    """柱状图: 数据集规模 + 字段数对比"""
    W, H = 900, 500
    out = [_svg_header(W, H)]
    out.append(_text(W / 2, 30, "数据集结构对比 (真实数据)", size=18, bold=True, anchor="middle"))

    bar_w = min(120, 700 / max(1, len(analyses)) / 2)
    gap = bar_w * 3
    max_rows = max(a.num_rows for a in analyses)
    chart_t, chart_b = 60, 400
    chart_h = chart_b - chart_t

    colors = [THEME["2024"], THEME["2025"], THEME["2026"], THEME["exact_match"], THEME["llm_judge"], THEME["rubric"]]

    for i, a in enumerate(analyses):
        x = 80 + i * gap
        # 样本量柱
        h1 = (a.num_rows / max_rows) * chart_h
        color = colors[i % len(colors)]
        out.append(_rect(x, chart_b - h1, bar_w, h1, fill=color, rx=3))
        out.append(_text(x + bar_w / 2, chart_b - h1 - 5, str(a.num_rows), size=9, color=color, anchor="middle"))
        # 列数柱
        h2 = (len(a.columns) / 20) * chart_h
        out.append(_rect(x + bar_w + 3, chart_b - h2, bar_w * 0.6, h2, fill=color, rx=2, opacity=0.5))
        out.append(_text(x + bar_w / 2, chart_b + 15, _esc(a.name[:12]), size=9, anchor="middle", color=THEME["text"]))

    # 图例
    out.append(_text(80, H - 50, "柱高 = 样本量, 半透明 = 字段数/20", size=10, color=THEME["text_muted"]))
    out.append(_text(80, H - 30, f"共 {len(analyses)} 个数据集, {sum(a.num_rows for a in analyses)} 条样本", size=10, color=THEME["text_muted"]))
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"    -> {os.path.basename(path)}")


def _svg_prompt_complexity(comparison, path):
    """水平柱状图: Prompt 复杂度排名"""
    W, H = 900, 500
    out = [_svg_header(W, H)]
    out.append(_text(W / 2, 30, "Prompt 复杂度分析 (基于真实问题文本)", size=18, bold=True, anchor="middle"))

    ranking = comparison["prompt_complexity_ranking"]
    max_len = max(r["avg_question_len"] for r in ranking) if ranking else 1
    bar_y, bar_h = 60, 28
    gap = 38

    for i, r in enumerate(ranking):
        y = bar_y + i * gap
        w = (r["avg_question_len"] / max_len) * 500
        out.append(_rect(250, y, w, bar_h, fill=THEME["2026"], rx=4))
        out.append(_text(240, y + bar_h * 0.7, _esc(r["name"]), size=11, anchor="end"))
        out.append(_text(255 + w, y + bar_h * 0.7, f"{r['avg_question_len']:.0f} chars, {r['multi_hop_rate']:.0f}% multi-hop, {r['avg_sub_questions']} sub-Q", size=9, color=THEME["text_light"]))

    out.append(_text(250, H - 30, "chars = 平均问题长度, multi-hop = 多跳推理比例, sub-Q = 平均子问题数", size=10, color=THEME["text_muted"]))
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"    -> {os.path.basename(path)}")


def _svg_eval_methods(analyses, path):
    """饼图/环图: 评估方法分布"""
    W, H = 800, 500
    out = [_svg_header(W, H)]
    out.append(_text(W / 2, 30, "评估方法推断 (基于 answer 格式/列结构)", size=18, bold=True, anchor="middle"))

    # 方法统计
    method_counts = Counter()
    for a in analyses:
        base = a.evaluation_method.split("—")[0].strip()
        method_counts[base] += 1

    total = sum(method_counts.values())
    cx, cy, r = 280, 280, 150
    colors = [THEME["exact_match"], THEME["llm_judge"], THEME["multi_level"], THEME["rubric"], THEME["2026"]]
    start_angle = -math.pi / 2

    for i, (method, count) in enumerate(method_counts.most_common()):
        sweep = 2 * math.pi * count / total
        # 画扇形 (polygon 近似)
        pts = [f"{cx},{cy}"]
        for j in range(21):
            a = start_angle + sweep * j / 20
            pts.append(f"{cx + r * math.cos(a):.0f},{cy + r * math.sin(a):.0f}")
        color = colors[i % len(colors)]
        out.append(f'<polygon points="{" ".join(pts)}" fill="{color}" fill-opacity="0.7" stroke="#fff" stroke-width="2"/>')
        # 标签
        mid_angle = start_angle + sweep / 2
        lx = cx + (r + 40) * math.cos(mid_angle)
        ly = cy + (r + 40) * math.sin(mid_angle)
        out.append(_text(lx, ly, f"{method}\n({count}, {count/total*100:.0f}%)", size=10, anchor="middle", color=THEME["text"]))
        start_angle += sweep

    # 右侧详情
    y = 80
    for a in analyses:
        out.append(_text(480, y, f"{a.name} ({a.year})", size=12, bold=True))
        out.append(_text(485, y + 18, a.evaluation_method[:90], size=9, color=THEME["text_light"]))
        out.append(_text(485, y + 30, f"证据: {a.evaluation_evidence[:100]}", size=9, color=THEME["text_muted"]))
        y += 70

    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"    -> {os.path.basename(path)}")


def _svg_answer_formats(analyses, path):
    """堆叠柱状图: 答案格式分布"""
    W, H = 900, 500
    out = [_svg_header(W, H)]
    out.append(_text(W / 2, 30, "答案格式分布 (基于真实 answer 数据)", size=18, bold=True, anchor="middle"))

    fmt_types = ["single_string", "set", "number", "structured"]
    fmt_colors = {"single_string": THEME["exact_match"], "set": THEME["llm_judge"],
                   "number": THEME["2024"], "structured": THEME["rubric"]}
    bar_w, gap = 80, 120
    chart_b = 400

    for i, a in enumerate(analyses):
        x = 100 + i * gap
        cumulative = 0
        total = a.num_rows or 1
        for fmt in fmt_types:
            count = a.answer_format_distribution.get(fmt, 0)
            h = (count / total) * 250
            if h > 0:
                out.append(_rect(x, chart_b - cumulative - h, bar_w, h, fill=fmt_colors[fmt], rx=2))
                if h > 20:
                    out.append(_text(x + bar_w / 2, chart_b - cumulative - h / 2, f"{count/total*100:.0f}%", size=9, color="#fff", anchor="middle"))
            cumulative += h
        out.append(_text(x + bar_w / 2, chart_b + 15, _esc(a.name[:12]), size=9, anchor="middle"))

    # 图例
    lx = 750
    for i, fmt in enumerate(fmt_types):
        out.append(_rect(lx, 80 + i * 25, 14, 14, fill=fmt_colors[fmt], rx=2))
        labels = {"single_string": "字符串", "set": "集合", "number": "数值", "structured": "结构化"}
        out.append(_text(lx + 20, 80 + i * 25 + 11, labels.get(fmt, fmt), size=10, color=THEME["text"]))

    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"    -> {os.path.basename(path)}")


def _svg_landscape(comparison, path):
    """散点图: X=样本量(log), Y=Prompt长度, 颜色=答案格式"""
    W, H = 900, 550
    out = [_svg_header(W, H)]
    out.append(_text(W / 2, 25, "数据集全景图 (X=样本量, Y=Prompt复杂度, 颜色=答案格式)", size=16, bold=True, anchor="middle"))

    points = comparison["dataset_size_vs_complexity"]
    ml, mr, mt, mb = 80, 60, 50, 60
    pw, ph = W - ml - mr, H - mt - mb

    out.append(_rect(ml, mt, pw, ph, fill="#fafbfc", rx=4))
    # 网格
    for i in range(6):
        y = mt + ph * i / 5
        out.append(_line(ml, y, ml + pw, y, width=0.5))
        x = ml + pw * i / 5
        out.append(_line(x, mt, x, mt + ph, width=0.5))

    # 数据点
    log_min = math.log10(50)
    log_max = math.log10(max(max(p["samples"] for p in points), 2000))
    len_max = max(p["avg_question_len"] for p in points)

    fmt_colors = {"single_string": THEME["exact_match"], "set": THEME["llm_judge"],
                   "number": THEME["2024"], "structured": THEME["rubric"]}

    for p in points:
        frac_x = (math.log10(max(p["samples"], 50)) - log_min) / (log_max - log_min)
        frac_y = 1 - p["avg_question_len"] / max(1, len_max)
        cx = ml + pw * max(0, min(1, frac_x))
        cy = mt + ph * max(0, min(1, frac_y))
        color = fmt_colors.get(p["answer_format"], THEME["text"])
        r = 6 + p["year"] - 2024  # newer = bigger
        out.append(_circle(cx, cy, r, fill=color))
        out.append(_text(cx + r + 3, cy + 3, _esc(p["name"][:14]), size=8, color=THEME["text_light"]))

    out.append(_text(ml, mt + ph + 30, "样本量 (log scale)", size=10, color=THEME["text_muted"], anchor="middle"))
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"    -> {os.path.basename(path)}")


# ============================================================
# 主入口
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="Deep Research 数据集下载与分析工具")
    parser.add_argument("--list", action="store_true", help="列出所有可下载数据集")
    parser.add_argument("--dataset", "-d", type=str, help="仅分析指定数据集")
    parser.add_argument("--export-svg", action="store_true", help="分析后生成 SVG 图表")
    parser.add_argument("--output", "-o", type=str, default="analysis_results", help="输出目录")
    args = parser.parse_args()

    if args.list:
        print("可下载的数据集:")
        for k, v in KNOWN_DATASETS.items():
            print(f"  {k:<20} {v['name']:<20} {v['hf_path']}")
        return

    # 创建输出目录
    output_dir = args.output
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # 选择数据集
    if args.dataset:
        ds_keys = [args.dataset]
    else:
        ds_keys = list(KNOWN_DATASETS.keys())

    # 逐一下载分析
    analyses = []
    print(f"\n开始分析 {len(ds_keys)} 个数据集...\n")
    for key in ds_keys:
        if key not in KNOWN_DATASETS:
            print(f"  未知数据集: {key}")
            continue
        config = KNOWN_DATASETS[key]
        print(f"[{config['name']}]")
        try:
            analysis = analyze_dataset(config)
            analyses.append(analysis)
            # 保存单个分析
            fpath = os.path.join(output_dir, f"{key}_analysis.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(asdict(analysis), f, ensure_ascii=False, indent=2)
            print(f"    -> 分析结果保存至 {fpath}")
            print(f"    -> 评估方式: {analysis.evaluation_method}")
            print(f"    -> 答案格式: {analysis.answer_format}")
            print(f"    -> 字段数: {len(analysis.columns)}, 行数: {analysis.num_rows}")
            if analysis.domain_distribution:
                top_domains = sorted(analysis.domain_distribution.items(), key=lambda x: -x[1])[:5]
                print(f"    -> 领域分布: {dict(top_domains)}")
        except Exception as e:
            print(f"    -> 错误: {e}")
        print()

    if not analyses:
        print("没有成功分析的数据集")
        return

    # 跨数据集对比
    print(f"\n{'='*60}")
    print(f"跨数据集对比分析 ({len(analyses)} 个数据集)")
    print(f"{'='*60}")
    comparison = cross_dataset_analysis(analyses)

    # 打印关键发现
    print(f"\n总样本数: {comparison['total_samples']}")
    print(f"\n年份分布: {comparison['by_year']}")
    print(f"\n评估方法分布: {comparison['by_eval_method']}")
    print(f"\nPrompt 复杂度排名:")
    for r in comparison["prompt_complexity_ranking"]:
        print(f"  {r['name']}: {r['avg_question_len']:.0f} chars, {r['multi_hop_rate']:.0f}% multi-hop")

    # 保存对比结果
    comp_path = os.path.join(output_dir, "cross_dataset_comparison.json")
    with open(comp_path, "w", encoding="utf-8") as f:
        # 转换 dataclass
        clean = {
            "total_datasets": comparison["total_datasets"],
            "total_samples": comparison["total_samples"],
            "by_year": comparison["by_year"],
            "by_eval_method": comparison["by_eval_method"],
            "answer_format_comparison": comparison["answer_format_comparison"],
            "prompt_complexity_ranking": comparison["prompt_complexity_ranking"],
            "dataset_size_vs_complexity": comparison["dataset_size_vs_complexity"],
        }
        json.dump(clean, f, ensure_ascii=False, indent=2)
    print(f"\n对比结果保存至: {comp_path}")

    # 生成 SVG
    if args.export_svg:
        svg_dir = os.path.join(output_dir, "charts")
        print(f"\n生成 SVG 图表...")
        generate_svgs(analyses, comparison, svg_dir)
        print(f"SVG 图表保存至: {svg_dir}/")

    print(f"\n全部分析结果保存至: {output_dir}/")


if __name__ == "__main__":
    main()
