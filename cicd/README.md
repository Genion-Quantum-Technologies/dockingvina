# Docking Vina CI/CD 文档和脚本

这个目录包含了Docking Vina服务的所有CI/CD相关文件，包括部署脚本和相关文档。

## 📂 目录结构

```
cicd/
├── scripts/                    # 部署和管理脚本
│   ├── deploy.sh              # 主部署脚本
│   └── start_dockingvina_service.sh  # 服务管理脚本
└── docs/                      # 文档
    └── DEPLOYMENT_GUIDE.md    # 部署指南
```

## 🚀 快速开始

### 方式一：使用快捷脚本（推荐）

在项目根目录下，可以直接使用快捷脚本：

```bash
# 部署管理
./deploy start          # 启动服务
./deploy stop           # 停止服务
./deploy status         # 查看状态
./deploy logs           # 查看日志

# 服务管理
./service start         # 启动Docking Vina服务
./service stop          # 停止服务
./service status        # 查看服务状态
```

### 方式二：直接使用CI/CD脚本

```bash
# 进入脚本目录
cd cicd/scripts/

# 完整部署
./deploy.sh start
```

## 📋 脚本功能说明

### 核心脚本

| 脚本 | 功能 | 用途 |
|------|------|------|
| `deploy.sh` | 主部署脚本 | 统一管理服务的部署 |
| `start_dockingvina_service.sh` | 服务管理 | 管理Docking Vina API服务 |

### 配置脚本

| 脚本 | 功能 | 用途 |
|------|------|------|
| `deploy` | 部署快捷入口 | 在项目根目录快速访问部署功能 |
| `service` | 服务快捷入口 | 在项目根目录快速管理服务 |

## 🔧 配置说明

### 环境变量

主要配置在脚本中定义：

```bash
# 项目路径
PROJECT_DIR="/home/davis/projects/genion_quantum/dockingvina"

# 服务配置
CONDA_ENV_NAME="dockingvina_final"
SERVICE_PORT=8002

# 日志配置
LOG_DIR="/home/davis/projects/serverlogs"
```

### 部署流程

1. **环境检查**: `./deploy check`
2. **启动服务**: `./deploy start`
3. **验证部署**: `./deploy status` 和 `./deploy test`

## 📖 详细文档

更详细的部署说明请参考：[部署指南](docs/DEPLOYMENT_GUIDE.md)

## 🐛 故障排除

### 常见问题

1. **权限问题**: 确保所有脚本有执行权限
   ```bash
   chmod +x cicd/scripts/*.sh
   ```

2. **路径问题**: 脚本已配置相对路径，可在项目任意位置运行

3. **服务状态**: 使用 `./deploy status` 查看服务状态

### 日志位置

- Docking Vina服务: `/home/davis/projects/serverlogs/dockingvina.log`

## 🔄 更新记录

- 基于peptide_opt架构创建
- 简化部署配置（仅本地服务）
- 使用端口8002
- 统一日志管理

---

*最后更新: 2025年9月*
