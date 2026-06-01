import io
from typing import Tuple

import numpy as np
import pandas as pd


def _is_header_row(row) -> bool:
    """判断一行是否为表头（包含非数字字符）"""
    if len(row) < 2:
        return False
    try:
        float(row.iloc[0])
        float(row.iloc[1])
        return False  # 都是数字，不是表头
    except (ValueError, TypeError, IndexError):
        return True  # 包含非数字，是表头


def _detect_encoding_and_read(file_bytes: bytes) -> pd.DataFrame:
    """
    尝试以常见编码读取文本数据为DataFrame（优化版）。
    自动识别分隔符（逗号/制表符/分号等）和表头。
    
    优化：
    - 优先使用 chardet 检测编码（如果可用）
    - 减少不必要的重复尝试
    """
    # 尝试使用 chardet 自动检测编码
    detected_encoding = None
    try:
        import chardet
        detected = chardet.detect(file_bytes)
        if detected and detected.get('confidence', 0) > 0.7:
            detected_encoding = detected['encoding']
    except ImportError:
        pass
    
    # 编码尝试列表（如果有检测结果，优先使用）
    encodings = [detected_encoding] if detected_encoding else []
    encodings.extend(["utf-8", "utf-8-sig", "gbk", "gb2312", "ansi"])
    
    for encoding in encodings:
        if not encoding:
            continue
        try:
            text = file_bytes.decode(encoding)
            buffer = io.StringIO(text)
            df = pd.read_csv(
                buffer,
                sep=None,
                engine="python",
                header=None,
                comment="#",
                skipinitialspace=True,
            )
            # 检查第一行是否为表头
            if len(df) > 0 and _is_header_row(df.iloc[0]):
                df = df.iloc[1:].reset_index(drop=True)
            return df
        except Exception:
            continue
    
    # 最后直接让pandas在二进制上猜测
    buffer = io.BytesIO(file_bytes)
    df = pd.read_csv(
        buffer,
        sep=None,
        engine="python",
        header=None,
        comment="#",
        skipinitialspace=True,
    )
    # 检查第一行是否为表头
    if len(df) > 0 and _is_header_row(df.iloc[0]):
        df = df.iloc[1:].reset_index(drop=True)
    return df


def load_spectrum_from_uploaded_file(file) -> Tuple[pd.DataFrame, str]:
    """
    从Streamlit上传的文件对象中读取光谱数据。

    约定：
    - 前两列为 [波长, 透射率] 或 [波长, 吸光度]。
    - 自动丢弃缺失值和明显异常值（非有限数）。
    """
    file_bytes = file.read()
    df_raw = _detect_encoding_and_read(file_bytes)

    if df_raw.shape[1] < 2:
        raise ValueError("数据列数不足，至少需要两列（波长, 强度）。")

    # 只保留前两列
    df = df_raw.iloc[:, :2].copy()
    df.columns = ["wavelength", "intensity"]

    # 转换为数值类型（自动处理无法转换的值，转为NaN）
    df["wavelength"] = pd.to_numeric(df["wavelength"], errors="coerce")
    df["intensity"] = pd.to_numeric(df["intensity"], errors="coerce")

    # 清洗数据：移除无穷值和缺失值
    df = df.replace([np.inf, -np.inf], np.nan).dropna()

    # 按波长排序，并去重
    df = df.sort_values("wavelength").drop_duplicates(subset="wavelength")

    if len(df) < 5:
        raise ValueError("有效数据点过少，无法进行后续分析。")

    # 判断强度是透射率还是吸光度
    intensity_desc = "unknown"
    if df["intensity"].dtype in [np.float64, np.int64, np.float32, np.int32]:
        if (df["intensity"] >= 0).all() and (df["intensity"] <= 1.2).all():
            intensity_desc = "transmittance(0-1)"
        elif (df["intensity"] >= 0).all() and (df["intensity"] <= 120).all():
            intensity_desc = "transmittance(%)"
        elif (df["intensity"] >= 0).all():
            # 吸光度通常 > 0，可能到 3-6
            intensity_desc = "absorbance"
        else:
            intensity_desc = "mixed"

    return df, intensity_desc

