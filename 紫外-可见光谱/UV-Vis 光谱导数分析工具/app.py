from typing import List, Dict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from utils.data_loader import load_spectrum_from_uploaded_file
from utils.preprocessing import preprocess_spectrum, crop_spectrum
from utils.derivative import add_derivatives_columns, detect_peaks
from utils.export import export_to_excel, export_figure_png, export_figure_html
from utils.conversion import convert_data_type
from utils.config_manager import ConfigManager, DEFAULT_CONFIG

# 和田玉皮色鉴别参考线预设（一阶导数关键峰位）
HETIANYU_REF_LINES = [
    {"wavelength": 435, "label": "针铁矿次峰", "color": "#f97316"},
    {"wavelength": 535, "label": "针铁矿主峰", "color": "#facc15"},
    {"wavelength": 575, "label": "赤铁矿峰", "color": "#dc2626"},
]

st.set_page_config(
    page_title="新疆中和鉴珠宝玉石质量检测研究所 - 光谱导数分析工具",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

def init_session_state() -> None:
    if "marks" not in st.session_state:
        st.session_state["marks"] = []
    if "pending_mark" not in st.session_state:
        st.session_state["pending_mark"] = {"x": 0.0, "y": 0.0}
    if "reference_lines" not in st.session_state:
        st.session_state["reference_lines"] = []
    if "data_conversion" not in st.session_state:
        st.session_state["data_conversion"] = None  # 存储转换类型 (from_type, to_type)
    
    # 初始化算法参数（如果尚未存在）
    for key, val in DEFAULT_CONFIG.items():
        if key not in st.session_state:
            st.session_state[key] = val


def build_figure(df: pd.DataFrame, marks: List[Dict], show_baseline: bool = False, ylabel: str = "强度") -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=2,
        shared_xaxes=True,
        subplot_titles=["原始谱", "预处理谱", "一阶导数", "二阶导数"],
    )

    # 确保数据是numpy数组或列表，避免pandas Series问题
    wl = df["wavelength"].values if hasattr(df["wavelength"], 'values') else df["wavelength"]
    intensity = df["intensity"].values if hasattr(df["intensity"], 'values') else df["intensity"]
    smooth = df["smooth"].values if hasattr(df["smooth"], 'values') else df["smooth"]
    corrected = df["corrected"].values if hasattr(df["corrected"], 'values') else df["corrected"]
    d1 = df["corrected_1st"].values if hasattr(df["corrected_1st"], 'values') else df["corrected_1st"]
    d2 = df["corrected_2nd"].values if hasattr(df["corrected_2nd"], 'values') else df["corrected_2nd"]

    # Row1 Col1: 原始
    fig.add_trace(
        go.Scatter(x=wl, y=intensity, mode="lines", name="原始", line=dict(color="#e5e7eb", width=2)),
        row=1,
        col=1,
    )

    # Row1 Col2: 预处理（平滑 + 校正）
    fig.add_trace(
        go.Scatter(x=wl, y=smooth, mode="lines", name="平滑", line=dict(color="#3b82f6", width=2)),
        row=1,
        col=2,
    )
    if show_baseline and "baseline" in df.columns:
        baseline = df["baseline"].values if hasattr(df["baseline"], 'values') else df["baseline"]
        fig.add_trace(
            go.Scatter(x=wl, y=baseline, mode="lines", name="基线", line=dict(color="#f59e0b", width=1, dash="dash")),
            row=1,
            col=2,
        )
    fig.add_trace(
        go.Scatter(x=wl, y=corrected, mode="lines", name="基线校正后", line=dict(color="#10b981", width=2)),
        row=1,
        col=2,
    )

    # Row2 Col1: 一阶导数
    fig.add_trace(
        go.Scatter(
            x=wl,
            y=d1,
            mode="lines",
            name="一阶导数",
            line=dict(color="#16a34a", width=2),
        ),
        row=2,
        col=1,
    )

    # Row2 Col2: 二阶导数
    fig.add_trace(
        go.Scatter(
            x=wl,
            y=d2,
            mode="lines",
            name="二阶导数",
            line=dict(color="#dc2626", width=2),
        ),
        row=2,
        col=2,
    )

    # 标记点（极值和手动标记）
    if marks:
        auto_marks = [m for m in marks if m.get("note", "").startswith("auto-")]
        manual_marks = [m for m in marks if not m.get("note", "").startswith("auto-")]
        
        # 自动极值标注（按子图分组）
        if auto_marks:
            # 按 (row, col) 分组
            from collections import defaultdict
            marks_by_subplot = defaultdict(list)
            for m in auto_marks:
                marks_by_subplot[(m.get("row", 1), m.get("col", 2))].append(m)
            
            # 为每个子图添加标记
            for (row, col), subplot_marks in marks_by_subplot.items():
                peak_x = [m["wavelength"] for m in subplot_marks]
                peak_y = [m["y"] for m in subplot_marks]
                peak_text = [f"λ={m['wavelength']:.1f}" for m in subplot_marks]
                
                # 根据标记类型确定图例名称
                first_note = subplot_marks[0].get("note", "")
                if "auto-peak" in first_note:
                    legend_name = "自动峰值"
                elif "auto-valley" in first_note:
                    legend_name = "自动谷值"
                else:
                    legend_name = "自动极值"
                
                fig.add_trace(
                    go.Scatter(
                        x=peak_x,
                        y=peak_y,
                        mode="markers+text",
                        text=peak_text,
                        textposition="top center",
                        marker=dict(color="#ef4444", size=8, symbol="diamond"),
                        name=legend_name,
                        showlegend=True,
                    ),
                    row=row,
                    col=col,
                )
        
        # 手动标记（优化显示效果）
        if manual_marks:
            for m in manual_marks:
                note_text = m.get("note", "标记")
                # 如果说明太长，截断
                if len(note_text) > 20:
                    note_text = note_text[:17] + "..."
                fig.add_trace(
                    go.Scatter(
                        x=[m["wavelength"]],
                        y=[m["y"]],
                        mode="markers+text",
                        text=[note_text],
                        textposition="top center",
                        textfont=dict(size=10, color="#8b5cf6"),
                        marker=dict(
                            color="#8b5cf6", 
                            size=12, 
                            symbol="x",
                            line=dict(color="#ffffff", width=1)
                        ),
                        name="手动标记",
                        showlegend=False,
                        hovertemplate=f"<b>{note_text}</b><br>λ: {m['wavelength']:.3f} nm<br>y: {m['y']:.5f}<extra></extra>",
                    ),
                    row=m.get("row", 1),
                    col=m.get("col", 2),
                )

    fig.update_layout(
        height=900,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=20, t=80, b=50),
        hovermode="x unified",
        font=dict(family="Microsoft YaHei, Arial, sans-serif", size=12),
        plot_bgcolor="rgba(248, 250, 252, 0.5)",
    )
    
    # 添加机构水印
    fig.add_annotation(
        text="新疆中和鉴珠宝玉石质量检测研究所",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=24, color="rgba(30, 58, 138, 0.08)", family="Microsoft YaHei"),
        textangle=-30,
        xanchor="center",
        yanchor="middle",
    )
    fig.update_xaxes(title_text="波长 (nm)", row=2, col=1)
    fig.update_xaxes(title_text="波长 (nm)", row=2, col=2)
    fig.update_yaxes(title_text=ylabel, row=1, col=1)
    fig.update_yaxes(title_text=ylabel, row=1, col=2)
    fig.update_yaxes(title_text=f"d({ylabel}) / dλ", row=2, col=1)
    fig.update_yaxes(title_text=f"d²({ylabel}) / dλ²", row=2, col=2)
    
    # 添加参考线（所有子图）
    if "reference_lines" in st.session_state and st.session_state["reference_lines"]:
        for ref in st.session_state["reference_lines"]:
            wavelength_val = ref["wavelength"]
            label = ref.get("label", "")
            color = ref.get("color", "#6b7280")
            
            for row in [1, 2]:
                for col in [1, 2]:
                    fig.add_vline(
                        x=wavelength_val,
                        line_dash="dash",
                        line_color=color,
                        line_width=1.5,
                        opacity=0.6,
                        annotation_text=label,
                        annotation_position="top",
                        annotation_font_size=9,
                        annotation_font_color=color,
                        row=row,
                        col=col,
                    )

    return fig


