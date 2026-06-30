# TCAI v6 使用教程

## 快速上手

1. 双击 `Start.bat` 启动
2. 输入故障描述（如：`英雄联盟崩溃报错 3A`）
3. TCAI 自动诊断并给出方案

## 文件说明

### 启动与安装
| 文件 | 说明 |
|------|------|
| `Start.bat` | 启动脚本，自动找 Python、加载配置、启动 Agent |
| `install.bat` | 安装脚本，安装依赖并创建 `home/.env` 配置模板 |
| `launcher.py` | 启动器，处理路径（内部使用，不直接运行） |

### 配置
| 文件 | 说明 |
|------|------|
| `.env.example` | 环境变量模板，复制到 `home/.env` 后填入 Key |
| `home/.env` | 你的配置文件（已 gitignore，不上传） |
| `pyproject.toml` | 项目元数据 + ruff/mypy/pytest 工具配置 |

### 文档
| 文件 | 说明 |
|------|------|
| `README.md` | 项目介绍和快速开始 |
| `ARCHITECTURE.md` | 完整系统架构文档 |
| `CODING_STANDARDS.md` | 编码规范（10 章，贡献者必读） |
| `CONTRIBUTING.md` | 贡献指南 |
| `CHANGELOG.md` | 版本变更记录 |
| `SECURITY.md` | 安全策略与漏洞报告 |
| `LICENSE` | AGPL v3 协议 |
| `AUTHORS` | 版权共有人 |

### 运行时
| 目录/文件 | 说明 |
|----------|------|
| `tools/python-venv/` | 捆绑的 Python 3.11 运行环境 |
| `records/` | 诊断记录（诊断结果、会话日志） |
| `work/` | 运行数据（审计日志 `audit.log`、快照） |
| `home/` | 用户配置目录 |
| `tests/` | 测试套件 |

## 命令

| 命令 | 说明 |
|------|------|
| 直接输入问题 | 开始诊断（如 `显卡驱动崩溃`） |
| `/help` | 显示帮助 |
| `/new` | 开始新会话（重置上下文） |
| `/machine <机号>` | 设置当前诊断机器编号 |
| `/learn <路径>` | 从会话日志提取知识到知识库 |
| `/exit` | 退出 |

## 配置

编辑 `home/.env`：

```
DEEPSEEK_API_KEY=sk-你的密钥
# 可选:
# TCAI_MODEL=deepseek-v4-pro
# TCAI_KNOWLEDGE_PATH=E:\你的知识库目录
```

## 知识库

### 格式
Markdown + YAML 头：

```markdown
---
title: 英雄联盟 3A 错误
game: 英雄联盟
category: game_issues
tags: [崩溃, 启动]
---

## 症状
游戏启动时弹出 3A 错误

## 原因
反作弊驱动冲突

## 方案
1. 关闭其他游戏
2. 重启电脑
3. 如果持续出现，运行 anti_cheat_check 检查冲突
```

### 目录结构
```
TCAI_Knowledge/
├── 游戏故障/
│   ├── 英雄联盟/
│   │   └── 错误码3A.md
│   └── ...
├── 系统故障/
├── 网络故障/
├── 外设故障/
├── 软件平台/
├── 参考知识/
└── 模板/
```

任何子目录下 `.md` 文件都会被索引。用 `/learn` 命令从诊断日志自动提取知识。

## 安全

TCAI 有 7 层安全防御，外部内容（网页、知识库）被标记为纯数据，不能覆盖系统指令。写操作（修改文件、注册表、服务）需要经过完整安全流水线。

详见 `README.md` 架构图和 `SECURITY.md`。
