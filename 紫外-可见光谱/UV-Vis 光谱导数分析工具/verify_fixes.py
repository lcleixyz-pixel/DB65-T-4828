"""快速验证关键修复"""
import numpy as np
import warnings

# 捕获所有警告
warnings.simplefilter("always")

print("=" * 60)
print("关键修复验证")
print("=" * 60)

# 测试 1: 导数计算（降序波长）
print("\n[验证 1] 降序波长导数符号")
try:
    from utils.derivative import compute_derivatives
    
    wl_desc = np.linspace(800, 200, 100)  # 降序
    sig_inc = np.linspace(0, 1, 100)  # 递增
    
    d1, _ = compute_derivatives(wl_desc, sig_inc, window_length=11, polyorder=2)
    mean_d1 = np.mean(d1[10:-10])
    
    print(f"  降序波长 [800→200]，信号递增 [0→1]")
    print(f"  一阶导数均值: {mean_d1:.6f}")
    
    if mean_d1 > 0:
        print("  [OK] 通过：导数符号正确")
    else:
        print("  [FAIL] 失败：导数符号错误")
except Exception as e:
    print(f"  [ERROR] 异常: {e}")

# 测试 2: K-M 转换往返
print("\n[验证 2] K-M 转换往返一致性")
try:
    from utils.conversion import reflectance_to_kubelka_munk, kubelka_munk_to_reflectance
    
    R_orig = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
    F = reflectance_to_kubelka_munk(R_orig)
    R_back = kubelka_munk_to_reflectance(F)
    
    max_err = np.max(np.abs(R_orig - R_back))
    print(f"  原始反射率: {R_orig}")
    print(f"  往返误差: {max_err:.2e}")
    
    if max_err < 1e-6:
        print("  [OK] 通过：往返误差 < 1e-6")
    else:
        print("  [FAIL] 失败：误差过大")
except Exception as e:
    print(f"  [ERROR] 异常: {e}")

# 测试 3: K-M 边界检查（应触发警告）
print("\n[验证 3] K-M 无效值警告")
try:
    from utils.conversion import reflectance_to_kubelka_munk
    
    # 包含无效值
    R_invalid = np.array([0.5, 1.2, -0.1, 0.8])  # 1.2 和 -0.1 无效
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        F = reflectance_to_kubelka_munk(R_invalid)
        
        if len(w) > 0:
            print(f"  触发警告: {w[0].message}")
            print("  [OK] 通过：检测到无效值并警告")
        else:
            print("  [WARN] 未触发警告（可能是边界情况）")
except Exception as e:
    print(f"  [ERROR] 异常: {e}")

# 测试 4: 基线校正负值处理
print("\n[验证 4] 基线校正负值裁剪")
try:
    from utils.preprocessing import baseline_correction
    
    wl = np.linspace(400, 700, 100)
    # 创建一个低值信号（容易产生负值）
    intensity = 0.1 + 0.05 * np.sin(wl / 50) + np.random.normal(0, 0.02, 100)
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        baseline, corrected = baseline_correction(
            wl, intensity, lam=1e5, clip_negative=True
        )
        
        has_negative = np.any(corrected < 0)
        print(f"  校正后有负值: {has_negative}")
        print(f"  最小值: {np.min(corrected):.6f}")
        
        if not has_negative:
            print("  [OK] 通过：成功裁剪负值")
        else:
            print("  [FAIL] 失败：仍有负值")
            
        if len(w) > 0:
            print(f"  警告消息: {w[0].message}")
except Exception as e:
    print(f"  [ERROR] 异常: {e}")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
