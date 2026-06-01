"""
验证算法正确性的脚本
在优化前后运行，确保结果一致
"""
import numpy as np
import pandas as pd
from utils.data_loader import load_spectrum_from_uploaded_file
from utils.preprocessing import savgol_smooth, baseline_correction, preprocess_spectrum
from utils.derivative import compute_derivatives, add_derivatives_columns

def test_savgol_smooth():
    """测试 Savitzky-Golay 平滑"""
    print("\n=== 测试 Savitzky-Golay 平滑 ===")
    
    # 测试数据：带噪声的正弦波
    x = np.linspace(0, 10, 100)
    y_true = np.sin(x)
    y_noisy = y_true + 0.1 * np.random.randn(100)
    
    # 平滑
    y_smooth = savgol_smooth(x, y_noisy, window_length=11, polyorder=3)
    
    # 验证：平滑后的数据应该更接近真实值
    error_before = np.mean((y_noisy - y_true) ** 2)
    error_after = np.mean((y_smooth - y_true) ** 2)
    
    print(f"平滑前误差: {error_before:.6f}")
    print(f"平滑后误差: {error_after:.6f}")
    print(f"误差降低: {(error_before - error_after) / error_before * 100:.1f}%")
    
    assert error_after < error_before, "平滑应该降低噪声"
    print("[PASS] 测试通过")
    return y_smooth

def test_baseline_correction():
    """测试 ALS 基线校正"""
    print("\n=== 测试 ALS 基线校正 ===")
    
    # 测试数据：带基线漂移的峰
    x = np.linspace(0, 100, 500)
    baseline_true = 0.1 * x  # 线性基线
    peak = 5 * np.exp(-((x - 50) ** 2) / 20)  # 高斯峰
    y = baseline_true + peak
    
    # 基线校正
    baseline_est, corrected = baseline_correction(x, y, lam=1e5, p=0.001, n_iter=10)
    
    # 验证：估计的基线应该接近真实基线
    baseline_error = np.mean((baseline_est - baseline_true) ** 2)
    print(f"基线估计误差: {baseline_error:.6f}")
    print(f"校正后峰高: {np.max(corrected):.3f} (真实峰高: {np.max(peak):.3f})")
    
    # 基线误差应该较小
    assert baseline_error < 0.5, "基线估计误差应该较小"
    # 校正后的峰高应该接近真实峰高
    assert abs(np.max(corrected) - np.max(peak)) < 0.5, "校正后峰高应该接近真实值"
    print("[PASS] 测试通过")
    return baseline_est, corrected

def test_derivatives():
    """测试导数计算"""
    print("\n=== 测试导数计算 ===")
    
    # 测试数据：多项式函数 y = x^2
    x = np.linspace(0, 10, 100)
    y = x ** 2
    
    # 计算导数
    d1, d2 = compute_derivatives(x, y, window_length=11, polyorder=3)
    
    # 理论导数：dy/dx = 2x, d²y/dx² = 2
    d1_true = 2 * x
    d2_true = 2 * np.ones_like(x)
    
    # 验证（忽略边界点）
    margin = 10
    d1_error = np.mean((d1[margin:-margin] - d1_true[margin:-margin]) ** 2)
    d2_error = np.mean((d2[margin:-margin] - d2_true[margin:-margin]) ** 2)
    
    print(f"一阶导数误差: {d1_error:.6f}")
    print(f"二阶导数误差: {d2_error:.6f}")
    
    # 误差应该很小
    assert d1_error < 0.1, "一阶导数应该准确"
    assert d2_error < 0.1, "二阶导数应该准确"
    print("✓ 测试通过")
    return d1, d2

def test_with_real_data():
    """使用真实数据测试"""
    print("\n=== 测试真实数据处理流程 ===")
    
    # 生成模拟的光谱数据
    wavelength = np.linspace(200, 800, 600)
    # 模拟吸收峰
    peak1 = 2 * np.exp(-((wavelength - 300) ** 2) / 100)
    peak2 = 3 * np.exp(-((wavelength - 500) ** 2) / 200)
    baseline = 0.5 + 0.0005 * wavelength
    noise = 0.05 * np.random.randn(len(wavelength))
    intensity = baseline + peak1 + peak2 + noise
    
    df = pd.DataFrame({"wavelength": wavelength, "intensity": intensity})
    
    # 预处理
    df_prep = preprocess_spectrum(
        df,
        smooth_window=11,
        smooth_polyorder=3,
        enable_baseline=True,
        baseline_lam=1e5,
        baseline_p=0.001,
    )
    
    # 导数
    df_all = add_derivatives_columns(
        df_prep,
        source_column="corrected",
        window_length=11,
        polyorder=3,
    )
    
    # 验证：数据应该包含所有必要列
    required_cols = ["wavelength", "intensity", "smooth", "baseline", "corrected", "corrected_1st", "corrected_2nd"]
    assert all(col in df_all.columns for col in required_cols), "缺少必要列"
    
    # 验证：数据长度应该一致
    assert len(df_all) == len(df), "数据长度应该一致"
    
    # 验证：无 NaN 值
    assert not df_all.isna().any().any(), "不应该有 NaN 值"
    
    print(f"数据点数: {len(df_all)}")
    print(f"列数: {len(df_all.columns)}")
    print(f"波长范围: [{df_all['wavelength'].min():.2f}, {df_all['wavelength'].max():.2f}]")
    print("✓ 测试通过")
    
    return df_all

if __name__ == "__main__":
    print("=" * 60)
    print("算法验证测试")
    print("=" * 60)
    
    try:
        test_savgol_smooth()
        test_baseline_correction()
        test_derivatives()
        test_with_real_data()
        
        print("\n" + "=" * 60)
        print("[PASS] 所有测试通过！算法实现正确。")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n[FAIL] 测试失败: {e}")
    except Exception as e:
        print(f"\n[ERROR] 错误: {e}")
        import traceback
        traceback.print_exc()