def build_merged_figure(
    df: pd.DataFrame,
    marks: List[Dict],
    show_baseline: bool = False,
    normalize: bool = True,
    height: int = 700,
    ylabel: str = "强度",
) -> go.Figure:
    """构建合并视图：所有谱线显示在同一坐标系，便于对比特征位置。"""
    wl = df["wavelength"].values if hasattr(df["wavelength"], "values") else df["wavelength"]
    intensity = df["intensity"].values if hasattr(df["intensity"], "values") else df["intensity"]
    smooth = df["smooth"].values if hasattr(df["smooth"], "values") else df["smooth"]
    corrected = df["corrected"].values if hasattr(df["corrected"], "values") else df["corrected"]
    d1 = df["corrected_1st"].values if hasattr(df["corrected_1st"], "values") else df["corrected_1st"]
    d2 = df["corrected_2nd"].values if hasattr(df["corrected_2nd"], "values") else df["corrected_2nd"]

    fig = go.Figure()
    
    def normalize_array(y):
        """标准化到 [0, 1]"""
        ymin, ymax = np.min(y), np.max(y)
        if ymax - ymin < 1e-10:
            return np.zeros_like(y)
        return (y - ymin) / (ymax - ymin)
    
    if normalize:
        # 标准化显示
        fig.add_trace(go.Scatter(
            x=wl, y=normalize_array(intensity), 
            mode="lines", name="原始谱", 
            line=dict(color="#9ca3af", width=1.5, dash="dot")
        ))
        fig.add_trace(go.Scatter(
            x=wl, y=normalize_array(smooth), 
            mode="lines", name="平滑谱", 
            line=dict(color="#3b82f6", width=2)
        ))
        fig.add_trace(go.Scatter(
            x=wl, y=normalize_array(corrected), 
            mode="lines", name="校正谱", 
            line=dict(color="#10b981", width=2.5)
        ))
        fig.add_trace(go.Scatter(
            x=wl, y=normalize_array(d1), 
            mode="lines", name="一阶导数", 
            line=dict(color="#f59e0b", width=2)
        ))
        fig.add_trace(go.Scatter(
            x=wl, y=normalize_array(d2), 
            mode="lines", name="二阶导数", 
            line=dict(color="#ef4444", width=2)
        ))
        ylabel_display = "标准化强度 [0-1]"
    else:
        # 原始值显示（可能不在同一量级）
        fig.add_trace(go.Scatter(
            x=wl, y=intensity, 
            mode="lines", name="原始谱", 
            line=dict(color="#9ca3af", width=1.5)
        ))
        fig.add_trace(go.Scatter(
            x=wl, y=smooth, 
            mode="lines", name="平滑谱", 
            line=dict(color="#3b82f6", width=2)
        ))
        fig.add_trace(go.Scatter(
            x=wl, y=corrected, 
            mode="lines", name="校正谱", 
            line=dict(color="#10b981", width=2.5)
        ))
        ylabel_display = ylabel
    
    # 标记（合并视图中显示所有标记，用不同符号区分子图）
    if marks:
        manual_marks = [m for m in marks if not m.get("note", "").startswith("auto-")]
        if manual_marks:
            # 按子图分组
            subplot_symbols = {(1,1): "circle", (1,2): "square", (2,1): "diamond", (2,2): "triangle-up"}
            subplot_colors = {(1,1): "#6366f1", (1,2): "#8b5cf6", (2,1): "#ec4899", (2,2): "#f43f5e"}
            
            for m in manual_marks:
                row_col = (m.get("row", 1), m.get("col", 2))
                symbol = subplot_symbols.get(row_col, "x")
                color = subplot_colors.get(row_col, "#8b5cf6")
                note_text = m.get("note", "标记")
                if len(note_text) > 15:
                    note_text = note_text[:12] + "..."
                
                # 在合并视图中，Y值需要对应到正确的谱线
                # 这里简化处理：直接使用记录的Y值（可能不准确）
                fig.add_trace(go.Scatter(
                    x=[m["wavelength"]],
                    y=[0.9],  # 合并视图中统一显示在上方
                    mode="markers+text",
                    text=[note_text],
                    textposition="bottom center",
                    textfont=dict(size=9, color=color),
                    marker=dict(color=color, size=10, symbol=symbol),
                    name=f"标记",
                    showlegend=False,
                    hovertemplate=f"<b>{m.get('note', '')}</b><br>λ: {m['wavelength']:.3f} nm<extra></extra>",
                ))

    fig.update_layout(
        height=height,
        title="合并视图 - 所有谱线标准化对比",
        margin=dict(l=60, r=30, t=60, b=50),
        hovermode="x unified",
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="right",
            x=0.98,
            bgcolor="rgba(255,255,255,0.8)",
        ),
        font=dict(family="Microsoft YaHei, Arial, sans-serif", size=12),
        plot_bgcolor="rgba(248, 250, 252, 0.5)",
    )
    
    # 添加机构水印
    fig.add_annotation(
        text="新疆中和鉴珠宝玉石质量检测研究所",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=24, color="rgba(30, 58, 138, 0.08)", family="Microsoft YaHei"),
        textangle=-30,
        xanchor="center",
        yanchor="middle",
    )
    fig.update_xaxes(title_text="波长 (nm)")
    fig.update_yaxes(title_text=ylabel_display)
    
    # 添加参考线（合并视图）
    if "reference_lines" in st.session_state and st.session_state["reference_lines"]:
        for ref in st.session_state["reference_lines"]:
            wavelength_val = ref["wavelength"]
            label = ref.get("label", "")
            color = ref.get("color", "#6b7280")
            
            fig.add_vline(
                x=wavelength_val,
                line_dash="dash",
                line_color=color,
                line_width=2,
                opacity=0.7,
                annotation_text=label,
                annotation_position="top",
                annotation_font_size=10,
                annotation_font_color=color,
            )
    
    return fig


