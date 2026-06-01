from typing import Tuple

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.signal import find_peaks


def compute_derivatives(
    wavelength: np.ndarray,
    signal: np.ndarray,
    window_length: int = 15,
    window_length_2nd: int | None = None,
    polyorder: int = 3,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    使用Savitzky-Golay计算一阶和二阶导数（优化版）。

    - 自动处理降序波长，确保导数符号正确
    - 使用 interp 模式提升边界精度
    - 二阶导数可使用独立窗口（更大窗口减少噪声放大）
    - 检测波长间隔一致性
    
    参数:
    - window_length: 一阶导数窗口
    - window_length_2nd: 二阶导数窗口（默认与一阶相同，建议设为更大值）
    - polyorder: 多项式阶数
    """
    n = len(signal)
    if n < 5:
        return np.zeros_like(signal), np.zeros_like(signal)

    # 检查波长顺序并处理降序
    wl_diffs = np.diff(wavelength)
    is_descending = np.mean(wl_diffs) < 0
    
    # 如果降序，翻转数据进行处理
    if is_descending:
        wavelength_proc = wavelength[::-1]
        signal_proc = signal[::-1]
        wl_diffs = -wl_diffs[::-1]
    else:
        wavelength_proc = wavelength
        signal_proc = signal
    
    # 计算波长间隔（使用绝对值）
    delta = float(np.abs(np.mean(wl_diffs)))
    
    # 检查等间距性（可选警告）
    spacing_std = np.std(wl_diffs)
    spacing_cv = spacing_std / (delta + 1e-10)
    if spacing_cv > 0.2:
        import warnings
        warnings.warn(
            f"波长间隔不均匀（变异系数={spacing_cv:.2%}），可能影响导数精度。",
            UserWarning
        )

    # 一阶导数窗口
    window_1st = max(5, window_length)
    if window_1st % 2 == 0:
        window_1st += 1
    if window_1st > n:
        window_1st = n if n % 2 == 1 else n - 1

    # 二阶导数窗口（默认与一阶相同，但可独立设置）
    if window_length_2nd is None:
        window_2nd = window_1st
    else:
        window_2nd = max(5, window_length_2nd)
        if window_2nd % 2 == 0:
            window_2nd += 1
        if window_2nd > n:
            window_2nd = n if n % 2 == 1 else n - 1

    # 一阶导数
    poly_1st = min(polyorder, window_1st - 1)
    first = savgol_filter(
        signal_proc,
        window_length=window_1st,
        polyorder=poly_1st,
        deriv=1,
        delta=delta,
        mode="interp",  # 改用 interp 模式，边界更平滑
    )
    
    # 二阶导数（使用独立窗口）
    poly_2nd = min(polyorder, window_2nd - 1)
    second = savgol_filter(
        signal_proc,
        window_length=window_2nd,
        polyorder=poly_2nd,
        deriv=2,
        delta=delta,
        mode="interp",
    )
    
    # 如果原始是降序，恢复原始顺序并修正符号
    if is_descending:
        first = -first[::-1]  # 一阶导数需要反号
        second = second[::-1]  # 二阶导数符号不变
    
    return first, second


def add_derivatives_columns(
    df: pd.DataFrame,
    source_column: str = "corrected",
    window_length: int = 15,
    window_length_2nd: int | None = None,
    polyorder: int = 3,
) -> pd.DataFrame:
    """
    在DataFrame上添加一阶/二阶导数列：
    - source_column_1st
    - source_column_2nd
    
    参数:
    - window_length: 一阶导数窗口
    - window_length_2nd: 二阶导数窗口（默认None，推荐设为更大值如41）
    - polyorder: 多项式阶数
    """
    if "wavelength" not in df.columns or source_column not in df.columns:
        raise ValueError("DataFrame缺少必要列 'wavelength' 或指定源列。")

    wl = df["wavelength"].to_numpy()
    sig = df[source_column].to_numpy()
    d1, d2 = compute_derivatives(
        wl,
        sig,
        window_length=window_length,
        window_length_2nd=window_length_2nd,
        polyorder=polyorder,
    )
    df_out = df.copy()
    df_out[f"{source_column}_1st"] = d1
    df_out[f"{source_column}_2nd"] = d2
    return df_out


def detect_peaks(
    wavelength: np.ndarray,
    signal: np.ndarray,
    height: float | None = None,
    distance: int | None = None,
    prominence: float | None = None,
    mode: str = "peak",
) -> Tuple[np.ndarray, dict]:
    """
    使用scipy.signal.find_peaks进行极值检测（峰或谷）。

    参数:
    - wavelength: 波长数组
    - signal: 信号数组
    - height: 峰/谷的最小高度
    - distance: 相邻峰/谷之间的最小间距
    - prominence: 峰/谷的显著性
    - mode: 检测模式，"peak"（峰，局部最大值）或 "valley"（谷，局部最小值）

    返回:
    - peaks_idx: 峰/谷位置的索引数组
    - properties: find_peaks返回的属性字典
    """
    if mode == "valley":
        # 对信号取反，谷值检测等价于对反信号的峰值检测
        peaks_idx, properties = find_peaks(
            -signal,
            height=height,
            distance=distance,
            prominence=prominence,
        )
    else:  # mode == "peak" 或其他值默认为峰值检测
        peaks_idx, properties = find_peaks(
            signal,
            height=height,
            distance=distance,
            prominence=prominence,
        )
    return peaks_idx, properties

