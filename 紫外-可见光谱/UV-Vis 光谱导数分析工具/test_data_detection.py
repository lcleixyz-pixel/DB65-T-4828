"""测试数据类型识别"""
import sys
import pandas as pd
import numpy as np

# 模拟 data_loader 的识别逻辑
def detect_intensity_type(intensity_series):
    """模拟工具的数据类型识别逻辑"""
    intensity = intensity_series.to_numpy()
    
    intensity_desc = "unknown"
    if (intensity >= 0).all() and (intensity <= 1.2).all():
        intensity_desc = "transmittance(0-1)"
    elif (intensity >= 0).all() and (intensity <= 120).all():
        intensity_desc = "transmittance(%)"
    elif (intensity >= 0).all():
        intensity_desc = "absorbance"
    else:
        intensity_desc = "mixed"
    
    return intensity_desc

# 测试文件1：0208-3.txt
print("="*60)
print("测试文件 1: 0208-3.txt (仪器显示 Mode R %)")
print("="*60)

file1_path = r"c:\Users\Martyr\OneDrive\桌面\超景深显微镜\工具\0208-3.txt"
try:
    df1 = pd.read_csv(file1_path, sep=None, engine='python', header=None)
    df1.columns = ["wavelength", "intensity"]
    
    print(f"数据点数: {len(df1)}")
    print(f"波长范围: {df1['wavelength'].min():.1f} - {df1['wavelength'].max():.1f} nm")
    print(f"强度范围: {df1['intensity'].min():.3f} - {df1['intensity'].max():.3f}")
    print(f"强度均值: {df1['intensity'].mean():.3f}")
    print(f"强度中位数: {df1['intensity'].median():.3f}")
    
    detected_type = detect_intensity_type(df1['intensity'])
    print(f"\n工具识别为: {detected_type}")
    print(f"用户说明是: 反射率 Mode R (%)")
    
    if detected_type == "transmittance(%)":
        print("✅ 识别正确（反射率%与透射率%在数学上等价处理）")
    else:
        print(f"❌ 识别错误！应识别为 reflectance(%) 但识别为 {detected_type}")
        
except Exception as e:
    print(f"❌ 读取失败: {e}")

print("\n" + "="*60)
print("测试文件 2: 0601.txt")
print("="*60)

file2_path = r"c:\Users\Martyr\OneDrive\桌面\超景深显微镜\工具\0601.txt"
try:
    df2 = pd.read_csv(file2_path, sep=None, engine='python', header=None)
    
    # 跳过表头
    if len(df2) > 0:
        try:
            float(df2.iloc[0, 0])
            float(df2.iloc[0, 1])
        except:
            df2 = df2.iloc[1:].reset_index(drop=True)
    
    df2.columns = ["wavelength", "intensity"]
    df2['wavelength'] = pd.to_numeric(df2['wavelength'], errors='coerce')
    df2['intensity'] = pd.to_numeric(df2['intensity'], errors='coerce')
    df2 = df2.dropna()
    
    print(f"数据点数: {len(df2)}")
    print(f"波长范围: {df2['wavelength'].min():.1f} - {df2['wavelength'].max():.1f} nm")
    print(f"强度范围: {df2['intensity'].min():.4f} - {df2['intensity'].max():.4f}")
    print(f"强度均值: {df2['intensity'].mean():.4f}")
    print(f"强度中位数: {df2['intensity'].median():.4f}")
    
    detected_type = detect_intensity_type(df2['intensity'])
    print(f"\n工具识别为: {detected_type}")
    
    if detected_type == "transmittance(0-1)":
        print("可能是反射率(0-1)格式或吸光度")
    
except Exception as e:
    print(f"❌ 读取失败: {e}")

print("\n" + "="*60)
print("数据类型识别规则检查")
print("="*60)
print("当前规则:")
print("  0 ≤ intensity ≤ 1.2  → transmittance(0-1)")
print("  0 ≤ intensity ≤ 120  → transmittance(%)")
print("  intensity ≥ 0 且超出上述范围 → absorbance")
print("  有负值 → mixed")
print("\n问题:")
print("  - 反射率与透射率在识别中被视为相同（数学等价）")
print("  - 工具不区分反射率和透射率（因物理测量方式不同但数学范围相同）")
print("  - 用户需在界面中手动选择是 reflectance 还是 transmittance")