def build_single_subplot(
    df: pd.DataFrame,
    subplot_key: str,
    marks: List[Dict],
    show_baseline: bool = False,
    height: int = 700,
    ylabel: str = "强度",
) -> go.Figure:
    """构建单个子图（放大显示），便于标记。"""
    wl = df["wavelength"].values if hasattr(df["wavelength"], "values") else df["wavelength"]
    intensity = df["intensity"].values if hasattr(df["intensity"], "values") else df["intensity"]
    smooth = df["smooth"].values if hasattr(df["smooth"], "values") else df["smooth"]
    corrected = df["corrected"].values if hasattr(df["corrected"], "values") else df["corrected"]
    d1 = df["corrected_1st"].values if hasattr(df["corrected_1st"], "values") else df["corrected_1st"]
    d2 = df["corrected_2nd"].values if hasattr(df["corrected_2nd"], "values") else df["corrected_2nd"]

    # 只保留属于当前子图的标记（row,col 对应：原始=1,1 预处理=1,2 一阶=2,1 二阶=2,2）
    subplot_map = {"原始谱": (1, 1), "预处理谱": (1, 2), "一阶导数": (2, 1), "二阶导数": (2, 2)}
    row, col = subplot_map.get(subplot_key, (1, 2))
    subplot_marks = [m for m in marks if m.get("row") == row and m.get("col") == col]

    if subplot_key == "原始谱":
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=wl, y=intensity, mode="lines", name="原始", line=dict(color="#2563eb", width=2))
        )
        fig.update_yaxes(title_text=ylabel)
    elif subplot_key == "预处理谱":
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=wl, y=smooth, mode="lines", name="平滑", line=dict(color="#3b82f6", width=2))
        )
        fig.add_trace(
            go.Scatter(x=wl, y=corrected, mode="lines", name="基线校正后", line=dict(color="#10b981", width=2))
        )
        if show_baseline and "baseline" in df.columns:
            baseline = df["baseline"].values if hasattr(df["baseline"], "values") else df["baseline"]
            fig.add_trace(
                go.Scatter(x=wl, y=baseline, mode="lines", name="基线", line=dict(color="#f59e0b", width=1, dash="dash"))
            )
        fig.update_yaxes(title_text=ylabel)
    elif subplot_key == "一阶导数":
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=wl, y=d1, mode="lines", name="一阶导数", line=dict(color="#16a34a", width=2))
        )
        fig.update_yaxes(title_text=f"d({ylabel}) / dλ")
    else:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=wl, y=d2, mode="lines", name="二阶导数", line=dict(color="#dc2626", width=2))
        )
        fig.update_yaxes(title_text=f"d²({ylabel}) / dλ²")

    if subplot_marks:
        mark_x = [m["wavelength"] for m in subplot_marks]
        mark_y = [m["y"] for m in subplot_marks]
        mark_text = [m.get("note", "标记")[:20] + "..." if len(m.get("note", "")) > 20 else m.get("note", "标记") for m in subplot_marks]
        fig.add_trace(
            go.Scatter(
                x=mark_x,
                y=mark_y,
                mode="markers+text",
                text=mark_text,
                textposition="top center",
                textfont=dict(size=11, color="#8b5cf6"),
                marker=dict(
                    color="#8b5cf6", 
                    size=14, 
                    symbol="x",
                    line=dict(color="#ffffff", width=1.5)
                ),
                name="标记",
                showlegend=True,
                hovertemplate="<b>%{text}</b><br>λ: %{x:.3f} nm<br>y: %{y:.5f}<extra></extra>",
            )
        )

    fig.update_layout(
        height=height,
        title=subplot_key,
        margin=dict(l=60, r=30, t=50, b=50),
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        font=dict(family="Microsoft YaHei, Arial, sans-serif", size=12),
        plot_bgcolor="rgba(248, 250, 252, 0.5)",
    )
    
    # 添加机构水印
    fig.add_annotation(
        text="新疆中和鉴珠宝玉石质量检测研究所",
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=24, color="rgba(30, 58, 138, 0.08)", family="Microsoft YaHei"),
        textangle=-30,
        xanchor="center",
        yanchor="middle",
    )
    
    fig.update_xaxes(title_text="波长 (nm)")
    
    # 添加参考线（单图视图）
    if "reference_lines" in st.session_state and st.session_state["reference_lines"]:
        for ref in st.session_state["reference_lines"]:
            wavelength_val = ref["wavelength"]
            label = ref.get("label", "")
            color = ref.get("color", "#6b7280")
            
            fig.add_vline(
                x=wavelength_val,
                line_dash="dash",
                line_color=color,
                line_width=2,
                opacity=0.7,
                annotation_text=label,
                annotation_position="top",
                annotation_font_size=10,
                annotation_font_color=color,
            )
    
    return fig


