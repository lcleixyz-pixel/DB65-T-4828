# -*- coding: utf-8 -*-
import re

readme_path = r'README.md'

with open(readme_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换文本
old_text = '自动峰值标记会以 "auto-peak" 的说明显示在预处理谱图子图上。'
new_text = '''自动极值标记（峰/谷）会根据检测数据源显示在对应的子图上：
- 检测"原始谱"：标记显示在原始谱子图
- 检测"平滑谱"或"基线校正后"：标记显示在预处理谱子图'''

content = content.replace(old_text, new_text)

with open(readme_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('README.md updated successfully')
