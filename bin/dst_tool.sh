#!/bin/bash

# =========================================================
# Wagstaff-Lab Control Center v6.1
# 模块化 DST 服务器管理脚本
# =========================================================

# --- 1. 环境初始化 ---

# 获取脚本所在目录的绝对路径 (bin/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# 定位项目根目录 (Wagstaff-Lab/)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
# 配置文件路径
CONFIG_FILE="$PROJECT_ROOT/conf/settings.ini"

# --- 2. 配置读取函数 (INI Parser) ---
# 用途：从 settings.ini 读取变量，并自动将 ~ 替换为 $HOME
read_config() {
    local section=$1
    local key=$2
    local val=$(awk -F ' = ' -v section="[$section]" -v key="$key" '
        $0 == section { in_section=1; next }
        /^\[/ { in_section=0 }
        in_section && $1 == key { print $2; exit }
    ' "$CONFIG_FILE")
    
    # 替换 ~ 为当前用户 Home 目录
    echo "${val/\~/$HOME}"
}

# --- 3. 加载变量 ---
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ 错误: 找不到配置文件 $CONFIG_FILE"
    exit 1
fi

DST_DIR=$(read_config "PATHS" "DST_ROOT")
STEAMCMD_DIR=$(read_config "PATHS" "STEAMCMD_DIR")
BACKUP_REPO=$(read_config "PATHS" "BACKUP_DIR")
CLUSTER_NAME=$(read_config "SERVER" "CLUSTER_NAME")
KLEI_HOME=$(read_config "SERVER" "KLEI_HOME")

# [关键修改] 启动脚本指向同目录下的 boot.sh
START_SCRIPT="$SCRIPT_DIR/boot.sh"

# 日志路径
LOG_MASTER="$KLEI_HOME/$CLUSTER_NAME/Master/server_log.txt"
LOG_CAVES="$KLEI_HOME/$CLUSTER_NAME/Caves/server_log.txt"

# 寻找 Conda Python 环境 (优先找 dst_lab)
PYTHON_EXEC="$HOME/miniconda3/envs/dst_lab/bin/python"
if [ ! -f "$PYTHON_EXEC" ]; then
    # 备用：尝试系统 python3
    PYTHON_EXEC=$(which python3)
fi

# 确保备份目录存在
mkdir -p "$BACKUP_REPO"

# --- 颜色定义 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

trap 'echo -e "\n${YELLOW}>> 返回主菜单...${NC}"; sleep 0.5' SIGINT

# ================= 辅助函数 =================

print_line() { echo -e "${CYAN}----------------------------------------${NC}"; }
pause() { echo -e "\n${WHITE}按回车键继续...${NC}"; read -r; }

# [Security] 解析绝对路径（优先 realpath，缺失则用 python3）
resolve_path() {
    local p="$1"
    if command -v realpath >/dev/null 2>&1; then
        realpath -m "$p"
        return $?
    fi
    python3 - "$p" <<'PY'
import os, sys
try:
    print(os.path.realpath(os.path.expanduser(sys.argv[1])))
except:
    sys.exit(1)
PY
}

# [Security] 高危删除：仅允许删除 KLEI_HOME/CLUSTER_NAME 且做二次确认
safe_delete_cluster_dir() {
    local base="$KLEI_HOME"
    local cluster="$CLUSTER_NAME"
    local target="$base/$cluster"

    if [ -z "$base" ] || [ -z "$cluster" ]; then
        echo -e "${RED}❌ KLEI_HOME 或 CLUSTER_NAME 为空，拒绝删除${NC}"
        return 1
    fi

    local base_real target_real
    base_real="$(resolve_path "$base")" || return 1
    target_real="$(resolve_path "$target")" || return 1

    # 护栏1: 目标不能是 /、HOME、KLEI_HOME 本身
    if [ "$target_real" = "/" ] || [ "$target_real" = "$HOME" ] || [ "$target_real" = "$base_real" ]; then
        echo -e "${RED}❌ 目标路径异常 (系统目录保护)，拒绝删除: $target_real${NC}"
        return 1
    fi

    # 护栏2: 目标必须严格位于 KLEI_HOME 目录树下
    case "$target_real" in
        "$base_real"/*) ;;
        *)
            echo -e "${RED}❌ 目标不在 KLEI_HOME 下 (越权保护)，拒绝删除${NC}"
            echo -e "   KLEI_HOME: $base_real"
            echo -e "   TARGET:    $target_real"
            return 1
            ;;
    esac

    if [ ! -d "$target_real" ]; then
        echo -e "${RED}❌ 存档目录不存在: $target_real${NC}"
        return 1
    fi

    echo -e "${YELLOW}🧹 警告：即将彻底删除旧存档目录:${NC}"
    echo -e "${RED}   $target_real${NC}"
    
    # 护栏3: 严格文本确认
    read -p "请输入以下内容确认删除: DELETE $target_real : " confirm_del
    if [ "$confirm_del" != "DELETE $target_real" ]; then
        echo -e "${YELLOW}🚫 输入不匹配，已取消删除操作${NC}"
        return 1
    fi

    echo -e "${RED}🔥 正在执行销毁...${NC}"
    rm -rf -- "$target_real"
    return 0
}


check_status() {
    local master_status="${RED}🔴 未运行${NC}"
    local caves_status="${RED}🔴 未运行${NC}"
    if screen -ls | grep -q "DST_Master"; then master_status="${GREEN}🟢 运行中${NC}"; fi
    if screen -ls | grep -q "DST_Caves"; then caves_status="${GREEN}🟢 运行中${NC}"; fi
    echo -e "   地面: $master_status    洞穴: $caves_status"
}

# 查看日志函数
view_log() {
    local logfile="$1"; local name="$2"
    if [ -f "$logfile" ]; then
        echo -e "${CYAN}📺 监视 $name 日志 (Ctrl+C 退出)${NC}"
        tail -f "$logfile"
    else
        echo -e "${RED}❌ 无日志文件: $logfile${NC}"; pause
    fi
}

# 发送指令的核心函数
send_cmd_to_master() {
    local cmd="$1"
    local desc="$2"
    if ! screen -ls | grep -q "DST_Master"; then
        echo -e "${RED}❌ 地面服未运行${NC}"; pause; return
    fi
    echo -e "${BLUE}📡 $desc${NC}"
    screen -S "DST_Master" -p 0 -X eval "stuff \"$cmd\015\""
    echo -e "${YELLOW}⏳ 指令已发送${NC}"; sleep 1
}

# ================= 核心功能模块 =================

start_server() {
    print_line
    if screen -ls | grep -q "DST_Master"; then
        echo -e "${YELLOW}⚠️  服务器已在运行！${NC}"; pause; return
    fi
    echo -e "${GREEN}🚀 调用启动引导程序 (Bootloader)...${NC}"
    
    # 检查启动脚本是否存在
    if [ -f "$START_SCRIPT" ]; then
        # 执行 boot.sh
        "$START_SCRIPT"
    else
        echo -e "${RED}❌ 找不到启动器: $START_SCRIPT${NC}"
        echo "请检查 bin/boot.sh 是否存在。"
    fi
    pause
}

graceful_stop() {
    print_line
    echo -e "${YELLOW}🛑 发送停服信号...${NC}"
    if ! screen -ls | grep -qE "DST_Master|DST_Caves"; then
        echo -e "${RED}⚠️  服务器未运行${NC}"; pause; return
    fi

    # 发送关闭指令
    for target in "DST_Master" "DST_Caves"; do
        if screen -list | grep -q "$target"; then
            screen -S "$target" -p 0 -X eval 'stuff "c_shutdown(true)\015"'
        fi
    done

    echo -e "${BLUE}⏳ 等待存档保存 (最多40秒)...${NC}"
    for ((i=1; i<=40; i++)); do
        if ! screen -list | grep -qE "DST_Master|DST_Caves"; then
            echo -e "\n${GREEN}✅ 服务器已关闭${NC}"; pause; return
        fi
        if tail -n 10 "$LOG_MASTER" 2>/dev/null | grep -q "Shutting down"; then
            echo -e "\n${GREEN}✅ 监测到关机信号${NC}"; break
        fi
        echo -n "."; sleep 0.5
    done
    
    # 清理残余进程
    screen -list | grep -E "DST_Master|DST_Caves" | cut -d. -f1 | xargs -r -I{} screen -S {} -X quit
    echo -e "\n${GREEN}✅ 进程已终止${NC}"; pause
}

restart_server() {
    print_line
    if screen -ls | grep -qE "DST_Master|DST_Caves"; then
        original_pause_def="$(declare -f pause)"; pause() { :; } 
        graceful_stop
        eval "$original_pause_def"
    fi
    read -p "是否顺便更新游戏? (y/n): " up_c
    if [[ "$up_c" == "y" ]]; then update_game; fi
    start_server
}

update_game() {
    print_line
    echo -e "${BLUE}⬇️  调用 SteamCMD 更新...${NC}"
    "$STEAMCMD_DIR/steamcmd.sh" +force_install_dir "$DST_DIR" +login anonymous +app_update 343050 validate +quit
    echo -e "${GREEN}✅ 更新完成${NC}"; pause
}

# --- 备份/恢复系统 ---
create_backup() {
    print_line
    local ts=$(date +"%Y%m%d_%H%M%S")
    if [ ! -d "$KLEI_HOME/$CLUSTER_NAME" ]; then echo -e "${RED}❌ 存档不存在: $KLEI_HOME/$CLUSTER_NAME${NC}"; pause; return; fi
    
    echo -e "${CYAN}💾 打包存档: $CLUSTER_NAME ...${NC}"
    tar -zcf "$BACKUP_REPO/backup_${ts}.tar.gz" -C "$KLEI_HOME" "$CLUSTER_NAME"
    echo -e "${GREEN}✅ 备份已创建: backup_${ts}.tar.gz${NC}"; pause
}

restore_backup() {
    print_line
    files=($(ls -1t "$BACKUP_REPO"/*.tar.gz 2>/dev/null))
    if [ ${#files[@]} -eq 0 ]; then echo -e "${RED}❌ 备份库为空${NC}"; pause; return; fi

    echo -e "${CYAN}📂 最近备份:${NC}"
    i=0
    for file in "${files[@]}"; do
        echo -e " [$i] $(basename "$file")"
        ((i++)); if [ $i -ge 10 ]; then break; fi
    done
    
    read -p "选择序号 (q退出): " c
    if [[ "$c" == "q" ]]; then return; fi
    if ! [[ "$c" =~ ^[0-9]+$ ]] || [ "$c" -ge "$i" ]; then echo "❌ 无效"; pause; return; fi

    read -p "⚠️  高危操作: 确认覆盖当前存档? (YES/n): " confirm
    if [[ "$confirm" != "YES" ]]; then return; fi

    # 自动停服
    if screen -ls | grep -qE "DST_Master|DST_Caves"; then
        original_pause_def="$(declare -f pause)"; pause() { :; } 
        graceful_stop
        eval "$original_pause_def"
    fi

    echo -e "${YELLOW}🧹 准备清理旧存档...${NC}"
    if ! safe_delete_cluster_dir; then
        echo -e "${RED}❌ 删除步骤失败或被取消，已中止回档流程${NC}"
        pause
        return
    fi
    echo -e "${BLUE}📦 解压备份...${NC}"
    tar -zxf "${files[$c]}" -C "$KLEI_HOME"
    echo -e "${GREEN}✅ 回档成功${NC}"
    read -p "立即启动? (y/n): " sn
    if [[ "$sn" == "y" ]]; then start_server; else pause; fi
}

# --- Wagstaff 工具箱集成 ---
run_explorer() {
    local script_path="$PROJECT_ROOT/apps/cli/explorer.py"
    if [ -f "$script_path" ]; then
        "$PYTHON_EXEC" "$script_path"
    else
        echo -e "${RED}❌ 找不到工具脚本: $script_path${NC}"
        pause
    fi
}

run_wiki() {
    local script_path="$PROJECT_ROOT/apps/cli/wiki.py"
    if [ ! -f "$script_path" ]; then
        echo -e "${RED}❌ 找不到 Wiki 脚本: $script_path${NC}"; pause; return
    fi

    echo -e "${CYAN}📚 请输入物品代码进行查询 (例如 spear, log, meat)${NC}"
    read -p "物品代码: " item_code
    if [ -n "$item_code" ]; then
        "$PYTHON_EXEC" "$script_path" "$item_code"
    fi
    pause
}
console_menu() {
    while true; do
        clear
        echo -e "   🎮 ${CYAN}控制台指令中心${NC} 🎮"
        check_status
        echo "--------------------------------"
        echo "1. 💾 立即保存 (c_save)"
        echo "2. ⏪ 回滚1天 (c_rollback)"
        echo "3. 📢 发送公告 (c_announce)"
        echo "4. ☠️  重置世界 (c_regenerateworld)"
        echo "5. 👥 列出玩家"
        echo "0. 🔙 返回"
        echo "--------------------------------"
        read -p "指令: " cc
        case $cc in
            1) send_cmd_to_master "c_save()" "立即保存" ;;
            2) send_cmd_to_master "c_rollback(1)" "回滚1天" ;;
            3) read -p "内容: " m; send_cmd_to_master "c_announce(\"$m\")" "公告" ;;
            4) read -p "输入 YES 确认重置: " r; [[ "$r" == "YES" ]] && send_cmd_to_master "c_regenerateworld()" "重置世界" ;;
            5) send_cmd_to_master "c_listallplayers()" "玩家列表" ;;
            0) return ;;
        esac
    done
}

# ================= 主循环 =================
while true; do
    clear
    echo "==========================================="
    echo -e " 🦅 ${CYAN}Wagstaff-Lab 控制台 v6.1${NC} 🦅"
    echo "==========================================="
    check_status
    echo -e "${CYAN}--- 运维管理 ---${NC}"
    echo "1. 🚀 启动服务器      2. 🛑 停止服务器"
    echo "3. 🔄 重启服务器      4. ⬇️  更新版本"
    echo -e "${CYAN}--- 数据与工具 ---${NC}"
    echo "5. 💾 创建备份        6. ⏪ 恢复存档"
    echo "7. 📜 查看日志        8. 🎮 发送指令"
    echo -e "9. 🔬 ${YELLOW}源码透视镜 (Explorer)${NC}"
    echo -e "10.📚 ${GREEN}Wagstaff 百科 (Wiki)${NC}"
    echo "0. 🚪 退出"
    echo "==========================================="
    
    read -p "选项: " choice

    case $choice in
        1) start_server ;;
        2) graceful_stop ;;
        3) restart_server ;;
        4) update_game ;;
        5) create_backup ;;
        6) restore_backup ;;
        7) view_log "$LOG_MASTER" "Master" ;; 
        8) console_menu ;;
        9) run_explorer ;; 
	10) run_wiki ;;
        0) echo -e "${GREEN}再见，研究员。${NC}"; exit 0 ;;
        *) echo "无效"; sleep 0.5 ;;
    esac
done
