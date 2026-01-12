#!/bin/bash
# Wagstaff-Lab 初始化/更新后置脚本

echo "🔧 正在执行项目初始化..."

# 1. 恢复执行权限 (Git 可能会丢失 chmod +x)
chmod +x bin/*.sh
chmod +x src/*.py
chmod +x devtools/*.py
echo "✅ 脚本权限已修复"

# 2. 确保 Python 环境
# 尝试激活 conda 环境 (假设安装在标准位置)
if [ -z "$CONDA_DEFAULT_ENV" ] || [ "$CONDA_DEFAULT_ENV" != "dst_lab" ]; then
    echo "⚠️  检测到当前未处于 dst_lab 环境"
    source ~/miniconda3/etc/profile.d/conda.sh 2>/dev/null
    conda activate dst_lab 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ 已自动激活 dst_lab 环境"
    else
        echo "❌ 激活失败，请手动运行: conda activate dst_lab"
    fi
fi

# 3. 重新注册环境 (更新 PATH 和别名)
python devtools/installer.py

echo "🎉 项目环境同步完成！输入 'Wagstaff-Lab' 呼出控制台。"
