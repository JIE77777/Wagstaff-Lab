# 🧪 Wagstaff-Lab (v2.2)

**Wagstaff-Lab** 是一个专为《饥荒联机版》(Don't Starve Together) 设计的服务器运维、源码分析与项目管理工具集。它采用“注册表驱动”架构，实现了从底层数据解析到高层 UI 展示的全自动化管理。

## 🌟 核心理念 (Manifesto)

本项目的开发严格遵循以下宗旨：
* **架构分层**：`Engine` 负责底层 I/O 与数据解析，`Tool` 负责业务逻辑与交互。
* **单文件可用**：每个脚本必须保持原子化，能够独立运行。
* **路径自适应**：禁止硬编码绝对路径，所有路径均通过 `__file__` 动态推算。
* **数据持久化**：所有扫描结果与日志必须落盘保存。
* **稳健降级**：优先读取 `scripts.zip`，失败时自动降级为文件夹模式。

## 🚀 快速开始

### 1. 环境准备
确保您的系统已安装 **Conda**，并创建了名为 `dst_lab` 的 Python 3.10+ 环境。

### 2. 初始化项目
在拉取代码后，运行一键初始化脚本：
```bash
./setup.sh
```
该脚本会自动：
* 修复脚本执行权限。
* 自动激活 `dst_lab` 环境。
* 将项目工具路径注册到您的系统环境变量（`.bashrc` 或 `.profile`）。

### 3. 生效配置
```bash
source ~/.bashrc
```

## 🛠️ 工具箱说明书

您可以通过输入 `Wagstaff-Lab` 呼出主控制面板。

| 命令 | 别名 | 功能说明 |
| :--- | :--- | :--- |
| `Wagstaff-Lab` | - | **主入口**：查看项目概况与工具清单 |
| `pm` | - | **项目管理**：交互式管理任务进度 |
| `wagstaff wiki` | `wiki` | **百科**：查阅物品配方与数值 |
| `wagstaff exp` | `exp` | **透视**：分析 Prefab 结构与逻辑 |
| `wagstaff report` | `report` | **情报**：生成资产与配方报告 |
| `wagstaff snap` | `snap` | **快照**：生成项目全息代码快照 |

## 🏗️ 新工具开发 SOP (v2.2 标准)

若要在实验室中纳入新工具，请遵循以下流程：

1.  **开发 (Develop)**：在 `src/` 或 `devtools/` 目录下编写您的 Python 脚本。
2.  **注册 (Register)**：在 `src/registry.py` 的 `TOOLS` 列表中添加该工具的元数据。
3.  **同步 (Apply)**：运行 `wagstaff install` (或 `python3 devtools/installer.py`)。
4.  **记录 (Log)**：使用 `pm ui` 记录您的开发日志。

## 📁 目录结构

```text
├── bin/                # 自动化生成的命令行包装器
├── src/                # 业务核心代码 (Engine, Wiki, Explorer, Registry)
├── devtools/           # 开发运维工具 (PM, Snap, Reporter, Installer)
├── conf/               # 配置文件 (settings.ini)
├── data/               # 持久化数据与报告
└── PROJECT_STATUS.json # 项目进度与宗旨数据库
```