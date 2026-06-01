"""分析用户的两个数据文件"""
import pandas as pd
import numpy as np

def analyze_file(filepath, name, expected_type):
    print("\n" + "="*60)
    print(f"分析文件: {name}")
    print(f"仪器说明: {expected_type}")
    print("="*60)
    
    try:
        # 读取文件（自动检测分隔符）
        df = pd.read_csv(filepath, sep=None, engine='python', header=None, encoding='utf-8', on_bad_lines='skip')
        
        print(f"\n初步读取:")
        print(f"  行数: {len(df)}, 列数: {df.shape[1]}")
        print(f"  前3行:\n{df.head(3)}")
        
        # 检查是否有表头
        try:
            float(df.iloc[0, 0])
            float(df.iloc[0, 1])
            has_header = False
        except:
            has_header = True
            df = df.iloc[1:].reset_index(drop=True)
        
        # 只取前两列（波长和强度）
        if df.shape[1] >= 2:
            df = df.iloc[:, [0, 1]]
        
        # 转换为数值
        df.columns = ["wavelength", "intensity"]
        df['wavelength'] = pd.to_numeric(df['wavelength'], errors='coerce')
        df['intensity'] = pd.to_numeric(df['intensity'], errors='coerce')
        
        print(f"\n数值转换后:")
        print(f"  行数: {len(df)}, NaN数: {df.isna().sum().sum()}")
        
        df = df.dropna()
        
        print(f"\n去除NaN后:")
        print(f"  有效数据点: {len(df)}")
        
        wl = df['wavelength'].to_numpy()
        intensity = df['intensity'].to_numpy()
        
        print(f"\n基本信息:")
        print(f"  有表头: {'是' if has_header else '否'}")
        print(f"  数据点数: {len(df)}")
        print(f"  波长范围: {wl.min():.2f} - {wl.max():.2f} nm")
        print(f"  波长顺序: {'升序' if np.mean(np.diff(wl)) > 0 else '降序'}")
        
        print(f"\n强度统计:")
        print(f"  最小值: {intensity.min():.6f}")
        print(f"  最大值: {intensity.max():.6f}")
        print(f"  均值:   {intensity.mean():.6f}")
        print(f"  中位数: {np.median(intensity):.6f}")
        print(f"  标准差: {intensity.std():.6f}")
        
        # 数据类型识别（模拟工具逻辑）
        detected_type = "unknown"
        if (intensity >= 0).all() and (intensity <= 1.2).all():
            detected_type = "transmittance(0-1)"
        elif (intensity >= 0).all() and (intensity <= 120).all():
            detected_type = "transmittance(%)"
        elif (intensity >= 0).all():
            detected_type = "absorbance"
        else:
            detected_type = "mixed"
        
        print(f"\n类型识别:")
        print(f"  工具自动识别: {detected_type}")
        print(f"  用户说明类型: {expected_type}")
        
        # 判断是否合理
        if expected_type == "reflectance(%)":
            if detected_type == "transmittance(%)":
                print(f"  [OK] 数学上等价（反射率%与透射率%处理相同）")
                print(f"  [WARN] 但用户需手动选择 reflectance% 而非 transmittance%")
            elif detected_type == "transmittance(0-1)":
                print(f"  [ERROR] 识别错误！强度范围 {intensity.min():.2f}-{intensity.max():.2f}")
                print(f"     如果是反射率%，应该是 0-100 范围")
                print(f"     当前范围提示数据可能有问题或被预处理")
            else:
                print(f"  [ERROR] 识别为 {detected_type}，与预期不符")
        
        # 显示前后各5个点
        print(f"\n数据样本（前5行）:")
        print(df.head(5).to_string(index=False))
        print(f"\n数据样本（后5行）:")
        print(df.tail(5).to_string(index=False))
        
        return df
        
    except Exception as e:
        print(f"[ERROR] 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return None

# 分析两个文件
print("\n" + "█"*60)
print("用户数据文件类型识别测试")
print("█"*60)

df1 = analyze_file(
    r"C:\Users\Martyr\OneDrive\桌面\超景深显微镜\工具\0208-3.txt",
    "0208-3.txt",
    "reflectance(%)"
)

df2 = analyze_file(
    r"C:\Users\Martyr\OneDrive\桌面\超景深显微镜\工具\0601.txt",
    "0601.txt",
    "未知（请用户说明）"
)

# 总结发现的问题
print("\n" + "█"*60)
print("问题总结")
print("█"*60)

if df1 is not None:
    intensity1 = df1['intensity'].to_numpy()
    print("\n【文件1: 0208-3.txt】")
    print(f"  仪器显示: Mode R (%)  → 应为反射率百分比")
    print(f"  实际数值范围: {intensity1.min():.2f} - {intensity1.max():.2f}")
    
    if intensity1.max() < 100 and intensity1.min() > 0:
        if intensity1.max() > 1.2:
            print(f"  [OK] 数值在 0-100 范围内，符合反射率(%)")
            print(f"  [OK] 工具会识别为 transmittance(%)，数学等价")
        else:
            print(f"  [WARN] 数值在 0-1.2 内，工具会识别为 transmittance(0-1)")
            print(f"  [WARN] 但仪器说是%格式，存在矛盾")
            print(f"  建议: 检查仪器设置或数据是否被预处理")

if df2 is not None:
    intensity2 = df2['intensity'].to_numpy()
    print("\n【文件2: 0601.txt】")
    print(f"  实际数值范围: {intensity2.min():.5f} - {intensity2.max():.5f}")
    
    if intensity2.max() <= 1.2:
        print(f"  [OK] 数值在 0-1 范围内")
        print(f"  工具识别: transmittance(0-1) 或 reflectance(0-1)")
        print(f"  物理意义可能是: 反射率(0-1) 或 透射率(0-1) 或 吸光度")

print("\n" + "█"*60)
