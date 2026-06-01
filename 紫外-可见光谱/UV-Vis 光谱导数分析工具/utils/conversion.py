"""数据类型转换模块：支持透射率、吸光度、反射率及 Kubelka-Munk 转换"""
import numpy as np
import pandas as pd


def transmittance_to_absorbance(transmittance: np.ndarray, is_percent: bool = False) -> np.ndarray:
    """
    透射率转吸光度（Beer-Lambert 定律）: A = -log₁₀(T)
    
    参数:
    - transmittance: 透射率数据
    - is_percent: 是否为百分比形式
    
    注意：
    - 透射率必须在 (0, 1] 范围内
    - T=1 对应 A=0（无吸收），T→0 对应 A→∞（完全吸收）
    """
    T = transmittance.copy()
    if is_percent:
        T = T / 100.0
    
    # 检查有效性
    if np.any((T < -0.01) | (T > 1.05)):
        import warnings
        invalid_count = np.sum((T < -0.01) | (T > 1.05))
        warnings.warn(
            f"检测到 {invalid_count} 个无效透射率值（正常范围 0-1），已裁剪。",
            UserWarning
        )
    
    # 避免 log10(0) 的情况，设置下限
    T = np.clip(T, 1e-10, 1.0)
    
    absorbance = -np.log10(T)
    return absorbance


def absorbance_to_transmittance(absorbance: np.ndarray, as_percent: bool = False) -> np.ndarray:
    """
    吸光度转透射率: T = 10^(-A)
    """
    T = np.power(10, -absorbance)
    T = np.clip(T, 0, 1)
    
    if as_percent:
        T = T * 100.0
    
    return T


def reflectance_to_kubelka_munk(reflectance: np.ndarray, is_percent: bool = False) -> np.ndarray:
    """
    反射率转 Kubelka-Munk 函数: F(R∞) = (1-R)² / (2R)
    
    参数:
    - reflectance: 反射率数据
    - is_percent: 是否为百分比形式
    
    注意：
    - 此公式仅适用于无限厚（不透明）样品的反射率 R∞
    - K-M 函数与吸收系数 K 和散射系数 S 的关系：F(R∞) = K/S
    - 输入必须在 (0, 1] 范围内，超出范围会触发警告
    """
    R = reflectance.copy()
    if is_percent:
        R = R / 100.0
    
    # 检查数据有效性
    invalid_mask = (R < -0.01) | (R > 1.05)  # 允许小幅超出（噪声容差）
    if np.any(invalid_mask):
        import warnings
        invalid_count = np.sum(invalid_mask)
        invalid_range = f"[{np.min(R[invalid_mask]):.3f}, {np.max(R[invalid_mask]):.3f}]"
        warnings.warn(
            f"检测到 {invalid_count} 个无效反射率值 {invalid_range}（正常范围 0-1）。"
            "可能需要先进行基线校正或数据清洗。已自动裁剪。",
            UserWarning
        )
    
    # 裁剪到合理范围
    # 下限避免除以0，上限避免 R≈1 时 F(R)≈0 的数值不稳定
    R = np.clip(R, 1e-6, 0.999)
    
    km = (1.0 - R)**2 / (2.0 * R)
    return km


def kubelka_munk_to_reflectance(km: np.ndarray, as_percent: bool = False) -> np.ndarray:
    """
    Kubelka-Munk 转反射率（逆变换）
    
    从 F(R∞) = (1-R)²/(2R) 求解 R：
    整理为一元二次方程：R² - 2(F+1)R + 1 = 0
    解：R = (F+1) - √(F²+2F)
    
    参数:
    - km: K-M 函数值，必须 ≥ 0
    - as_percent: 是否返回百分比形式
    """
    # K-M 函数必须非负
    if np.any(km < 0):
        import warnings
        neg_count = np.sum(km < 0)
        warnings.warn(
            f"检测到 {neg_count} 个负 K-M 值，已裁剪为 0。K-M 函数必须非负。",
            UserWarning
        )
    
    y = np.maximum(km, 0)
    
    # 求解一元二次方程：R² - 2(y+1)R + 1 = 0
    # 判别式：Δ = 4(y+1)² - 4 = 4[(y+1)² - 1] = 4(y²+2y)
    # 解：R = [(y+1) ± √(y²+2y)] / 1
    # 取物理解（R < 1）：R = (y+1) - √(y²+2y)
    discriminant = y**2 + 2.0 * y
    R = (y + 1.0) - np.sqrt(np.maximum(discriminant, 0))  # 防止数值误差导致负判别式
    R = np.clip(R, 0, 1)
    
    if as_percent:
        R = R * 100.0
    return R


def convert_data_type(
    df: pd.DataFrame,
    from_type: str,
    to_type: str,
) -> pd.DataFrame:
    """
    转换数据类型
    
    参数:
    - df: 包含 wavelength 和 intensity 列的 DataFrame
    - from_type/to_type 支持:
      - "transmittance", "transmittance%" (透射率)
      - "reflectance", "reflectance%" (反射率，数学上等同于透射率处理)
      - "absorbance" (吸光度)
      - "kubelka_munk" (K-M 函数)
    """
    if from_type == to_type:
        return df
    
    df_out = df.copy()
    intensity = df["intensity"].to_numpy()
    
    # 1. 统一转为比率 (0-1) (即 T 或 R)
    # 我们假设 T 和 R 在数学处理上是等价的（都是比率），只是物理意义不同
    ratio = None
    
    if from_type in ["transmittance", "reflectance"]:
        ratio = intensity
    elif from_type in ["transmittance%", "reflectance%"]:
        ratio = intensity / 100.0
    elif from_type == "absorbance":
        ratio = absorbance_to_transmittance(intensity, as_percent=False)
    elif from_type == "kubelka_munk":
        ratio = kubelka_munk_to_reflectance(intensity, as_percent=False)
    else:
        # 未知类型或默认情况，假设已经是比率或不进行预处理
        # 如果是未知类型，可能导致后续转换错误，但尽力而为
        ratio = intensity

    # 确保比率在合理范围 (0-1)
    # 注意：某些原始数据可能因噪声略小于0或大于1，clip是必要的
    ratio = np.clip(ratio, 1e-10, 1.0)

    # 2. 转为目标类型
    target_data = None
    
    if to_type in ["transmittance", "reflectance"]:
        target_data = ratio
    elif to_type in ["transmittance%", "reflectance%"]:
        target_data = ratio * 100.0
    elif to_type == "absorbance":
        target_data = transmittance_to_absorbance(ratio, is_percent=False)
    elif to_type == "kubelka_munk":
        target_data = reflectance_to_kubelka_munk(ratio, is_percent=False)
    else:
        target_data = ratio

    df_out["intensity"] = target_data
    return df_out
