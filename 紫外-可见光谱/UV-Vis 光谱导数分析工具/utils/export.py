from __future__ import annotations

import io
from typing import Dict, List

import pandas as pd
from plotly.graph_objs import Figure


def export_to_excel(
    data_frames: Dict[str, pd.DataFrame],
    marks: List[dict] | None = None,
) -> bytes:
    """
    将多个DataFrame和标记信息写入单个Excel文件。

    data_frames: {sheet_name: df}
    marks: [{'wavelength': float, 'y': float, 'note': str, 'source': str}, ...]
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        
        # 创建品牌信息封面页
        info_sheet = workbook.add_worksheet("分析信息")
        
        # 定义格式
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'font_color': '#1e3a8a',
            'align': 'left',
            'valign': 'vcenter'
        })
        
        header_format = workbook.add_format({
            'bold': True,
            'font_size': 12,
            'font_color': '#1e3a8a',
            'bg_color': '#f8fafc',
            'align': 'left'
        })
        
        content_format = workbook.add_format({
            'font_size': 11,
            'align': 'left',
            'valign': 'top',
            'text_wrap': True
        })
        
        # 写入品牌信息
        info_sheet.set_column('A:A', 20)
        info_sheet.set_column('B:B', 60)
        
        row = 0
        info_sheet.write(row, 0, "UV-Vis 光谱导数分析报告", title_format)
        row += 2
        
        info_sheet.write(row, 0, "检测机构：", header_format)
        info_sheet.write(row, 1, "新疆中和鉴珠宝玉石质量检测研究所", content_format)
        row += 1
        
        info_sheet.write(row, 0, "机构英文名：", header_format)
        info_sheet.write(row, 1, "Xin Jiang Zhong He Jian Jewelry Testing Institute", content_format)
        row += 2
        
        info_sheet.write(row, 0, "分析工具：", header_format)
        info_sheet.write(row, 1, "UV-Vis 光谱导数分析工具 v1.0", content_format)
        row += 2
        
        info_sheet.write(row, 0, "数据说明：", header_format)
        row += 1
        info_sheet.write(row, 1, "本文件包含紫外-可见光谱的原始数据、预处理数据、导数数据及标记信息。", content_format)
        row += 1
        info_sheet.write(row, 1, "各工作表说明：", content_format)
        row += 1
        info_sheet.write(row, 1, "• raw - 原始光谱数据", content_format)
        row += 1
        info_sheet.write(row, 1, "• preprocessed - 平滑和基线校正后的数据", content_format)
        row += 1
        info_sheet.write(row, 1, "• with_derivatives - 包含一阶、二阶导数的完整数据", content_format)
        row += 1
        info_sheet.write(row, 1, "• marks - 标记点信息（峰值、谷值等特征点）", content_format)
        
        # 写入数据表
        for name, df in data_frames.items():
            safe_name = name[:31] or "Sheet"
            df.to_excel(writer, sheet_name=safe_name, index=False)

        # 写入标记信息
        if marks:
            df_marks = pd.DataFrame(marks)
            df_marks.to_excel(writer, sheet_name="marks", index=False)

    output.seek(0)
    return output.read()


def export_figure_png(fig: Figure, width: int = 1600, height: int = 1200) -> bytes:
    """
    使用kaleido将Plotly图导出为PNG字节流。
    """
    img_bytes = fig.to_image(format="png", width=width, height=height, scale=2)
    return img_bytes


def export_figure_html(fig: Figure) -> bytes:
    """
    导出交互式HTML报告（单个图形），包含所有图层和注释，并添加机构品牌信息。
    """
    # 获取基础HTML
    html_str = fig.to_html(full_html=True, include_plotlyjs="cdn")
    
    # 添加自定义品牌页眉和页脚
    custom_header = """
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #ffffff;
        }
        .brand-header {
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            color: white;
            padding: 20px 40px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .brand-header h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 700;
        }
        .brand-header p {
            margin: 5px 0 0 0;
            font-size: 14px;
            opacity: 0.95;
        }
        .content-wrapper {
            padding: 20px 40px;
        }
        .brand-footer {
            text-align: center;
            padding: 20px;
            background-color: #f8fafc;
            color: #64748b;
            font-size: 13px;
            border-top: 1px solid #e2e8f0;
            margin-top: 30px;
        }
        .brand-footer strong {
            color: #1e3a8a;
        }
    </style>
    <div class="brand-header">
        <h1>UV-Vis 光谱导数分析报告</h1>
        <p>新疆中和鉴珠宝玉石质量检测研究所 | Xin Jiang Zhong He Jian Jewelry Testing Institute</p>
    </div>
    <div class="content-wrapper">
    """
    
    custom_footer = """
    </div>
    <div class="brand-footer">
        <p>
            <strong>新疆中和鉴珠宝玉石质量检测研究所</strong><br>
            UV-Vis 光谱导数分析工具 v1.0<br>
            本报告由专业光谱分析软件自动生成，图表支持交互式操作（缩放、平移、悬停查看数据）
        </p>
    </div>
    """
    
    # 插入自定义内容
    html_str = html_str.replace('<body>', '<body>' + custom_header)
    html_str = html_str.replace('</body>', custom_footer + '</body>')
    
    return html_str.encode("utf-8")

