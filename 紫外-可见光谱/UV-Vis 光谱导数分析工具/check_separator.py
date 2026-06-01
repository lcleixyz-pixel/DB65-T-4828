"""检查文件分隔符"""

def check_file_separator(filepath, name):
    print(f"\n{'='*60}")
    print(f"文件: {name}")
    print('='*60)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [f.readline() for _ in range(5)]
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # 检测分隔符
        has_comma = ',' in line
        has_tab = '\t' in line
        has_space = ' ' in line
        
        # 计算分隔符
        comma_count = line.count(',')
        tab_count = line.count('\t')
        space_count = line.count(' ')
        multi_space = '  ' in line  # 多个空格
        
        print(f"\n第 {i+1} 行:")
        print(f"  内容: {repr(line[:80])}")
        print(f"  逗号: {comma_count}, 制表符: {tab_count}, 空格: {space_count}")
        print(f"  有多空格: {'是' if multi_space else '否'}")
        
        if has_comma:
            print(f"  推荐分隔符: 逗号 (,)")
        elif has_tab:
            print(f"  推荐分隔符: 制表符 (\\t)")
        elif multi_space:
            print(f"  推荐分隔符: 多空格 (\\s+)")
        elif has_space:
            print(f"  推荐分隔符: 单空格 ( )")
        else:
            print(f"  推荐分隔符: 未知")

print("█"*60)
print("文件分隔符检测")
print("█"*60)

check_file_separator(
    r"C:\Users\Martyr\OneDrive\桌面\超景深显微镜\工具\0208-3.txt",
    "0208-3.txt"
)

check_file_separator(
    r"C:\Users\Martyr\OneDrive\桌面\超景深显微镜\工具\0601.txt",
    "0601.txt"
)

print("\n" + "█"*60)
