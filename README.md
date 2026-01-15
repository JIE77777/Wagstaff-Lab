# 🧪 Wagstaff-Lab (v3.0)

**Wagstaff-Lab** 是一个专为《饥荒联机版》(Don't Starve Together) 设计的服务器运维、源码分析与项目管理工具集。它采用“注册表驱动”架构，实现了从底层数据解析到高层 UI 展示的全自动化管理。

## 🌟 核心理念 (Manifesto)

本项目的开发严格遵循以下宗旨：
* **分层清晰**：`core/` 负责解析与索引，`apps/` 承载 UI/服务，`devtools/` 提供流程工具。
* **单向依赖**：上层 (`apps/`、`devtools/`) 可以依赖 `core/`，`core/` 不依赖上层。
* **数据契约**：对外展示只依赖 `data/` 下的版本化产物，不直接读取原始脚本。
* **路径自适应**：禁止硬编码绝对路径，统一通过 `__file__` 推导项目根目录。
* **可追溯**：索引与报告必须携带来源元信息（scripts hash / schema_version）。
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
| `wagstaff snap` | `snap` | **快照**：生成 LLM 友好代码快照 |

## 🏗️ 新工具开发 SOP (v3.0 标准)

若要在实验室中纳入新工具，请遵循以下流程：

1.  **开发 (Develop)**：在 `core/`、`apps/` 或 `devtools/` 目录下编写您的 Python 脚本。
2.  **注册 (Register)**：在 `apps/cli/registry.py` 的 `TOOLS` 列表中添加该工具的元数据。
3.  **同步 (Apply)**：运行 `wagstaff install` (或 `python3 devtools/installer.py`)。
4.  **记录 (Log)**：使用 `pm ui` 记录您的开发日志。

## 🧭 开发规范与约定 (v3.0)

- **代码落点**：`core/` 只放领域解析与索引；`apps/cli` 放交互命令；`apps/webcraft` 放 API+UI；`devtools/` 放构建/清理/报告。
- **导入约定**：入口脚本负责挂载 `core/`（必要时 `apps/`）到 `sys.path`；核心模块不得自行修改 `sys.path`。
- **数据产物**：全部落盘到 `data/`，并带版本后缀（例如 `wagstaff_catalog_v1.json`）。
- **WebCraft**：UI 只通过 API 读取数据；API 不绕过索引产物直读脚本。
- **变更同步**：重要重构必须同步更新 `README.md`、`PROJECT_STATUS.json` 与相关文档。
- 详细规范与路线图：`docs/DEV_GUIDE.md`、`docs/ROADMAP.md`。

## 📁 目录结构

```text
├── bin/                # 自动化生成的命令行包装器
├── core/               # 业务核心代码 (Engine, Analyzer, Catalog)
├── apps/               # 应用层
│   ├── cli/            # CLI 工具 (guide/wiki/explorer/doctor)
│   └── webcraft/       # WebCraft 服务 (FastAPI)
├── devtools/           # 开发运维工具 (PM, Snap, Reporter, Installer)
├── conf/               # 配置文件 (settings.ini)
├── docs/               # 设计/约定/架构文档
├── data/               # 持久化数据与报告
└── PROJECT_STATUS.json # 项目进度与宗旨数据库
```
