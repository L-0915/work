#!/usr/bin/env python3
"""
Deep Research 评测框架可视化工具 — 生成可编辑 SVG 图表

生成多种 SVG 图表:
  1. timeline        — 2024-2026 Benchmark 发布时间线
  2. landscape       — Benchmark 全景图 (样本量 x 评分方式 x 年份)
  3. methodology     — 评估方法论流程图
  4. prompt-arch     — 推理 vs 评估 Prompt 架构对比图
  5. comparison      — 多维度雷达对比图
  6. ecosystem       — 生态系统关系图
  7. all             — 全部生成

所有 SVG 纯文本输出, 可手动编辑修改配色/布局/文字。

用法:
    python benchmark_visualizer.py                          # 生成全部图表
    python benchmark_visualizer.py --type timeline          # 仅时间线
    python benchmark_visualizer.py --type landscape         # 仅全景图
    python benchmark_visualizer.py --type methodology       # 仅方法论流程
    python benchmark_visualizer.py --type prompt-arch       # 仅 Prompt 架构对比
    python benchmark_visualizer.py --type comparison        # 仅多维度对比
    python benchmark_visualizer.py --type ecosystem         # 仅生态系统
    python benchmark_visualizer.py --output ./my_charts/    # 自定义输出目录
"""

import argparse
import math
import os
import sys
from dataclasses import dataclass
from typing import Optional

# Fix Windows encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# 颜色主题 (集中定义, 方便修改)
# ============================================================

THEME = {
    "bg":             "#ffffff",
    "grid":           "#e8ecf1",
    "text":           "#1a1a2e",
    "text_light":     "#6b7280",
    "text_muted":     "#9ca3af",
    "year_2024":      "#3b82f6",  # 蓝
    "year_2025":      "#8b5cf6",  # 紫
    "year_2026":      "#ef4444",  # 红
    "exact_match":    "#10b981",  # 绿
    "llm_judge":      "#f59e0b",  # 琥珀
    "multi_level":    "#06b6d4",  # 青
    "pairwise":       "#ec4899",  # 粉
    "rubric":         "#6366f1",  # 靛蓝
    "inference":      "#2563eb",  # 蓝
    "evaluation":     "#dc2626",  # 红
    "gaia":           "#3b82f6",
    "browsecomp":     "#ef4444",
    "deepsearchqa":   "#f59e0b",
    "tool_bg":        "#f0fdf4",
    "tool_border":    "#bbf7d0",
    "section_bg":     "#f8fafc",
}


# ============================================================
# SVG 工具函数
# ============================================================


def svg_header(width: int, height: int) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"
     width="{width}" height="{height}"
     font-family="system-ui, -apple-system, sans-serif">
  <rect width="{width}" height="{height}" fill="{THEME["bg"]}"/>
