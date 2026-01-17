#!/bin/bash
# Wagstaff-Lab 初始化/更新后置脚本

echo "🔧 正在执行项目初始化..."

# 1. 恢复执行权限 (Git 可能会丢失 chmod +x)
chmod +x core/*.py
chmod +x apps/cli/commands/*.py
chmod +x apps/webcraft/*.py
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

# 3. 通过 pyproject.toml 注册入口
echo "建议执行: python -m pip install -e \".[cli]\" 以注册 wagstaff 入口"
echo "如需完整依赖: python -m pip install -e \".[all]\""

echo "🎉 项目环境同步完成！使用 wagstaff 进入控制台。"
