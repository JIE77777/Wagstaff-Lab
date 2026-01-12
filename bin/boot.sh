#!/bin/bash
# =========================================================
# Wagstaff-Lab Bootloader (启动引导程序)
# 职责: 设置环境库(LD_LIBRARY_PATH)并启动 DST 二进制文件
# =========================================================

# --- 1. 定位配置 ---
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/conf/settings.ini"

# --- 2. 简易配置读取器 ---
read_config() {
    local section=$1
    local key=$2
    local val=$(awk -F ' = ' -v section="[$section]" -v key="$key" '
        $0 == section { in_section=1; next }
        /^\[/ { in_section=0 }
        in_section && $1 == key { print $2; exit }
    ' "$CONFIG_FILE")
    echo "${val/\~/$HOME}"
}

# --- 3. 加载核心变量 ---
INSTALL_DIR=$(read_config "PATHS" "DST_ROOT")
CLUSTER_NAME=$(read_config "SERVER" "CLUSTER_NAME")

# --- 4. 环境检查 ---
if [ -z "$INSTALL_DIR" ] || [ -z "$CLUSTER_NAME" ]; then
    echo "❌ [Boot] 错误: 无法读取配置，请检查 conf/settings.ini"
    exit 1
fi

BIN_DIR="$INSTALL_DIR/bin"

# --- 5. 设置依赖库 (关键步骤) ---
# 这是让 Linux 能运行 DST 的核心魔法
export LD_LIBRARY_PATH="$BIN_DIR/lib32:$BIN_DIR:$LD_LIBRARY_PATH"

# --- 6. 进入执行目录 ---
# 必须进入 bin 目录，否则游戏找不到 data
cd "$BIN_DIR" || { echo "❌ [Boot] 找不到目录: $BIN_DIR"; exit 1; }

echo "⚡ [Boot] 正在初始化 Wagstaff 引擎..."
echo "   - 游戏根目录: $INSTALL_DIR"
echo "   - 存档簇名称: $CLUSTER_NAME"

# --- 7. 启动进程 (Master) ---
# 使用 -dmS 让它在后台 Screen 运行
screen -dmS "DST_Master" ./dontstarve_dedicated_server_nullrenderer -console -cluster "$CLUSTER_NAME" -shard Master
echo "✅ [Boot] 地面服务器 (Master) 已启动"

# --- 8. 启动进程 (Caves) ---
# 只有当存档中存在 Caves 文件夹时才启动，或者你可以选择强制启动
# 这里为了稳妥，我们直接启动，如果没洞穴配置游戏会自动停止 Caves 进程，无伤大雅
screen -dmS "DST_Caves" ./dontstarve_dedicated_server_nullrenderer -console -cluster "$CLUSTER_NAME" -shard Caves
echo "✅ [Boot] 洞穴服务器 (Caves) 已启动"

echo "✨ 启动序列完成。"