def main() -> None:
    init_session_state()
    
    # 自定义CSS样式 - 品牌增强
    st.markdown("""
    <style>
    /* 侧边栏品牌强化 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
    }
    
    /* 侧边栏标题样式 */
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #1e3a8a;
        font-weight: 600;
    }
    
    /* 主标题样式优化 */
    h1 {
        color: #1e3a8a;
        font-weight: 700;
        border-bottom: 3px solid #1e3a8a;
        padding-bottom: 0.5rem;
    }
    
    /* 按钮品牌色 */
    .stButton>button {
        border-radius: 6px;
        font-weight: 500;
    }
    
    /* 信息框样式 */
    .stAlert {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

    # 品牌标识区域
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        st.image("logo.png", width=120)
    with col_title:
        st.title("UV-Vis 光谱导数分析工具")
        st.caption("新疆中和鉴珠宝玉石质量检测研究所")
    
    st.divider()

    # --- 侧边栏布局 ---
    with st.sidebar:
        st.header("设置 & 工具")
        
        with st.expander("📖 新手使用指南", expanded=False):
            st.markdown("""
            **1. 数据导入**
            - 点击下方 **Browse files** 上传 `.txt` 或 `.csv` 文件。
            - 确保文件为两列数据（波长、强度），无表头或单行表头。
            
            **2. 视图切换**
            - **四图总览**：全局把控，同时查看处理前后的所有曲线。
            - **合并视图**：将各阶段曲线标准化叠加，直观对比峰位偏移。
            - **单图放大**：**最常用的交互模式**。在此模式下，点击图表上的任意点，坐标会自动填入“📍 标记”栏。

            **3. 参数调优与预设**
            - 在下方标签页中调整平滑、基线和导数参数。
            - **保存预设**：当您调出一组完美适合当前样品的参数时，点击“💾 管理预设”将其保存。下次遇到同类样品，一键“加载”即可复现分析标准。

            **4. 结果输出**
            - 所有的标记（自动+手动）都会汇总在 Excel 表格中。
            - 可导出高清 PNG 图片用于论文或报告。
            """)
        
        uploaded = st.file_uploader("上传数据文件", type=["txt", "csv"])
        
        st.divider()
        
        # --- 参数预设管理 ---
        st.caption("参数预设")
        presets = ConfigManager.load_presets()
        preset_names = list(presets.keys())
        # 确保默认配置在第一个
        if "默认配置" in preset_names:
            preset_names.remove("默认配置")
            preset_names.insert(0, "默认配置")
        
        c_p1, c_p2 = st.columns([3, 1])
        with c_p1:
            selected_preset = st.selectbox("选择预设", preset_names, key="preset_selector", label_visibility="collapsed")
        with c_p2:
            if st.button("加载", help="应用选中的参数配置"):
                config = presets[selected_preset]
                for k, v in config.items():
                    st.session_state[k] = v
                st.toast(f"已加载预设：{selected_preset}")
                st.rerun()
        
        with st.popover("💾 保存/管理预设", use_container_width=True):
            st.markdown("##### 保存当前参数")
            new_preset_name = st.text_input("预设名称", placeholder="例如：红外光谱-高噪")
            if st.button("保存", type="primary", use_container_width=True):
                if new_preset_name:
                    # 收集当前 session_state 中的参数
                    current_config = {k: st.session_state.get(k, DEFAULT_CONFIG.get(k)) for k in ConfigManager.get_default_keys()}
                    ConfigManager.save_preset(new_preset_name, current_config)
                    st.toast(f"已保存预设：{new_preset_name}")
                    st.rerun()
                else:
                    st.error("请输入名称")
            
            st.divider()
            st.markdown("##### 删除预设")
            if selected_preset == "默认配置":
                st.caption("默认配置不可删除")
            else:
                if st.button(f"删除 '{selected_preset}'", type="primary", help="此操作不可恢复"):
                    ConfigManager.delete_preset(selected_preset)
                    st.toast(f"已删除预设：{selected_preset}")
                    st.rerun()

        st.divider()
        
        view_mode = st.radio(
            "视图模式",
            ["四图总览", "合并视图", "单图放大"],
            index=0,
            horizontal=True,
        )
        
        st.divider()

        # 使用 Tab 组织侧边栏功能
        tab_params, tab_peaks, tab_marks, tab_export = st.tabs(["⚙️ 处理", "🔍 检测", "📍 标记", "💾 导出"])

        with tab_params:
            st.subheader("预处理")
            smooth_window = st.slider("平滑窗口", 5, 51, 15, 2, key="smooth_win", help="Savitzky-Golay 滤波器窗口大小")
            smooth_poly = st.slider("多项式阶数", 2, 5, 3, 1, key="smooth_poly")
            
            st.subheader("基线校正")
            enable_baseline = st.checkbox("启用基线校正", value=False, key="baseline_enable")
            baseline_lam = st.slider("基线 λ (10^x)", 3.0, 8.0, 5.0, 0.5, key="baseline_lam", help="值越大基线越平滑")
            
            st.subheader("导数计算")
            deriv_window = st.slider("一阶导数窗口", 5, 51, 21, 2, key="deriv_win")
            deriv_window_2nd = st.slider("二阶导数窗口", 11, 101, 41, 2, key="deriv_win_2nd", help="建议设为一阶窗口的 1.5-2 倍")
            deriv_poly = st.slider("导数多项式", 2, 5, 3, 1, key="deriv_poly")

        with tab_peaks:
            enable_peak = st.checkbox("启用自动检测", value=True, key="peak_enable")
            peak_source = st.selectbox("检测数据源", ["基线校正后", "平滑谱", "原始谱"], index=0, key="peak_source")
            peak_mode = st.radio("检测模式", ["自动", "峰", "谷"], index=0, key="peak_mode", horizontal=True)
            peak_prom = st.slider("显著性阈值", 0.0, 1.0, 0.02, 0.01, key="peak_prom")
            peak_distance = st.slider("最小间距 (点)", 1, 200, 10, 1, key="peak_dist")

        with tab_marks:
            # 视图特定选项放在这里，因为标记通常在单图模式下进行
            if view_mode == "单图放大":
                st.info("单图模式下，点击图表可获取坐标")
                # 子图选择已移动到主界面图表上方
                # 这里从 session_state 获取当前值，用于后续的标记逻辑
                selected_subplot = st.session_state.get("subplot_sel", "预处理谱")
                # single_chart_height 已移动到主界面
            elif view_mode == "合并视图":
                # merged_chart_height 已移动到主界面
                pass
            else:
                st.caption("切换到“单图放大”模式以进行精确标记")

            st.divider()
            st.subheader("手动标记")
            # 标记输入区
            manual_wl = st.number_input("波长 (nm)", value=st.session_state.get("pending_mark", {}).get("x", 0.0), format="%.2f", key="mark_wl")
            manual_y = st.number_input("强度", value=st.session_state.get("pending_mark", {}).get("y", 0.0), format="%.4f", key="mark_y")
            manual_note = st.text_input("说明", value="", key="mark_note", placeholder="例如：特征峰")
            
            if st.button("➕ 添加标记", use_container_width=True, type="primary"):
                # 确定当前标记属于哪个子图
                if view_mode == "单图放大":
                    subplot_map = {"原始谱": (1, 1), "预处理谱": (1, 2), "一阶导数": (2, 1), "二阶导数": (2, 2)}
                    m_row, m_col = subplot_map.get(selected_subplot, (1, 2))
                else:
                    # 默认归到预处理谱
                    m_row, m_col = (1, 2)
                
                if manual_wl > 0:
                    st.session_state["marks"].append({
                        "wavelength": manual_wl,
                        "y": manual_y,
                        "note": manual_note or "标记",
                        "row": m_row,
                        "col": m_col,
                    })
                    # 清除待处理标记
                    st.session_state["pending_mark"] = {"x": 0.0, "y": 0.0}
                    st.rerun()

            # 标记列表管理
            current_marks = st.session_state["marks"]
            if current_marks:
                with st.expander(f"已添加 {len(current_marks)} 个标记", expanded=False):
                    for i, m in enumerate(current_marks):
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.text(f"{m['wavelength']:.1f}nm : {m.get('note','-')}")
                        with c2:
                            if st.button("×", key=f"del_m_{i}"):
                                st.session_state["marks"].pop(i)
                                st.rerun()
                    if st.button("清空所有标记", use_container_width=True):
                        st.session_state["marks"] = []
                        st.rerun()
            
            st.divider()
            st.subheader("参考线")
            if st.button("🟡 快速添加和田玉参考线", use_container_width=True, help="添加 435/535/575 nm 三条标准峰位参考线"):
                existing_wl = [ref["wavelength"] for ref in st.session_state["reference_lines"]]
                added = 0
                for ref in HETIANYU_REF_LINES:
                    wl = ref["wavelength"]
                    if not any(abs(ex - wl) < 3 for ex in existing_wl):
                        st.session_state["reference_lines"].append(ref.copy())
                        existing_wl.append(wl)
                        added += 1
                if added > 0:
                    st.toast(f"已添加 {added} 条和田玉参考线（435/535/575 nm）", icon="🟡")
                else:
                    st.toast("和田玉参考线已存在", icon="ℹ️")
                st.rerun()
            ref_wl = st.number_input("参考波长", value=0.0, format="%.1f", key="ref_wl")
            ref_label = st.text_input("标签", value="", key="ref_label")
            ref_color = st.color_picker("颜色", value="#6b7280", key="ref_color")
            if st.button("➕ 添加参考线", use_container_width=True):
                if ref_wl > 0:
                    st.session_state["reference_lines"].append({
                        "wavelength": ref_wl,
                        "label": ref_label or f"{ref_wl:.0f}",
                        "color": ref_color,
                    })
                    st.rerun()
            
            if st.session_state["reference_lines"]:
                with st.expander(f"已添加 {len(st.session_state['reference_lines'])} 条参考线", expanded=False):
                    for i, ref in enumerate(st.session_state["reference_lines"]):
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.text(f"{ref['wavelength']}nm")
                        with c2:
                            if st.button("×", key=f"del_r_{i}"):
                                st.session_state["reference_lines"].pop(i)
                                st.rerun()

        with tab_export:
            st.info("导出当前分析结果")
            # 导出按钮将在后面生成数据后渲染，这里先占位或者在最后渲染
            # 由于 Streamlit 的执行顺序，我们可以在这里定义占位符，或者将导出逻辑放在最后
            export_container = st.container()


    # --- 主区域逻辑 ---

    if "last_uploaded_file" not in st.session_state:
        st.session_state["last_uploaded_file"] = None
    if uploaded and uploaded.name != st.session_state["last_uploaded_file"]:
        st.session_state["data_conversion"] = None
        st.session_state["marks"] = []
        st.session_state["reference_lines"] = []
        st.session_state["crop_range"] = None
        st.session_state["last_uploaded_file"] = uploaded.name
    
    # 初始化变量以避免未定义错误
    # 这些变量将在下方根据 view_mode 动态更新
    single_chart_height = 700
    merged_chart_height = 700
    use_normalize = True
    selected_subplot = "预处理谱"

    baseline_p = 0.01

    if not uploaded:
        st.info("👋 欢迎使用新疆中和鉴珠宝玉石质量检测研究所专业光谱分析工具！")
        st.markdown("""
        ### 快速开始
        1. **上传数据**：在左侧点击“Browse files”上传文件。
        2. **调整参数**：在“⚙️ 处理”标签页调整平滑和导数参数。
        3. **自动检测**：在“🔍 检测”标签页开启自动峰值检测。
        4. **手动分析**：切换到“单图放大”模式，点击图表添加标记。
        5. **导出报告**：在“💾 导出”标签页下载结果。
        """)
        
        st.markdown("---")
        st.markdown("""
        **关于本工具**  
        本工具由新疆中和鉴珠宝玉石质量检测研究所开发，专注于紫外-可见光谱数据的专业分析，
        特别适用于和田玉等珠宝玉石的皮色鉴别与成分分析。
        """)
        
        return

    try:
        df_raw, intensity_desc = load_spectrum_from_uploaded_file(uploaded)
    except Exception as e:
        st.error(f"数据读取失败: {e}")
        return

    # 数据类型识别与转换
    type_map = {
        "transmittance(0-1)": "透射率(0-1)",
        "transmittance(%)": "透射率(%)",
        "absorbance": "吸光度",
        "reflectance(0-1)": "反射率(0-1)",
        "reflectance(%)": "反射率(%)",
        "kubelka_munk": "Kubelka-Munk",
        "unknown": "未知",
        "mixed": "混合",
    }
    
    # 检查是否有待应用的转换
    if st.session_state["data_conversion"]:
        from_type, to_type = st.session_state["data_conversion"]
        try:
            df_raw = convert_data_type(df_raw, from_type, to_type)
            current_type_desc = type_map.get(to_type, to_type)
            # 根据转换后的类型确定纵坐标标签
            if to_type == "absorbance":
                ylabel = "吸光度 (A)"
            elif to_type == "transmittance":
                ylabel = "透射率 (T)"
            elif to_type == "transmittance%":
                ylabel = "透射率 (%)"
            elif to_type == "kubelka_munk":
                ylabel = "Kubelka-Munk F(R)"
            elif to_type == "reflectance":
                ylabel = "反射率 (R)"
            elif to_type == "reflectance%":
                ylabel = "反射率 (%)"
            else:
                ylabel = "强度"
        except Exception as e:
            st.error(f"数据转换失败: {e}")
            current_type_desc = type_map.get(intensity_desc, intensity_desc)
            ylabel = "强度"
    else:
        current_type_desc = type_map.get(intensity_desc, intensity_desc)
        # 根据原始类型确定纵坐标标签
        if intensity_desc == "absorbance":
            ylabel = "吸光度 (A)"
        elif "transmittance" in intensity_desc and "%" in intensity_desc:
            ylabel = "透射率 (%)"
        elif "transmittance" in intensity_desc:
            ylabel = "透射率 (T)"
        else:
            ylabel = "强度"
    
    st.caption(f"📂 **{uploaded.name}** | {len(df_raw)} 点 | λ {df_raw['wavelength'].min():.0f}–{df_raw['wavelength'].max():.0f} nm | 类型: {current_type_desc}")

    with st.expander("✂️ 波长范围截取", expanded=False):
        min_wl_val = float(df_raw['wavelength'].min())
        max_wl_val = float(df_raw['wavelength'].max())
        
        # 获取当前生效的截取范围（用于回填表单默认值）
        current_crop = st.session_state.get("crop_range")
        if current_crop:
            default_min, default_max = current_crop
            # 确保默认值在当前文件范围内
            default_min = max(min_wl_val, default_min)
            default_max = min(max_wl_val, default_max)
        else:
            default_min, default_max = min_wl_val, max_wl_val

        with st.form("crop_form"):
            c_crop1, c_crop2 = st.columns(2)
            with c_crop1:
                input_min = st.number_input("最小波长 (nm)", value=default_min, min_value=min_wl_val, max_value=max_wl_val, step=1.0)
            with c_crop2:
                input_max = st.number_input("最大波长 (nm)", value=default_max, min_value=min_wl_val, max_value=max_wl_val, step=1.0)
            
            submitted = st.form_submit_button("🔄 应用截取并刷新图表", use_container_width=True)
        
        if submitted:
            if input_min > input_max:
                st.error("❌ 最小波长不能大于最大波长")
            else:
                st.session_state["crop_range"] = (input_min, input_max)
                st.rerun()
        
        # 应用截取逻辑
        if st.session_state.get("crop_range"):
            c_min, c_max = st.session_state["crop_range"]
            # 仅当截取范围小于原始范围时才处理
            if c_min > min_wl_val or c_max < max_wl_val:
                st.info(f"✅ 当前显示范围: {c_min} - {c_max} nm (原始: {min_wl_val:.0f} - {max_wl_val:.0f} nm)")
                df_raw = crop_spectrum(df_raw, c_min, c_max)

    with st.expander("🔄 数据类型转换 (透射/反射/KM)", expanded=False):
        c1, c2, c3 = st.columns([2, 2, 1])
        
        type_options = [
            "transmittance", "transmittance%", "absorbance", 
            "reflectance", "reflectance%", "kubelka_munk"
        ]
        
        type_labels = {
            "transmittance": "透射率(0-1)", 
            "transmittance%": "透射率(%)", 
            "absorbance": "吸光度",
            "reflectance": "反射率(0-1)",
            "reflectance%": "反射率(%)",
            "kubelka_munk": "Kubelka-Munk"
        }

        with c1:
            current_type = st.selectbox(
                "当前类型",
                type_options,
                index=0 if "transmittance" in intensity_desc else 2,
                format_func=lambda x: type_labels.get(x, x),
                key="current_type"
            )
        with c2:
            target_type = st.selectbox(
                "转换为",
                type_options,
                index=5,  # 默认为 Kubelka-Munk
                format_func=lambda x: type_labels.get(x, x),
                key="target_type"
            )
        with c3:
            st.write("") # Spacer
            st.write("") 
            if current_type != target_type:
                if st.button("执行转换", use_container_width=True):
                    st.session_state["data_conversion"] = (current_type, target_type)
                    st.rerun()
            else:
                if st.session_state["data_conversion"]:
                    if st.button("恢复原始", use_container_width=True):
                        st.session_state["data_conversion"] = None
                        st.rerun()

    # 预处理
    try:
        df_prep = preprocess_spectrum(
            df_raw,
            smooth_window=smooth_window,
            smooth_polyorder=smooth_poly,
            enable_baseline=enable_baseline,
            baseline_lam=10**baseline_lam,
            baseline_p=baseline_p,
        )
    except Exception as e:
        st.error(f"预处理失败: {e}")
        st.exception(e)
        return

    # 导数
    try:
        df_all = add_derivatives_columns(
            df_prep,
            source_column="corrected",
            window_length=deriv_window,
            window_length_2nd=deriv_window_2nd,
            polyorder=deriv_poly,
        )
    except Exception as e:
        st.error(f"导数计算失败: {e}")
        st.exception(e)
        return
    
    if df_all.empty:
        st.error("处理后的数据为空。")
        return

    # 峰值检测
    auto_peaks: List[Dict] = []
    if enable_peak:
        wl = df_all["wavelength"].to_numpy()
        source_map = {
            "基线校正后": ("corrected", 1, 2),
            "平滑谱": ("smooth", 1, 2),
            "原始谱": ("intensity", 1, 1),
        }
        col_name, mark_row, mark_col = source_map.get(peak_source, ("corrected", 1, 2))
        sig = df_all[col_name].to_numpy()
        
        if peak_mode == "自动":
            if st.session_state["data_conversion"]:
                _, to_type = st.session_state["data_conversion"]
                resolved_mode = "peak" if to_type in ["absorbance", "kubelka_munk"] else "valley"
            else:
                resolved_mode = "peak" if intensity_desc == "absorbance" else "valley" if ("transmittance" in intensity_desc or "reflectance" in intensity_desc) else "peak"
        else:
            resolved_mode = "peak" if peak_mode == "峰" else "valley"
        
        mode_label = "峰" if resolved_mode == "peak" else "谷"
        
        # 自适应 prominence：将相对阈值转换为绝对阈值
        if peak_prom > 0:
            sig_range = np.ptp(sig)  # peak-to-peak 范围
            adjusted_prom = peak_prom * sig_range  # 相对值 → 绝对值
        else:
            adjusted_prom = None
        
        peaks_idx, props = detect_peaks(
            wl, sig, prominence=adjusted_prom, distance=peak_distance, mode=resolved_mode
        )
        
        prefix = "auto-peak" if resolved_mode == "peak" else "auto-valley"
        for idx in peaks_idx:
            auto_peaks.append({
                "wavelength": float(wl[idx]),
                "y": float(sig[idx]),
                "note": f"{prefix} {mode_label}λ={wl[idx]:.2f}",
                "row": mark_row,
                "col": mark_col,
            })

    # 合并标记
    all_marks = auto_peaks + list(st.session_state["marks"])

    # 构建图表
    try:
        fig = build_figure(df_all, all_marks, show_baseline=enable_baseline, ylabel=ylabel)
    except Exception as e:
        st.error(f"图表构建失败: {e}")
        return

    # 根据视图模式选择显示内容
    if view_mode == "单图放大":
        # 在图表上方添加子图选择器
        st.write("##### 🔍 选择当前分析的图谱")
        
        c_sel, c_h = st.columns([3, 2])
        with c_sel:
            subplot_options = ["原始谱", "预处理谱", "一阶导数", "二阶导数"]
            # 确保默认值有效
            default_idx = 1
            current_sel = st.session_state.get("subplot_sel")
            if current_sel in subplot_options:
                default_idx = subplot_options.index(current_sel)
                
            selected_subplot = st.radio(
                "选择子图", 
                subplot_options, 
                index=default_idx, 
                key="subplot_sel", 
                horizontal=True,
                label_visibility="collapsed"
            )
        with c_h:
            single_chart_height = st.slider("↕️ 图表高度/纵向拉伸", 400, 2000, 700, 50, key="single_h", label_visibility="visible")
        
        display_fig = build_single_subplot(
            df_all, selected_subplot, all_marks, show_baseline=enable_baseline, height=single_chart_height, ylabel=ylabel
        )
        chart_height = single_chart_height
    elif view_mode == "合并视图":
        st.write("##### 🛠️ 显示设置")
        c_opt, c_h = st.columns([3, 2])
        with c_opt:
            use_normalize = st.checkbox("标准化显示 (0-1)", value=True, key="norm_cb")
        with c_h:
            merged_chart_height = st.slider("↕️ 图表高度/纵向拉伸", 400, 2000, 700, 50, key="merged_h")

        display_fig = build_merged_figure(
            df_all, all_marks, show_baseline=enable_baseline, normalize=use_normalize, height=merged_chart_height, ylabel=ylabel
        )
        chart_height = merged_chart_height
    else:  # 四图总览
        # 四图总览也可以提供高度调节
        st.write("##### 🛠️ 显示设置")
        # 默认四图高度设为 900，允许调节
        overview_chart_height = st.slider("↕️ 图表高度/纵向拉伸", 600, 2400, 900, 50, key="overview_h")
        display_fig = fig
        chart_height = overview_chart_height

    # 渲染图表（使用 Streamlit 原生交互）
    # 使用 key 避免状态冲突，但保持足够的稳定性
    chart_key = f"chart_{view_mode}"
    
    event = st.plotly_chart(
        display_fig,
        use_container_width=True,
        height=chart_height,
        key=chart_key,
        on_select="rerun",
        selection_mode="points",
    )

    # 处理点击/选择事件
    if event and "selection" in event and event["selection"]["points"]:
        # 获取最后一个被选中的点（通常是用户刚点击的）
        points = event["selection"]["points"]
        if points:
            pt = points[0]
            # 提取坐标（根据不同视图可能需要适配，这里取 x 和 y）
            # Plotly 返回的 point 对象包含 x, y, curve_number, point_index 等
            x_val = pt.get("x")
            y_val = pt.get("y")
            
            if x_val is not None and y_val is not None:
                # 更新 pending_mark
                st.session_state["pending_mark"] = {
                    "x": float(x_val),
                    "y": float(y_val),
                }
                # 显式更新输入框绑定的 session_state key
                # Streamlit 的 number_input 不会自动响应 value 参数的变化，必须修改对应的 key
                st.session_state["mark_wl"] = float(x_val)
                st.session_state["mark_y"] = float(y_val)
                
                # 只有当坐标发生变化时才提示，或者总是提示但使用唯一 key
                st.toast(f"已捕获坐标: {x_val:.2f}, {y_val:.4f}，请在侧边栏'📍 标记'中添加说明并保存。", icon="📍")

        
    # --- 导出逻辑 (放在最后生成数据) ---
    with export_container:
        data_frames = {
            "raw": df_raw,
            "preprocessed": df_prep,
            "with_derivatives": df_all,
        }
        excel_bytes = export_to_excel(data_frames, marks=st.session_state["marks"])
        png_bytes = export_figure_png(display_fig)
        html_bytes = export_figure_html(display_fig)
        
        st.download_button(
            "📊 下载 Excel 数据",
            data=excel_bytes,
            file_name=uploaded.name.rsplit(".", 1)[0] + "_processed.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.download_button(
                "🖼️ 下载 PNG",
                data=png_bytes,
                file_name=uploaded.name.rsplit(".", 1)[0] + "_spectra.png",
                mime="image/png",
                use_container_width=True,
            )
        with col_d2:
            st.download_button(
                "📄 下载 HTML",
                data=html_bytes,
                file_name=uploaded.name.rsplit(".", 1)[0] + "_report.html",
                mime="text/html",
                use_container_width=True,
            )
    
    # 页脚版权信息
    st.divider()
    footer_col1, footer_col2 = st.columns([3, 1])
    with footer_col1:
        st.caption("© 2024-2026 新疆中和鉴珠宝玉石质量检测研究所 | UV-Vis 光谱导数分析工具 v1.0")
    with footer_col2:
        st.caption("Xin Jiang Zhong He Jian Jewelry Testing")

if __name__ == "__main__":
    main()

