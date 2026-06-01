"""
算法准确性验证测试
验证导数计算和 Kubelka-Munk 转换的正确性
"""
import numpy as np
import sys
import os

# 添加父目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.derivative import compute_derivatives
from utils.conversion import (
    reflectance_to_kubelka_munk, 
    kubelka_munk_to_reflectance,
    transmittance_to_absorbance,
    absorbance_to_transmittance,
)


def test_derivative_sign_with_descending_wavelength():
    """测试降序波长是否导致导数符号错误"""
    print("\n[测试 1] 降序波长的导数符号正确性")
    
    # 降序波长 + 线性增长信号
    wl_desc = np.linspace(800, 200, 100)  # 降序
    sig_inc = np.linspace(0, 1, 100)  # 递增
    
    d1_desc, d2_desc = compute_derivatives(wl_desc, sig_inc, window_length=11, polyorder=2)
    
    # 一阶导数应该为正（信号递增，波长递减 → dS/dλ < 0 但我们关心 dS/d(波长递减) 应为正）
    # 物理意义：随着波长减小，信号增大
    mean_d1 = np.mean(d1_desc[10:-10])  # 忽略边界
    
    print(f"  降序波长 [800→200 nm]，信号递增 [0→1]")
    print(f"  一阶导数均值: {mean_d1:.6f}")
    
    # 升序波长 + 线性增长信号（对照组）
    wl_asc = np.linspace(200, 800, 100)  # 升序
    sig_inc_2 = np.linspace(0, 1, 100)  # 递增
    
    d1_asc, d2_asc = compute_derivatives(wl_asc, sig_inc_2, window_length=11, polyorder=2)
    mean_d1_asc = np.mean(d1_asc[10:-10])
    
    print(f"  升序波长 [200→800 nm]，信号递增 [0→1]")
    print(f"  一阶导数均值: {mean_d1_asc:.6f}")
    
    # 两者应该符号一致（都表示信号随波长增加）
    assert mean_d1 > 0, f"❌ 降序波长导致导数符号错误！d1={mean_d1:.6f}"
    assert mean_d1_asc > 0, f"❌ 升序波长导数计算错误！d1={mean_d1_asc:.6f}"
    
    print(f"  ✅ 测试通过：降序和升序波长的导数符号一致且正确")


def test_km_roundtrip():
    """测试 K-M 转换的可逆性（往返一致性）"""
    print("\n[测试 2] K-M 转换的往返一致性")
    
    R_original = np.array([0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.95])
    
    # R → F(R) → R'
    F = reflectance_to_kubelka_munk(R_original)
    R_recovered = kubelka_munk_to_reflectance(F)
    
    max_error = np.max(np.abs(R_original - R_recovered))
    rel_error = max_error / np.mean(R_original)
    
    print(f"  原始反射率: {R_original}")
    print(f"  K-M 值: {F}")
    print(f"  恢复反射率: {R_recovered}")
    print(f"  最大误差: {max_error:.2e} (相对误差: {rel_error:.2%})")
    
    np.testing.assert_allclose(R_original, R_recovered, rtol=1e-6, atol=1e-8)
    print(f"  ✅ 测试通过：往返误差 < 1e-6")


def test_km_boundary_values():
    """测试 K-M 在边界值的行为"""
    print("\n[测试 3] K-M 边界值正确性")
    
    # R=1: 完全反射, F(R)=0
    F_at_1 = reflectance_to_kubelka_munk(np.array([0.999]))
    print(f"  R=0.999 → F(R)={F_at_1[0]:.6f} (理论: 0)")
    assert F_at_1[0] < 0.01, "❌ R≈1 时 F(R) 应接近 0"
    
    # R→0: 完全吸收, F(R)→∞
    F_at_low = reflectance_to_kubelka_munk(np.array([0.01]))
    print(f"  R=0.01 → F(R)={F_at_low[0]:.3f} (理论: 很大)")
    assert F_at_low[0] > 10, "❌ R→0 时 F(R) 应很大"
    
    # R=0.5: F(R) = 0.25/1 = 0.25
    F_at_half = reflectance_to_kubelka_munk(np.array([0.5]))
    print(f"  R=0.5 → F(R)={F_at_half[0]:.6f} (理论: 0.25)")
    np.testing.assert_allclose(F_at_half[0], 0.25, rtol=1e-5)
    
    print(f"  ✅ 测试通过：边界值行为正确")