'''


SVG_FOOTER = "</svg>\n"


def text(x: float, y: float, content: str, size: int = 12, color: str = "", bold: bool = False, anchor: str = "start") -> str:
    c = color or THEME["text"]
    fw = ' font-weight="bold"' if bold else ""
    return f'  <text x="{x}" y="{y}" font-size="{size}" fill="{c}" text-anchor="{anchor}"{fw}>{_escape(content)}</text>'


def rect(x: float, y: float, w: float, h: float, fill: str = "", stroke: str = "", rx: float = 4, opacity: float = 1.0) -> str:
    parts = [f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"']
    if fill:
        parts.append(f' fill="{fill}"')
    if stroke:
        parts.append(f' stroke="{stroke}" stroke-width="1.5"')
    if opacity < 1.0:
        parts.append(f' opacity="{opacity}"')
    parts.append("/>")
    return "".join(parts)


def line(x1: float, y1: float, x2: float, y2: float, color: str = "", width: float = 1.5, dash: str = "") -> str:
    c = color or THEME["grid"]
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" stroke-width="{width}"{dash_attr}/>'


def circle(cx: float, cy: float, r: float, fill: str, stroke: str = "") -> str:
    s = f' stroke="{stroke}" stroke-width="2"' if stroke else ""
    return f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{s}/>'


def rounded_rect_text(x: float, y: float, w: float, h: float, content: str, fill: str, text_color: str = "#fff", size: int = 11, bold: bool = False) -> str:
    out = []
    out.append(rect(x, y, w, h, fill=fill, rx=4))
    # 垂直居中文字
    ty = y + h / 2 + size / 3
    out.append(text(x + w / 2, ty, content, size=size, color=text_color, bold=bold, anchor="middle"))
    return "\n".join(out)


def group(transform: str = "") -> str:
    if transform:
        return f'  <g transform="{transform}">\n'
    return "  <g>\n"


GROUP_END = "  </g>\n"


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ============================================================
# 图表 1: 时间线 (Timeline)
# ============================================================

BENCHMARK_TIMELINE = [
    # (name, year, month, publisher, scoring_type, category)
    ("GAIA",           2024,  4, "Meta+HF",          "exact_match",  "foundation"),
    ("FRAMES",         2024,  9, "Google DeepMind",  "multi_level",  "foundation"),
    ("BrowseComp",     2025,  4, "OpenAI",            "llm_judge",    "browsing"),
    ("BrowseComp-ZH",  2025,  4, "HKUST",             "llm_judge",    "browsing"),
    ("DeepConsult",    2025,  5, "You.com",           "pairwise",     "report"),
    ("xbench-DS",     2025,  6, "Sequoia CN",        "llm_judge",    "browsing"),
    ("BrowseComp-Plus", 2025, 8, "Chen et al.",       "exact_match",  "browsing"),
    ("WideSearch",     2025,  8, "ByteDance Seed",    "exact_match",  "domain"),
    ("ReportBench",    2025,  8, "ByteDance",         "rubric",       "report"),
    ("FinSearchComp",  2025,  9, "ByteDance Seed",    "exact_match",  "domain"),
    ("HLE",            2025, 10, "CAIS",               "llm_judge",    "foundation"),
    ("WebWalkerQA",    2025, 11, "Alibaba",            "multi_level",  "browsing"),
    ("DeepSearchQA",   2026,  1, "Google DeepMind",   "llm_judge",    "foundation"),
    ("MM-BrowseComp",  2026,  1, "Community",          "llm_judge",    "browsing"),
    ("MMDR-Bench",     2026,  1, "AIoT-MLSys",         "rubric",       "report"),
    ("DRB2",           2026,  2, "Community",          "rubric",       "report"),
    ("DRACO",          2026,  2, "Perplexity AI",      "rubric",       "report"),
    ("PDR-Bench",      2026,  2, "OPPO (ICLR)",        "rubric",       "report"),
    ("LiveBrowseComp", 2026,  5, "Community",          "llm_judge",    "browsing"),
    ("K-BrowseComp",   2026,  6, "prometheus-eval",    "llm_judge",    "browsing"),
    ("PhySciBench",    2026,  6, "Community",          "llm_judge",    "domain"),
    ("InfoSeek",       2026,  6, "BAAI",               "exact_match",  "foundation"),
    ("KnowledgeBerg",  2026,  6, "ACL 2026",           "exact_match",  "foundation"),
]

CATEGORY_COLORS = {
    "foundation": "#3b82f6",
    "browsing":   "#ef4444",
    "report":     "#8b5cf6",
    "domain":     "#10b981",
}

SCORING_SHAPES = {
    "exact_match": "circle",
    "llm_judge":   "diamond",
    "multi_level": "triangle",
    "pairwise":    "square",
    "rubric":      "hexagon",
}


def draw_timeline(output_path: str) -> str:
    W, H = 1200, 750
    out = [svg_header(W, H)]
    out.append(text(W / 2, 35, "Deep Research Benchmark 时间线 (2024-2026)", size=20, bold=True, color=THEME["text"], anchor="middle"))

    # 年份列
    year_x = {2024: 80, 2025: 450, 2026: 820}
    year_w = 310

    for yr, x in year_x.items():
        out.append(rect(x, 55, year_w, H - 70, fill=THEME["section_bg"], rx=8))
        out.append(text(x + year_w / 2, 78, str(yr), size=28, bold=True, color=THEME[f"year_{yr}"], anchor="middle"))
        out.append(line(x + year_w / 2, 88, x + year_w / 2, H - 25, color=THEME[f"year_{yr}"], width=1, dash="6,4"))

    # 每个月的高度范围
    def y_for_month(m):
        return 105 + (m - 1) * 52

    # 按年份分组, 同月偏移
    placed = {}

    for name, yr, mo, pub, stype, cat in BENCHMARK_TIMELINE:
        base_y = y_for_month(mo)
        x = year_x[yr] + 15
        offset_key = (yr, mo)
        idx = placed.get(offset_key, 0)
        placed[offset_key] = idx + 1
        y = base_y + idx * 28

        color = CATEGORY_COLORS.get(cat, THEME["text"])

        # 节点
        out.append(circle(x + 7, y + 3, 5, fill=color))
        # 连线到中线
        out.append(line(x + 12, y + 3, x + 35, y + 3, color=color, width=1, dash="3,2"))
        # 名称
        out.append(text(x + 38, y + 7, name, size=12, bold=True, color=THEME["text"]))
        # 发布方 + 评分方式
        stype_label = {"exact_match": "EM", "llm_judge": "LLM-J", "multi_level": "ML", "pairwise": "PW", "rubric": "RB"}.get(stype, stype)
        out.append(text(x + 38, y + 21, f"{pub}  [{stype_label}]", size=9, color=THEME["text_light"]))

    # 图例
    lx, ly = 20, H - 45
    for cat, color in CATEGORY_COLORS.items():
        labels = {"foundation": "基础能力", "browsing": "浏览搜索", "report": "报告评估", "domain": "领域特化"}
        out.append(circle(lx + 5, ly + 4, 5, fill=color))
        out.append(text(lx + 15, ly + 8, labels.get(cat, cat), size=11, color=THEME["text"]))
        lx += 100

    out.append(text(W - 20, H - 30, "节点大小表示样本量, 形状表示评分方式, 颜色表示类别", size=10, color=THEME["text_muted"], anchor="end"))
    out.append(SVG_FOOTER)

    result = "\n".join(out)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return output_path


# ============================================================
# 图表 2: 全景图 (Landscape Scatter)
# ============================================================

def draw_landscape(output_path: str) -> str:
    """Benchmark 全景图: X=sample_size, Y=complexity, color=scoring_type, size=year"""
    W, H = 1000, 720
    out = [svg_header(W, H)]
    out.append(text(W / 2, 32, "Deep Research Benchmark 全景图", size=20, bold=True, anchor="middle"))

    # 坐标轴区域
    margin_l, margin_r, margin_t, margin_b = 120, 60, 70, 80
    plot_w = W - margin_l - margin_r
    plot_h = H - margin_t - margin_b

    # 背景
    out.append(rect(margin_l, margin_t, plot_w, plot_h, fill="#fafbfc", rx=4))

    # 网格线
    for i in range(11):
        y = margin_t + plot_h * i / 10
        out.append(line(margin_l, y, margin_l + plot_w, y, color=THEME["grid"], width=0.5))
    for i in range(6):
        x = margin_l + plot_w * i / 5
        out.append(line(x, margin_t, x, margin_t + plot_h, color=THEME["grid"], width=0.5))

    # 轴标签
    out.append(text(margin_l + plot_w / 2, margin_t + plot_h + 40, "样本量 (log scale)", size=12, color=THEME["text_light"], anchor="middle"))
    out.append(text(margin_l - 55, margin_t + plot_h / 2, "任务复杂度", size=12, color=THEME["text_light"], anchor="middle", bold=False))

    # Y 轴标签 (旋转)
    for i, label in enumerate(["低 (1-2步)", "中 (3-6步)", "高 (7+步/\n多工具)", "极高 (专家级)"]):
        y = margin_t + plot_h - plot_h * i / 3
        out.append(text(margin_l - 10, y + 4, label, size=9, color=THEME["text_muted"], anchor="end"))

    # X 轴标签
    x_labels = [(100, "100"), (500, "500"), (1000, "1K"), (5000, "5K"), (50000, "50K")]
    for val, label in x_labels:
        log_val = math.log10(val)
        log_min, log_max = math.log10(50), math.log10(60000)
        frac = (log_val - log_min) / (log_max - log_min)
        x = margin_l + plot_w * frac
        out.append(text(x, margin_t + plot_h + 20, label, size=9, color=THEME["text_muted"], anchor="middle"))
        out.append(line(x, margin_t + plot_h, x, margin_t + plot_h + 5, color=THEME["grid"]))

    # 数据点映射
    data_points = [
        # (name, samples, complexity_score, scoring_type, year)
        ("GAIA",        466,  2.5, "exact_match", 2024),
        ("FRAMES",      824,  3.0, "multi_level", 2024),
        ("BrowseComp",  1266, 3.8, "llm_judge",   2025),
        ("BrowseComp-ZH",289, 3.6, "llm_judge",   2025),
        ("BrowseComp+", 830,  3.2, "exact_match", 2025),
        ("xbench-DS",   100,  3.5, "llm_judge",   2025),
        ("WideSearch",  200,  2.8, "exact_match", 2025),
        ("FinSearchComp",635, 3.0, "exact_match", 2025),
        ("WebWalkerQA", 680,  3.3, "multi_level", 2025),
        ("HLE",         2158, 4.5, "llm_judge",   2025),
        ("ReportBench", 200,  3.5, "rubric",      2025),
        ("DeepConsult", 150,  3.0, "pairwise",    2025),
        ("DeepSearchQA",900, 4.0, "llm_judge",    2026),
        ("DRB2",        200,  4.3, "rubric",      2026),
        ("MM-BrowseC.", 400,  4.0, "llm_judge",   2026),
        ("LiveBrowseC.",335,  4.2, "llm_judge",   2026),
        ("K-BrowseComp",400,  3.8, "llm_judge",   2026),
        ("DRACO",       300,  4.0, "rubric",      2026),
        ("PhySciBench", 200,  4.8, "llm_judge",   2026),
        ("MMDR-Bench",  140,  4.5, "rubric",      2026),
        ("PDR-Bench",   250,  4.2, "rubric",      2026),
        ("InfoSeek",    50000,2.0, "exact_match", 2026),
        ("KnowledgeBerg",4800,3.5, "exact_match", 2026),
    ]

    log_min, log_max = math.log10(50), math.log10(60000)
    for name, samples, complexity, stype, year in data_points:
        log_s = math.log10(max(samples, 50))
        frac_x = max(0, min(1, (log_s - log_min) / (log_max - log_min)))
        frac_y = 1 - complexity / 5.0

        cx = margin_l + plot_w * frac_x
        cy = margin_t + plot_h * frac_y

        color = THEME.get(stype, THEME["text"])
        r = 5 if year == 2024 else (6 if year == 2025 else 8)

        out.append(circle(cx, cy, r, fill=color, stroke="#fff"))
        if r >= 7:
            # 标签交替放在左右, 避免溢出
            label_x = cx + r + 4 if cx < margin_l + plot_w * 0.7 else cx - r - 4
            anchor = "start" if cx < margin_l + plot_w * 0.7 else "end"
            out.append(text(label_x, cy + 4, name, size=8, color=THEME["text_light"], anchor=anchor))

    # 图例 (放在左下)
    lx, ly = margin_l, H - 50
    for i, (stype, color) in enumerate([("exact_match", THEME["exact_match"]), ("llm_judge", THEME["llm_judge"]),
                          ("multi_level", THEME["multi_level"]), ("pairwise", THEME["pairwise"]),
                          ("rubric", THEME["rubric"])]):
        labels = {"exact_match": "精确匹配", "llm_judge": "LLM Judge", "multi_level": "多级评分", "pairwise": "成对比较", "rubric": "Rubric"}
        out.append(circle(lx + 5, ly + 4, 5, fill=color))
        out.append(text(lx + 15, ly + 8, labels[stype], size=10, color=THEME["text"]))
        lx += 105

    out.append(SVG_FOOTER)

    result = "\n".join(out)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return output_path


# ============================================================
# 图表 3: 评估方法论流程图
# ============================================================

def draw_methodology(output_path: str) -> str:
    """评估方法论流程: 输入 -> 方法 -> 评分 -> 输出"""
    W, H = 1100, 850
    out = [svg_header(W, H)]
    out.append(text(W / 2, 32, "Deep Research 评估方法论全景", size=20, bold=True, anchor="middle"))

    # ---- 上半: 输入层 ----
    input_y = 60
    inputs = [
        ("问题 (Question)", 100, THEME["year_2024"]),
        ("标准答案 (Ground Truth)", 340, THEME["year_2025"]),
        ("模型输出 (Prediction)", 580, THEME["year_2026"]),
        ("引用来源 (Citations)", 820, "#10b981"),
    ]
    for label, x, color in inputs:
        out.append(rounded_rect_text(x, input_y, 180, 36, label, fill=color, size=13, bold=True))
        out.append(line(x + 90, input_y + 36, x + 90, input_y + 56, color=color, width=1.5))

    # ---- 中: 汇聚线 ----
    out.append(line(100 + 90, input_y + 56, 550, input_y + 56, color=THEME["grid"], width=1.5))
    out.append(line(820 + 90, input_y + 56, 550, input_y + 56, color=THEME["grid"], width=1.5))
    out.append(line(340 + 90, input_y + 56, 340 + 90, input_y + 76, color=THEME["grid"]))
    out.append(line(580 + 90, input_y + 56, 580 + 90, input_y + 76, color=THEME["grid"]))

    # ---- 中: 五大评估方法 ----
    methods_y = 140
    methods = [
        ("精确匹配\n(Exact Match)",  60,  THEME["exact_match"], "答案归一化\n字符串比对\n客观/可复现", ["GAIA", "BrowseComp-Plus", "InfoSeek"]),
        ("LLM-as-Judge",            240, THEME["llm_judge"],   "语义等价判断\n灵活/可扩展\nJudge 偏见风险", ["BrowseComp", "DeepSearchQA", "HLE"]),
        ("三级/多级评分\n(Multi-Level)", 420, THEME["multi_level"], "CORRECT/INCORRECT/\nNOT_ATTEMPTED\n区分错误vs未尝试", ["FRAMES", "WebWalkerQA"]),
        ("成对比较\n(Pairwise)",      600, THEME["pairwise"],   "A vs B 对比\n位置偏差缓解\nELO 锦标赛", ["DeepConsult"]),
        ("Rubric 评分",              780, THEME["rubric"],      "多维标准\n层级化评估\n诊断性反馈", ["ReportBench", "DRB2", "DRACO"]),
    ]

    for label, x, color, desc, examples in methods:
        out.append(rounded_rect_text(x, methods_y, 180, 40, label, fill=color, size=11, bold=True))
        # 描述框
        desc_lines = desc.split("\n")
        for i, dl in enumerate(desc_lines):
            out.append(text(x + 90, methods_y + 56 + i * 16, dl, size=9, color=THEME["text_light"], anchor="middle"))
        # 示例
        out.append(text(x + 90, methods_y + 56 + len(desc_lines) * 16 + 4, "适用: " + ", ".join(examples), size=8, color=THEME["text_muted"], anchor="middle"))

    # ---- 中下: 处理流程 ----
    process_y = 340
    processes = ["归一化", "语义判断", "分级判断", "对比判断", "多维打分"]
    proc_x = [150, 330, 510, 690, 870]
    for i, (px, plabel) in enumerate(zip(proc_x, processes)):
        out.append(rounded_rect_text(px, process_y, 100, 30, plabel, fill=THEME["section_bg"], text_color=THEME["text"], size=11))

    # ---- 下: 输出指标 ----
    metrics_y = 420
    metric_groups = [
        (50,  "准确率\n(Accuracy)",       THEME["exact_match"], ["ACC", "EM", "F1"]),
        (220, "全面性\n(Comprehensiveness)", THEME["llm_judge"], ["Recall@Set", "Coverage"]),
        (390, "可靠性\n(Reliability)",     THEME["multi_level"], ["NOT_ATTEMPTED%", "Hallucination%"]),
        (560, "引用质量\n(Citation Q.)",    THEME["pairwise"],   ["Citation Precision", "Source Verif."]),
        (730, "综合得分\n(Composite)",      THEME["rubric"],     ["Weighted Score", "Normalized"]),
    ]
    for x, label, color, sub_metrics in metric_groups:
        out.append(rounded_rect_text(x, metrics_y, 150, 36, label, fill=color, size=11, bold=True))
        for i, sm in enumerate(sub_metrics):
            out.append(text(x + 75, metrics_y + 52 + i * 15, sm, size=9, color=THEME["text_light"], anchor="middle"))

    # ---- 底部: 最终输出 ----
    out.append(text(W / 2, 570, "最终评测报告", size=15, bold=True, anchor="middle", color=THEME["text"]))
    out.append(text(W / 2, 595, "ACC / F1 / EM / Coverage / Citation / Composite Score / Cost Efficiency", size=10, color=THEME["text_muted"], anchor="middle"))

    # ---- 右侧: 2026 年新趋势 ----
    trend_x = 920
    out.append(rect(trend_x, 60, 160, 500, fill=THEME["section_bg"], rx=6))
    out.append(text(trend_x + 80, 82, "2026 新趋势", size=14, bold=True, anchor="middle", color=THEME["year_2026"]))
    trends = [
        "集合答案评估\n(DeepSearchQA)",
        "层级化 Rubric\n(DRB2)",
        "多模态证据链\n(MMDR-Bench)",
        "个性化对齐\n(PDR-Bench)",
        "时间窗口防污染\n(LiveBrowseComp)",
        "跨语言扩展\n(K-BrowseComp等)",
        "领域特化\n(PhySciBench)",
    ]
    for i, t in enumerate(trends):
        y = 100 + i * 62
        out.append(rounded_rect_text(trend_x + 10, y, 140, 52, t, fill="#fef2f2", text_color=THEME["year_2026"], size=10))

    out.append(SVG_FOOTER)

    result = "\n".join(out)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return output_path


# ============================================================
# 图表 4: Prompt 架构对比
# ============================================================

def draw_prompt_arch(output_path: str) -> str:
    """推理 vs 评估 Prompt 架构对比"""
    W, H = 1100, 780
    out = [svg_header(W, H)]
    out.append(text(W / 2, 30, "推理 Prompt vs 评估 Prompt 架构对比", size=20, bold=True, anchor="middle"))

    # 左右两栏
    left_x, right_x = 30, 570
    col_w = 500

    # ---- 左: 推理 Prompt ----
    out.append(rect(left_x, 50, col_w, 700, fill="#eff6ff", rx=10))
    out.append(text(left_x + col_w / 2, 75, "推理 Prompt (Inference)", size=16, bold=True, anchor="middle", color=THEME["inference"]))
    out.append(text(left_x + col_w / 2, 95, "驱动 Agent 行动: 搜索 -> 浏览 -> 提取 -> 综合 -> 回答", size=11, anchor="middle", color=THEME["text_light"]))

    inf_layers = [
        (110, "身份声明", "「Web Information Seeking Master」", "#dbeafe"),
        (170, "行为原则", "持续性 + 反复验证 + 注意细节", "#bfdbfe"),
        (230, "工具定义", 'search / visit / Python / scholar (JSON Schema)', "#93c5fd"),
        (310, "输出格式", "<think> / <tool_call> / <tool_response> / <answer>", "#60a5fa"),
        (390, "上下文管理", "摘要触发 + Token 裁剪 + 降级策略 (Stop Sequences)", "#3b82f6"),
        (470, "上下文范围", "管理 100K+ token 流式工具调用结果", "#2563eb"),
        (530, "优化方式", "遗传式 Prompt 进化 (GEPA) + RL 微调 (GRPO)", "#1d4ed8"),
        (590, "复杂度趋势", "越来越简单 (Bitter Lesson 效应)", "#1e3a5f"),
        (650, "失败模式", "上下文腐烂 / 认知窒息 / 噪声污染 / 幻觉工具调用", "#1e3a5f"),
    ]

    for y, title, detail, bg in inf_layers:
        out.append(rect(left_x + 15, y, col_w - 30, 45, fill=bg, rx=6))
        out.append(text(left_x + 30, y + 18, title, size=12, bold=True, color="#1e3a5f"))
        out.append(text(left_x + 30, y + 35, detail, size=10, color="#334155"))

    # ---- 右: 评估 Prompt ----
    out.append(rect(right_x, 50, col_w, 700, fill="#fef2f2", rx=10))
    out.append(text(right_x + col_w / 2, 75, "评估 Prompt (Evaluation)", size=16, bold=True, anchor="middle", color=THEME["evaluation"]))
    out.append(text(right_x + col_w / 2, 95, "驱动 Judge 评分: 输入 -> 标准 -> 判断 -> 输出", size=11, anchor="middle", color=THEME["text_light"]))

    eva_layers = [
        (110, "角色定义", "「You are an evaluation assistant」", "#fecaca"),
        (170, "输入结构", "question + correct_answer + prediction 三要素", "#fca5a5"),
        (230, "评分标准", "语义等价 / 完整性 / 准确性 / 置信度", "#f87171"),
        (310, "Few-shot 校准", "Obama 孩子例子等具体示例消除歧义", "#ef4444"),
        (390, "输出约束", '只输出 "Correct"/"Incorrect" 或结构化 JSON', "#dc2626"),
        (470, "评分等级", "二级 (Correct/Incorrect) / 三级 (+NOT_ATTEMPTED) / 多级", "#b91c1c"),
        (530, "优化方式", "人类专家 Rubric 校准 + ELO 锦标赛对比", "#991b1b"),
        (590, "复杂度趋势", "越来越复杂 (多轴 Rubric -> Claim-Graph -> 过程评估)", "#7f1d1d"),
        (650, "失败模式", "隐性需求遗漏 / Judge 偏见 / Reward Hacking", "#7f1d1d"),
    ]

    for y, title, detail, bg in eva_layers:
        out.append(rect(right_x + 15, y, col_w - 30, 45, fill=bg, rx=6))
        out.append(text(right_x + 30, y + 18, title, size=12, bold=True, color="#7f1d1d"))
        out.append(text(right_x + 30, y + 35, detail, size=10, color="#450a0a"))

    # 中间连接箭头
    for i in range(9):
        y = 132 + i * (700 // 9)
        out.append(line(left_x + col_w, y, right_x, y, color=THEME["grid"], width=1, dash="4,4"))

    out.append(SVG_FOOTER)

    result = "\n".join(out)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return output_path


# ============================================================
# 图表 5: 多维度雷达对比
# ============================================================

def draw_comparison(output_path: str) -> str:
    """Benchmark 多维对比: 按类别分组雷达图"""
    W, H = 1200, 800
    out = [svg_header(W, H)]
    out.append(text(W / 2, 30, "Benchmark 多维度能力雷达对比", size=20, bold=True, anchor="middle"))

    # 五大雷达: Foundation / Browsing / Report / Domain 各一个
    categories = [
        ("基础能力", 40,   ["深度推理", "多步检索", "工具使用", "知识覆盖", "综合能力"], [
            ("GAIA",       [2.5, 3.0, 3.5, 3.0, 3.0], THEME["year_2024"]),
            ("FRAMES",     [3.0, 3.5, 2.0, 3.5, 3.0], THEME["year_2024"]),
            ("HLE",        [5.0, 2.0, 2.0, 5.0, 4.0], THEME["year_2025"]),
            ("DeepSearchQA",[4.5, 4.5, 4.0, 4.0, 4.5], THEME["year_2026"]),
        ]),
        ("浏览搜索", 300,  ["搜索持久性", "多步导航", "事实核查", "策略创造性", "答案精确性"], [
            ("BrowseComp",    [4.5, 4.5, 4.0, 4.5, 3.5], THEME["browsecomp"]),
            ("BrowseComp-Plus",[3.5, 3.5, 3.5, 3.0, 4.5], THEME["exact_match"]),
            ("MM-BrowseComp", [4.5, 4.0, 4.0, 4.0, 3.5], THEME["llm_judge"]),
            ("LiveBrowseComp",[4.5, 4.5, 5.0, 4.5, 3.5], THEME["year_2026"]),
        ]),
        ("报告评估", 570,  ["结构连贯性", "引用准确性", "全面性", "分析深度", "可验证性"], [
            ("ReportBench",  [4.0, 4.5, 3.5, 3.5, 4.5], THEME["rubric"]),
            ("DRB2",         [4.5, 4.5, 4.5, 4.5, 4.0], THEME["year_2026"]),
            ("DRACO",        [4.0, 4.0, 4.5, 4.0, 4.0], THEME["year_2026"]),
            ("DeepConsult",  [3.5, 2.0, 4.0, 2.5, 3.0], THEME["pairwise"]),
        ]),
        ("领域特化", 870,  ["领域知识", "专业工具", "数据格式", "时效性", "客观性"], [
            ("FinSearchComp",[4.5, 2.5, 3.5, 4.5, 3.5], THEME["exact_match"]),
            ("PhySciBench",  [5.0, 4.0, 4.0, 3.0, 5.0], THEME["year_2026"]),
            ("KnowledgeBerg",[5.0, 2.0, 2.5, 3.0, 4.5], THEME["year_2026"]),
            ("WideSearch",   [2.5, 2.5, 2.5, 3.0, 3.5], THEME["exact_match"]),
        ]),
    ]

    for cat_name, cat_x, dims, datasets in categories:
        # 分类标题
        out.append(text(cat_x + 120, 55, cat_name, size=15, bold=True, anchor="middle", color=THEME["text"]))

        # 小雷达图区域
        cx, cy, r = cat_x + 120, 200, 85
        n = len(dims)

        # 背景网格 (同心多边形)
        for ring in [0.25, 0.5, 0.75, 1.0]:
            pts = []
            for i in range(n):
                angle = -math.pi / 2 + 2 * math.pi * i / n
                px = cx + r * ring * math.cos(angle)
                py = cy + r * ring * math.sin(angle)
                pts.append(f"{px:.0f},{py:.0f}")
            out.append(f'  <polygon points="{" ".join(pts)}" fill="none" stroke="{THEME["grid"]}" stroke-width="0.5"/>')

        # 轴线和维度标签
        for i, dim in enumerate(dims):
            angle = -math.pi / 2 + 2 * math.pi * i / n
            # 轴线端点
            ex = cx + r * 1.05 * math.cos(angle)
            ey = cy + r * 1.05 * math.sin(angle)
            out.append(line(cx, cy, ex, ey, color=THEME["grid"], width=0.5))
            # 标签 (略远于轴线)
            lx = cx + (r + 25) * math.cos(angle)
            ly = cy + (r + 25) * math.sin(angle)
            out.append(text(lx, ly, dim, size=9, color=THEME["text_light"], anchor="middle"))

        # 数据集多边形 (正确使用 cos/sin)
        for ds_name, scores, color in datasets:
            pts = []
            for i, s in enumerate(scores):
                angle = -math.pi / 2 + 2 * math.pi * i / n
                dist = r * s / 5.0
                px = cx + dist * math.cos(angle)
                py = cy + dist * math.sin(angle)
                pts.append(f"{px:.0f},{py:.0f}")
            out.append(f'  <polygon points="{" ".join(pts)}" fill="{color}" fill-opacity="0.25" stroke="{color}" stroke-width="2"/>')

        # 图例 (下方, 两列)
        for i, (ds_name, _, color) in enumerate(datasets):
            col_idx = i % 2
            row_idx = i // 2
            lx = cat_x + 5 + col_idx * 120
            ly = 340 + row_idx * 20
            out.append(rect(lx, ly, 14, 14, fill=color, rx=2))
            out.append(text(lx + 18, ly + 11, ds_name, size=9, color=THEME["text"]))

    out.append(SVG_FOOTER)

    result = "\n".join(out)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return output_path


# ============================================================
# 图表 6: 生态系统关系图
# ============================================================

def draw_ecosystem(output_path: str) -> str:
    """生态系统: Benchmarks <-> Tools <-> Models 关系"""
    W, H = 1100, 750
    out = [svg_header(W, H)]
    out.append(text(W / 2, 30, "Deep Research 评测生态系统", size=20, bold=True, anchor="middle"))

    # 三栏: Benchmarks | Tools & Frameworks | Models
    col_w = 320
    cols = [
        (30,  "Benchmarks\n(评测基准)", THEME["year_2026"]),
        (390, "Tools & Frameworks\n(工具与框架)", THEME["year_2025"]),
        (750, "Models & Agents\n(模型与 Agent)", "#10b981"),
    ]

    for cx, title, color in cols:
        out.append(rect(cx, 55, col_w, 42, fill=color, rx=6))
        out.append(text(cx + col_w / 2, 72, title, size=12, bold=True, anchor="middle", color="#fff"))

    # Benchmarks
    bm_list = [
        ("GAIA", THEME["year_2024"]), ("FRAMES", THEME["year_2024"]),
        ("BrowseComp", THEME["browsecomp"]), ("BrowseComp-Plus", THEME["exact_match"]),
        ("xbench-DS", THEME["llm_judge"]), ("HLE", THEME["llm_judge"]),
        ("DeepSearchQA", THEME["deepsearchqa"]), ("DRB2", THEME["rubric"]),
        ("DRACO", THEME["rubric"]), ("LiveBrowseComp", THEME["year_2026"]),
        ("PhySciBench", THEME["year_2026"]), ("MMDR-Bench", THEME["rubric"]),
    ]
    for i, (name, color) in enumerate(bm_list):
        x = 45 + (i % 3) * 105
        y = 110 + (i // 3) * 32
        out.append(rounded_rect_text(x, y, 90, 24, name, fill=color, size=9))

    # Tools
    tools_list = [
        ("perplexity/search_evals", "#6366f1"),
        ("LDR Benchmarks", "#8b5cf6"),
        ("OpenResearcher", "#a78bfa"),
        ("Web-Bench (HF)", "#c4b5fd"),
        ("EvalScope (ModelScope)", "#ddd6fe"),
        ("Alibaba DR eval/", "#ede9fe"),
        ("DeepConsult Pairwise", "#6366f1"),
        ("BrowseComp-Plus corpus", "#8b5cf6"),
    ]
    for i, (name, color) in enumerate(tools_list):
        x = 405 + (i % 2) * 155
        y = 110 + (i // 2) * 38
        out.append(rounded_rect_text(x, y, 140, 28, name, fill=color, size=9))

    # Models
    models_list = [
        ("Tongyi DR 30B", "#059669"),
        ("GPT-5 + Browse", "#10b981"),
        ("Kimi K2.5 Swarm", "#34d399"),
        ("Gemini DR Max", "#6ee7b7"),
        ("Claude Opus 4", "#a7f3d0"),
        ("OpenResearcher 30B", "#059669"),
        ("DeepSeek-R1", "#10b981"),
        ("Search-R1", "#34d399"),
        ("Perplexity DR", "#6ee7b7"),
    ]
    for i, (name, color) in enumerate(models_list):
        x = 765 + (i % 3) * 105
        y = 110 + (i // 3) * 32
        out.append(rounded_rect_text(x, y, 90, 24, name, fill=color, size=9))

    # 关系连线 (简化版)
    # Benchmarks -> Tools
    for i in range(4):
        out.append(line(30 + col_w, 140 + i * 60, 390, 130 + i * 60, color=THEME["grid"], width=0.8, dash="4,3"))

    # Tools -> Models
    for i in range(4):
        out.append(line(390 + col_w, 140 + i * 60, 750, 130 + i * 60, color=THEME["grid"], width=0.8, dash="4,3"))

    # 底部说明
    out.append(rect(30, 550, W - 60, 180, fill=THEME["section_bg"], rx=8))
    out.append(text(50, 575, "生态关系说明", size=14, bold=True, color=THEME["text"]))
    notes = [
        "1. Benchmarks 定义评测标准和问题集, 通过 Tools 实现对 Models 的自动化评估",
        "2. Tools 提供统一接口: 加载数据集 -> 运行 Agent -> 提取答案 -> 调用 Judge -> 计算指标",
        "3. OpenResearcher/Web-Bench 致力于统一各 benchmark 格式, 降低评测门槛",
        "4. LDR Benchmarks 是社区驱动的公开排行榜, 任何人可提交结果 (YAML PR)",
        "5. 2026 年趋势: 固定语料库 (BrowseComp-Plus) + 时间窗口 (LiveBrowseComp) + 加密数据集防污染",
        "6. DeepSearchQA 首次引入集合答案评估, 推动从「答对」到「答全」的范式转变",
    ]
    for i, note in enumerate(notes):
        out.append(text(50, 600 + i * 20, note, size=11, color=THEME["text_light"]))

    out.append(SVG_FOOTER)

    result = "\n".join(out)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result)
    return output_path


# ============================================================
# 主入口
# ============================================================

CHART_TYPES = {
    "timeline":    ("benchmark_timeline.svg",    draw_timeline,    "Benchmark 发布时间线"),
    "landscape":   ("benchmark_landscape.svg",   draw_landscape,   "Benchmark 全景散点图"),
    "methodology": ("eval_methodology.svg",      draw_methodology, "评估方法论流程图"),
    "prompt-arch": ("prompt_architecture.svg",   draw_prompt_arch, "Prompt 架构对比图"),
    "comparison":  ("radar_comparison.svg",      draw_comparison,  "多维度雷达对比图"),
    "ecosystem":   ("ecosystem_map.svg",         draw_ecosystem,   "生态系统关系图"),
}


def main():
    parser = argparse.ArgumentParser(
        description="Deep Research 评测框架 SVG 可视化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                              # 生成全部 6 张图表
  %(prog)s --type timeline              # 仅时间线
  %(prog)s --type landscape             # 仅全景图
  %(prog)s --type methodology           # 仅方法论流程
  %(prog)s --type prompt-arch           # 仅 Prompt 架构对比
  %(prog)s --type comparison            # 仅多维度对比
  %(prog)s --type ecosystem             # 仅生态系统
  %(prog)s --output ./my_svg_charts/    # 自定义输出目录
        """,
    )
    parser.add_argument("--type", "-t", choices=list(CHART_TYPES.keys()) + ["all"], default="all", help="图表类型 (默认: all)")
    parser.add_argument("--output", "-o", type=str, default="", help="输出目录 (默认: charts/)")

    args = parser.parse_args()

    output_dir = args.output or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "charts")
    os.makedirs(output_dir, exist_ok=True)

    if args.type == "all":
        types_to_draw = list(CHART_TYPES.keys())
    else:
        types_to_draw = [args.type]

    print(f"生成 SVG 图表到: {output_dir}/\n")

    for chart_type in types_to_draw:
        filename, draw_fn, description = CHART_TYPES[chart_type]
        path = os.path.join(output_dir, filename)
        draw_fn(path)
        size_kb = os.path.getsize(path) / 1024
        print(f"  [{chart_type:<14}] {filename:<30} ({size_kb:.1f} KB) — {description}")

    print(f"\n共生成 {len(types_to_draw)} 张 SVG 图表")
    print(f"所有 SVG 均为纯文本格式, 可用文本编辑器或矢量图工具 (Figma/Illustrator/Inkscape) 编辑修改")


if __name__ == "__main__":
    main()
