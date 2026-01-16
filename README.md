# DockingVina

基于 AutoDock Vina 的分子对接服务，提供 FastAPI REST API 接口，支持数据库任务管理和 BINANA 结合分析。

## 功能特点

- **数据库驱动**: 从 PostgreSQL 数据库 tasks 表获取待处理的 docking 任务
- **异步处理**: 使用 FastAPI + asyncio 实现高效的异步任务处理
- **对象存储**: 集成 SeaweedFS 进行文件存储管理
- **BINANA 分析**: 自动分析对接结果的结合模式和相互作用
- **现代项目结构**: 遵循 Python 项目最佳实践 (src-layout, pyproject.toml)

## 项目结构

```
dockingvina/
├── pyproject.toml              # 项目配置和依赖管理
├── README.md                   # 项目文档
├── .env.example               # 环境变量示例
│
├── src/
│   └── dockingvina/           # 主包 (src-layout)
│       ├── __init__.py        # 包初始化
│       ├── __main__.py        # CLI 入口点
│       ├── app.py             # FastAPI 应用
│       │
│       ├── core/              # 核心业务逻辑
│       │   ├── task_processor.py    # 任务处理器
│       │   ├── async_processor.py   # 异步任务处理
│       │   └── vina_workflow.py     # Vina 工作流
│       │
│       ├── config/            # 配置模块
│       │   ├── settings.py    # 应用配置
│       │   ├── storage.py     # 存储配置
│       │   └── logging_config.py
│       │
│       ├── database/          # 数据库模块
│       │   ├── config.py      # 数据库配置
│       │   └── db.py          # 连接池管理
│       │
│       ├── services/          # 外部服务集成
│       │   └── storage/       # SeaweedFS 存储
│       │
│       ├── analysis/          # BINANA 分析模块
│       │
│       └── models/            # 数据模型
│
├── tests/                     # 测试套件
│   ├── conftest.py           # Pytest fixtures
│   ├── test_app.py           # API 测试
│   ├── test_task_processor.py
│   └── test_storage.py
│
├── Vina/                      # Vina 工作流实现 (legacy)
├── analysis/                  # BINANA 分析实现 (legacy)
├── vendor/                    # 第三方代码
│   └── gypsum_dl/            # Gypsum-DL 分子准备
│
├── docker/                    # Docker 配置
├── scripts/                   # 部署脚本
├── docs/                      # 文档
└── resource/                  # 资源文件
```

## 快速开始

### 安装

#### 使用 pip (推荐用于开发)

```bash
# 克隆仓库
git clone <repository-url>
cd dockingvina

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装为可编辑模式
pip install -e ".[dev]"
```

#### 使用 Conda (推荐用于科学计算依赖)

```bash
# 创建 conda 环境
conda env create -f env.yml
conda activate dockingvina

# 安装包
pip install -e .
```

### 配置

1. 复制环境变量模板：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件配置：
```env
# 数据库配置
DB_HOST=127.0.0.1
DB_PORT=5432
DB_USER=admin
DB_PASSWORD=secret
DB_NAME=mydatabase

# SeaweedFS 配置
SEAWEED_FILER_ENDPOINT=http://localhost:8888
SEAWEED_BUCKET=astramolecula

# 任务配置
MAX_CONCURRENT_TASKS=3
DOCKING_NUM_CPU=8
```

### 运行

#### 方式 1: 使用命令行

```bash
# 基本启动
dockingvina

# 指定参数
dockingvina --host 0.0.0.0 --port 8002 --log-level debug

# 开发模式 (热重载)
dockingvina --reload
```

#### 方式 2: 作为 Python 模块

```bash
python -m dockingvina --host 0.0.0.0 --port 8002
```

#### 方式 3: 直接运行应用

```bash
uvicorn dockingvina.app:app --host 0.0.0.0 --port 8002
```

## API 接口

### 基础端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/` | GET | API 根路径，返回服务状态 |
| `/health` | GET | 健康检查 |
| `/status` | GET | 获取服务详细状态 |
| `/docs` | GET | Swagger API 文档 |
| `/redoc` | GET | ReDoc API 文档 |

### 分析端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/analyze_binding` | POST | 分析受体-配体结合模式 |
| `/analyze_docking_results/{task_id}` | GET | 分析对接任务的所有结果 |
| `/binding_analysis_summary/{task_id}` | GET | 获取结合分析摘要 |

## 数据库任务格式

### 任务表结构
```sql
SELECT id, user_id, task_type, job_dir, status 
FROM tasks 
WHERE status = 'pending' AND task_type = 'docking'
```

### 输入配置文件 (`input.json`)
```json
{
    "ligands": [
        {"smiles": "CCO", "title": "ethanol"},
        {"smiles": "CC(=O)O", "title": "acetic_acid"}
    ],
    "receptor_pdbqt": "receptor.pdbqt",
    "center_x": 0.0,
    "center_y": 0.0,
    "center_z": 0.0,
    "box_size_x": 20.0,
    "box_size_y": 20.0,
    "box_size_z": 20.0,
    "exhaustiveness": 8,
    "n_poses": 10
}
```

## 开发

### 运行测试

```bash
# 运行所有测试
pytest

# 带覆盖率报告
pytest --cov=src/dockingvina --cov-report=html

# 运行特定测试
pytest tests/test_app.py -v
```

### 代码格式化

```bash
# 格式化代码
black src tests
isort src tests

# 检查代码质量
ruff check src tests
mypy src
```

### 构建包

```bash
# 构建 wheel 和 sdist
python -m build

# 安装构建的包
pip install dist/dockingvina-1.0.0-py3-none-any.whl
```

## Docker 部署

```bash
# 构建镜像
docker build -t dockingvina:latest -f docker/Dockerfile .

# 运行容器
docker run -d \
  --name dockingvina \
  -p 8002:8002 \
  -e DB_HOST=host.docker.internal \
  -e SEAWEED_FILER_ENDPOINT=http://host.docker.internal:8888 \
  dockingvina:latest
```

## 工作流程

1. **任务监控**: 应用每3分钟查询数据库中状态为 `pending` 的 `docking` 任务
2. **任务处理**: 
   - 从 SeaweedFS 下载输入文件
   - 验证配置并准备分子
   - 执行 SMILES → PDBQT 转换 (Gypsum-DL)
   - 运行 AutoDock Vina 对接
   - 执行 BINANA 结合分析 (可选)
   - 上传结果到 SeaweedFS
3. **状态更新**: 自动更新数据库任务状态

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