def test_absorbance_roundtrip():
    """测试吸光度转换的可逆性"""
    print("\n[测试 4] 吸光度转换的往返一致性")
    
    T_original = np.array([0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
    
    # T → A → T'
    A = transmittance_to_absorbance(T_original)
    T_recovered = absorbance_to_transmittance(A)
    
    max_error = np.max(np.abs(T_original - T_recovered))
    
    print(f"  原始透射率: {T_original}")
    print(f"  吸光度: {A}")
    print(f"  恢复透射率: {T_recovered}")
    print(f"  最大误差: {max_error:.2e}")
    
    np.testing.assert_allclose(T_original, T_recovered, rtol=1e-6, atol=1e-8)
    print(f"  ✅ 测试通过：往返误差 < 1e-6")


def test_derivative_with_noise():
    """测试含噪声信号的导数鲁棒性"""
    print("\n[测试 5] 含噪声信号的导数平滑效果")
    
    # 生成带噪声的高斯峰
    wl = np.linspace(400, 700, 300)
    signal_clean = np.exp(-((wl - 550)**2) / (2 * 20**2))  # 高斯峰
    noise = np.random.normal(0, 0.05, len(wl))
    signal_noisy = signal_clean + noise
    
    # 不同窗口大小
    d1_small, _ = compute_derivatives(wl, signal_noisy, window_length=5, polyorder=2)
    d1_large, _ = compute_derivatives(wl, signal_noisy, window_length=25, polyorder=3)
    
    # 大窗口应该更平滑（标准差更小）
    std_small = np.std(d1_small)
    std_large = np.std(d1_large)
    
    print(f"  窗口=5:  导数标准差 = {std_small:.6f}")
    print(f"  窗口=25: 导数标准差 = {std_large:.6f}")
    print(f"  平滑比 = {std_small / std_large:.2f}x")
    
    assert std_large < std_small, "❌ 大窗口应该产生更平滑的导数"
    print(f"  ✅ 测试通过：大窗口有效抑制噪声")


def test_km_physical_meaning():
    """测试 K-M 函数的物理意义"""
    print("\n[测试 6] K-M 函数的物理意义验证")
    
    # 红宝石 Cr³⁺ 典型反射光谱（简化）
    # 在 550 nm（绿光）有强吸收 → 低反射率 → 高 K-M 值
    wl = np.array([450, 550, 650, 694])  # nm
    R = np.array([0.4, 0.15, 0.3, 0.6])  # 绿光区吸收强
    
    F = reflectance_to_kubelka_munk(R)
    
    print(f"  波长 (nm): {wl}")
    print(f"  反射率 R: {R}")
    print(f"  K-M 值:   {F}")
    
    # 最强吸收（最低 R）应对应最高 F(R)
    idx_min_R = np.argmin(R)
    idx_max_F = np.argmax(F)
    
    print(f"  最低反射率位置: {wl[idx_min_R]} nm (R={R[idx_min_R]:.2f})")
    print(f"  最高 K-M 值位置: {wl[idx_max_F]} nm (F={F[idx_max_F]:.2f})")
    
    assert idx_min_R == idx_max_F, "❌ 最低反射率应对应最高 K-M 值"
    print(f"  ✅ 测试通过：K-M 值与吸收强度正相关")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("光谱分析算法准确性测试")
    print("=" * 60)
    
    tests = [
        test_derivative_sign_with_descending_wavelength,
        test_km_roundtrip,
        test_km_boundary_values,
        test_absorbance_roundtrip,
        test_derivative_with_noise,
        test_km_physical_meaning,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ 测试失败: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试完成: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
