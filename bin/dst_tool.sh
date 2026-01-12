#!/bin/bash

# ================= 配置区域 =================
DST_DIR="$HOME/dontstarvetogether_dedicated_server"
STEAMCMD_DIR="$HOME/steamcmd"
KLEI_DIR="$HOME/.klei/DoNotStarveTogether"
SAVE_DIR_NAME="MyDediServer"
BACKUP_REPO="$HOME/dst_backups"
START_SCRIPT="$HOME/start.sh"
LOG_MASTER="$KLEI_DIR/$SAVE_DIR_NAME/Master/server_log.txt"
LOG_CAVES="$KLEI_DIR/$SAVE_DIR_NAME/Caves/server_log.txt"
# ===========================================

# --- 颜色定义 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

mkdir -p "$BACKUP_REPO"
trap 'echo -e "\n${YELLOW}>> 操作已取消，返回菜单...${NC}"; sleep 1' SIGINT

# ================= 辅助函数 =================

print_line() { echo -e "${CYAN}----------------------------------------${NC}"; }

check_status() {
    local master_status="${RED}🔴 未运行${NC}"
    local caves_status="${RED}🔴 未运行${NC}"
    if screen -ls | grep -q "DST_Master"; then master_status="${GREEN}🟢 运行中${NC}"; fi
    if screen -ls | grep -q "DST_Caves"; then caves_status="${GREEN}🟢 运行中${NC}"; fi
    echo -e "   地面: $master_status    洞穴: $caves_status"
}

pause() { echo -e "\n${WHITE}按回车键返回...${NC}"; read -r; }

# 发送指令的核心函数 (带日志回显)
send_cmd_to_master() {
    local cmd="$1"
    local desc="$2"
    
    if ! screen -ls | grep -q "DST_Master"; then
        echo -e "${RED}❌ 地面服务器未运行，无法发送指令。${NC}"
        pause
        return
    fi

    echo -e "${BLUE}📡 发送指令: $desc${NC}"
    # 使用 eval ... \015 确保 100% 触发回车
    screen -S "DST_Master" -p 0 -X eval "stuff \"$cmd\015\""
    
    echo -e "${YELLOW}⏳ 等待服务器响应...${NC}"
    sleep 1 # 稍等一下让日志刷新
    
    echo -e "${CYAN}📋 --- 最近 3 条日志反馈 ---${NC}"
    tail -n 3 "$LOG_MASTER"
    echo -e "${CYAN}-----------------------------${NC}"
    pause
}

# ================= 核心功能 =================

start_server() {
    print_line
    if screen -ls | grep -q "DST_Master"; then
        echo -e "${YELLOW}⚠️  服务器已在运行中！${NC}"; pause; return
    fi
    echo -e "${GREEN}🚀 启动服务器...${NC}"
    if [ -f "$START_SCRIPT" ]; then
        cd "$HOME" || exit; "$START_SCRIPT"
    else
        echo -e "${RED}❌ 找不到启动脚本${NC}"; pause; return
    fi
    echo -e "${GREEN}✅ 启动指令已发送。${NC}"; pause
}

# 优雅停止 (集成日志监控)
graceful_stop() {
    print_line
    echo -e "${YELLOW}🛑 正在停止服务器...${NC}"
    if ! screen -ls | grep -qE "DST_Master|DST_Caves"; then
        echo -e "${RED}⚠️  服务器未运行。${NC}"; pause; return
    fi

    # 发送关闭指令
    for target in "DST_Master" "DST_Caves"; do
        if screen -list | grep -q "$target"; then
            screen -S "$target" -p 0 -X eval 'stuff "c_shutdown(true)\015"'
        fi
    done

    echo -e "${BLUE}⏳ 监控存档状态...${NC}"
    for ((i=1; i<=40; i++)); do
        if ! screen -list | grep -qE "DST_Master|DST_Caves"; then
            echo -e "\n${GREEN}✅ 服务器已正常关闭${NC}"; pause; return
        fi
        # 监控日志中的 Shutting down 信号
        if tail -n 10 "$LOG_MASTER" 2>/dev/null | grep -q "Shutting down"; then
            echo -e "\n${GREEN}✅ 存档完毕 (Shutting down)${NC}"
            break
        fi
        echo -n "."; sleep 0.5
    done

    # 强制清理
    screen -list | grep -E "DST_Master|DST_Caves" | cut -d. -f1 | xargs -r -I{} screen -S {} -X quit
    echo -e "\n${GREEN}✅ 服务器已完全停止。${NC}"; pause
}

restart_server() {
    print_line
    if screen -ls | grep -qE "DST_Master|DST_Caves"; then
        # 临时覆盖 pause 以实现自动流转
        eval "original_pause_def=$(declare -f pause)"; pause() { :; } 
        graceful_stop
        eval "$original_pause_def"
    fi
    echo ""; read -p "是否更新游戏? (y/n): " up_c
    if [[ "$up_c" == "y" ]]; then update_game; fi
    start_server
}

update_game() {
    print_line
    echo -e "${BLUE}⬇️  SteamCMD 更新中...${NC}"
    $STEAMCMD_DIR/steamcmd.sh +force_install_dir "$DST_DIR" +login anonymous +app_update 343050 validate +quit
    echo -e "${GREEN}✅ 更新结束。${NC}"; pause
}

view_log() {
    local logfile="$1"; local name="$2"
    if [ -f "$logfile" ]; then
        echo -e "${CYAN}📺 监视 $name 日志 (Ctrl+C 退出)${NC}"
        tail -f "$logfile"
    else
        echo -e "${RED}❌ 无日志文件${NC}"; pause
    fi
}

