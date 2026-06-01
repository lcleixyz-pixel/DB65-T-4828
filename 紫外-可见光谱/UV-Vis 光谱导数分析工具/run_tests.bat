@echo off
chcp 65001 >nul
echo 正在运行算法准确性测试...
echo.
python tests\test_algorithms.py
echo.
pause
