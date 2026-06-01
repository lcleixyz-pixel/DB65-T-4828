from typing import Tuple

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.signal import savgol_filter


def crop_spectrum(df: pd.DataFrame, min_wl: float, max_wl: float) -> pd.DataFrame:
    """
    根据波长范围截取光谱数据。
    """
    if "wavelength" not in df.columns:
        return df
    
    mask = (df["wavelength"] >= min_wl) & (df["wavelength"] <= max_wl)
    return df[mask].copy().reset_index(drop=True)


def savgol_smooth(
    wavelength: np.ndarray,
    intensity: np.ndarray,
    window_length: int = 15,
    polyorder: int = 3,
) -> np.ndarray:
    """
    Savitzky-Golay 平滑（优化版）。

    - 自动保证 window_length 为奇数且不超过数据长度。
    - 使用平均波长间隔作为 delta，以减弱非严格等间距的影响。
    - 使用 interp 模式提升边界精度。
    """
    n = len(intensity)
    if n < 5:
        return intensity.copy()

    window_length = max(5, window_length)
    if window_length % 2 == 0:
        window_length += 1
    if window_length > n:
        window_length = n if n % 2 == 1 else n - 1

    delta = float(np.abs(np.mean(np.diff(wavelength))))

    y_smooth = savgol_filter(
        intensity,
        window_length=window_length,
        polyorder=min(polyorder, window_length - 1),
        deriv=0,
        delta=delta,
        mode="interp",  # 使用 interp 模式，边界更平滑
    )
    return y_smooth


def _als_baseline(
    y: np.ndarray,
    lam: float = 1e5,
    p: float = 0.001,
    n_iter: int = 10,
    tol: float = 1e-6,
) -> np.ndarray:
    """
    Asymmetric Least Squares (ALS) 基线校正（优化版）。

    参数:
    - lam: 平滑程度，越大越平滑。
    - p: 权重不对称性，越小越偏向下包络。
    - n_iter: 最大迭代次数。
    - tol: 收敛阈值，提前终止判断。
    
    优化:
    - 添加收敛判断，提前终止
    - 使用 CSC 稀疏矩阵格式，提升求解效率
    - 大数据自动减少迭代次数
    """
    n = y.size
    
    # 大数据优化：自动调整迭代次数
    if n > 5000:
        n_iter = min(n_iter, 5)
    
    diag = np.ones(n)
    D = sparse.diags([diag[:-2], -2 * diag[1:-1], diag[2:]], [0, 1, 2], shape=(n - 2, n))
    DTD = (D.T @ D).tocsc()  # 转换为 CSC 格式，提升效率

    w = np.ones(n)
    z = y.copy()
    
    for i in range(n_iter):
        z_old = z.copy()
        W = sparse.spdiags(w, 0, n, n).tocsc()  # CSC 格式
        Z = W + lam * DTD
        z = sparse.linalg.spsolve(Z, w * y)
        
        # 提前终止判断（收敛检查）
        change = np.linalg.norm(z - z_old) / (np.linalg.norm(z) + 1e-10)
        if change < tol:
            break
        
        w = p * (y > z) + (1 - p) * (y < z)
    
    return z


def baseline_correction(
    wavelength: np.ndarray,
    intensity: np.ndarray,
    lam: float = 1e5,
    p: float = 0.001,
    n_iter: int = 10,
    clip_negative: bool = True,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    对谱线进行ALS基线校正，返回 (baseline, corrected)。
    
    参数:
    - clip_negative: 是否将校正后的负值裁剪为小正值（推荐对透射率/反射率启用）
    
    注意：
    - 对于透射率/反射率数据，基线校正可能产生负值，破坏物理意义
    - 建议先将透射率转换为吸光度后再进行基线校正
    """
    if len(intensity) < 5:
        baseline = np.zeros_like(intensity)
        return baseline, intensity.copy()

    baseline = _als_baseline(intensity.astype(float), lam=lam, p=p, n_iter=n_iter)
    corrected = intensity - baseline
    
    # 对于比率型数据（透射率/反射率），防止出现负值
    if clip_negative:
        if np.any(corrected < 0):
            import warnings
            neg_count = np.sum(corrected < 0)
            warnings.warn(
                f"基线校正后产生 {neg_count} 个负值，已裁剪为 1e-10。"
                "建议：对透射率/反射率数据，先转换为吸光度再做基线校正。",
                UserWarning
            )
            corrected = np.maximum(corrected, 1e-10)
    
    return baseline, corrected


def preprocess_spectrum(
    df: pd.DataFrame,
    smooth_window: int = 15,
    smooth_polyorder: int = 3,
    enable_baseline: bool = True,
    baseline_lam: float = 1e5,
    baseline_p: float = 0.001,
    baseline_iter: int = 10,
    clip_negative: bool = True,
) -> pd.DataFrame:
    """
    统一入口：给定包含 'wavelength' 和 'intensity' 列的DataFrame，
    返回附加平滑和基线校正结果的新DataFrame。
    
    参数:
    - clip_negative: 基线校正后是否裁剪负值（防止透射率/反射率变负）
    """
    wavelength = df["wavelength"].to_numpy()
    intensity = df["intensity"].to_numpy()

    y_smooth = savgol_smooth(
        wavelength,
        intensity,
        window_length=smooth_window,
        polyorder=smooth_polyorder,
    )

    if enable_baseline:
        baseline, corrected = baseline_correction(
            wavelength,
            y_smooth,
            lam=baseline_lam,
            p=baseline_p,
            n_iter=baseline_iter,
            clip_negative=clip_negative,
        )
    else:
        baseline = np.zeros_like(y_smooth)
        corrected = y_smooth.copy()

    df_out = df.copy()
    df_out["smooth"] = y_smooth
    df_out["baseline"] = baseline
    df_out["corrected"] = corrected
    return df_out