create_backup() {
    print_line
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    if [ ! -d "$KLEI_DIR/$SAVE_DIR_NAME" ]; then echo -e "${RED}❌ 无存档${NC}"; pause; return; fi
    echo -e "${CYAN}💾 正在备份...${NC}"
    tar -zcf "$BACKUP_REPO/backup_${TIMESTAMP}.tar.gz" -C "$KLEI_DIR" "$SAVE_DIR_NAME"
    echo -e "${GREEN}✅ 备份完成: backup_${TIMESTAMP}.tar.gz${NC}"; pause
}

restore_backup() {
    print_line
    files=($(ls -1t "$BACKUP_REPO"/*.tar.gz 2>/dev/null))
    if [ ${#files[@]} -eq 0 ]; then echo -e "${RED}❌ 无备份${NC}"; pause; return; fi

    echo -e "${CYAN}📂 备份列表:${NC}"
    i=0
    for file in "${files[@]}"; do
        echo -e " [$i] $(basename "$file")"
        ((i++)); if [ $i -ge 10 ]; then break; fi
    done
    
    read -p "序号 (q退出): " c
    if [[ "$c" == "q" ]]; then return; fi
    if ! [[ "$c" =~ ^[0-9]+$ ]] || [ "$c" -ge "$i" ]; then echo "❌ 无效"; pause; return; fi

    read -p "🔴 确认覆盖当前存档? (y/n): " confirm
    if [[ "$confirm" != "y" ]]; then return; fi

    if screen -ls | grep -qE "DST_Master|DST_Caves"; then
        eval "original_pause_def=$(declare -f pause)"; pause() { :; } 
        graceful_stop
        eval "$original_pause_def"
    fi

    rm -rf "$KLEI_DIR/$SAVE_DIR_NAME"
    tar -zxf "${files[$c]}" -C "$KLEI_DIR"
    echo -e "${GREEN}✅ 回档完成${NC}"
    read -p "立即启动? (y/n): " sn
    if [[ "$sn" == "y" ]]; then start_server; else pause; fi
}

# === 新功能：指令发送菜单 ===
console_menu() {
    while true; do
        clear
        echo "========================================"
        echo -e "   🎮 ${CYAN}发送控制台指令${NC} 🎮"
        echo "========================================"
        check_status
        print_line
        echo "1. 💾 立即保存 (c_save)"
        echo "2. ⏪ 回滚1天 (c_rollback(1))"
        echo "3. ⏪ 回滚指定天数..."
        echo "4. 📢 发送全服公告 (c_announce)"
        echo -e "5. ☠️  ${RED}重置世界 (c_regenerateworld)${NC}"
        echo "6. 👥 列出玩家 (c_listallplayers)"
        print_line
        echo "9. ⌨️  输入自定义 Lua 代码"
        echo "0. 🔙 返回主菜单"
        echo "========================================"
        read -p "选择指令: " cmd_choice

        case $cmd_choice in
            1) send_cmd_to_master "c_save()" "立即保存" ;;
            2) send_cmd_to_master "c_rollback(1)" "回滚 1 天" ;;
            3) 
                read -p "输入回滚天数 (数字): " days
                if [[ "$days" =~ ^[0-9]+$ ]]; then
                    send_cmd_to_master "c_rollback($days)" "回滚 $days 天"
                fi
                ;;
            4)
                read -p "输入公告内容: " msg
                # 自动包裹引号
                send_cmd_to_master "c_announce(\"$msg\")" "发送公告: $msg"
                ;;
            5)
                echo -e "${RED}⚠️  警告：这将删除当前存档并生成新地图！${NC}"
                read -p "输入 YES 确认重置: " confirm_regen
                if [[ "$confirm_regen" == "YES" ]]; then
                    send_cmd_to_master "c_regenerateworld()" "重置世界"
                else
                    echo "操作取消。"
                    sleep 1
                fi
                ;;
            6) send_cmd_to_master "c_listallplayers()" "列出玩家" ;;
            9)
                echo -e "${YELLOW}👉 输入完整 Lua 命令 (例如 c_godmode())${NC}"
                read -p "命令: " user_cmd
                if [ ! -z "$user_cmd" ]; then
                    send_cmd_to_master "$user_cmd" "自定义: $user_cmd"
                fi
                ;;
            0) return ;;
            *) echo "无效选项"; sleep 0.5 ;;
        esac
    done
}

# ================= 主菜单循环 =================
while true; do
    clear
    echo "========================================"
    echo -e "   🦁 ${CYAN}饥荒联机版 (DST) 管理面板 v5.0${NC} 🦁"
    echo "========================================"
    check_status
    print_line
    echo "1. 🚀 启动服务器"
    echo "2. 🛑 停止服务器"
    echo "3. 🔄 重启服务器"
    echo "4. ⬇️  更新游戏版本"
    print_line
    echo -e "5. 🎮 ${YELLOW}发送控制台指令 (安全模式)${NC}"
    echo "6. 📜 查看地面日志"
    echo "7. 📜 查看洞穴日志"
    print_line
    echo "8. 💾 创建备份"
    echo "9. ⏪ 恢复存档"
    echo "0. 🚪 退出脚本"
    echo "========================================"
    
    read -p "请输入选项: " choice

    case $choice in
        1) start_server ;;
        2) graceful_stop ;;
        3) restart_server ;;
        4) update_game ;;
        5) console_menu ;; # 进入子菜单
        6) view_log "$LOG_MASTER" "地面" ;;
        7) view_log "$LOG_CAVES" "洞穴" ;;
        8) create_backup ;;
        9) restore_backup ;;
        0) echo -e "${GREEN}👋 拜拜！${NC}"; exit 0 ;;
        *) echo -e "${RED}❌ 无效选项${NC}"; sleep 0.5 ;;
    esac
done