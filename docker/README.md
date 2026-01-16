# DockingVina Docker 部署指南

本文档介绍如何使用 Docker 部署 DockingVina 分子对接服务。

## 目录结构

```
docker/
├── Dockerfile              # Docker 镜像构建文件
├── docker-compose.yml      # 生产环境配置
├── docker-compose.dev.yml  # 开发环境配置
├── docker-manage.sh        # Docker 管理脚本
├── .dockerignore           # Docker 构建忽略文件
└── README.md               # 本文档
```

## 快速开始

### 1. 构建镜像

```bash
cd docker
./docker-manage.sh build
```

### 2. 启动服务

```bash
# 生产环境
./docker-manage.sh up

# 开发环境 (支持热重载)
./docker-manage.sh -d up

# 包含 SeaweedFS 存储服务
./docker-manage.sh -s up
```

### 3. 查看服务状态

```bash
./docker-manage.sh status
```

### 4. 查看日志

```bash
# 查看最近日志
./docker-manage.sh logs

# 持续跟踪日志
./docker-manage.sh -f logs
```

### 5. 进入容器

```bash
./docker-manage.sh shell
```

### 6. 停止服务

```bash
./docker-manage.sh down
```

## 环境配置

### 环境变量

可以通过 `.env` 文件或环境变量配置以下参数：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `DB_HOST` | postgres | 数据库主机 |
| `DB_PORT` | 5432 | 数据库端口 |
| `DB_USER` | admin | 数据库用户 |
| `DB_PASSWORD` | secret | 数据库密码 |
| `DB_NAME` | mydatabase | 数据库名称 |
| `SEAWEED_FILER_ENDPOINT` | http://seaweedfs-filer:8888 | SeaweedFS Filer 端点 |
| `SEAWEED_S3_ENDPOINT` | http://seaweedfs-s3:8333 | SeaweedFS S3 端点 |
| `TASK_QUERY_INTERVAL` | 180 | 任务查询间隔 (秒) |
| `MAX_CONCURRENT_TASKS` | 3 | 最大并发任务数 |
| `DOCKING_NUM_CPU` | 8 | 对接使用的 CPU 数 |
| `BINANA_ENABLED` | true | 是否启用 BINANA 分析 |
| `APP_PORT` | 8000 | 应用端口 |

### 创建 `.env` 文件

```bash
cd docker
cp ../.env.example .env
# 编辑 .env 文件配置参数
```

## 单独运行容器

如果不使用 docker-compose，可以单独运行容器：

```bash
# 构建镜像
docker build -t dockingvina:latest -f docker/Dockerfile .

# 运行容器
docker run -d --name dockingvina-test \
  -e DB_HOST=172.17.0.1 \
  -e DB_PORT=5432 \
  -e DB_USER=admin \
  -e DB_PASSWORD=secret \
  -e DB_NAME=mydatabase \
  -e SEAWEED_FILER_ENDPOINT=http://172.17.0.1:8888 \
  -p 8000:8000 \
  dockingvina:latest
```

## 开发环境

开发环境配置 (`docker-compose.dev.yml`) 提供以下特性：

- **热重载**: 源代码挂载到容器，支持自动重载
- **调试模式**: 更短的任务查询间隔
- **日志目录**: 本地日志目录挂载

启动开发环境：

```bash
./docker-manage.sh -d up
```

## 生产部署建议

### 1. 资源限制

在 `docker-compose.yml` 中添加资源限制：

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '8'
          memory: 16G
        reservations:
          cpus: '4'
          memory: 8G
```

### 2. 日志配置

配置日志轮转：

```yaml
services:
  app:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
```

### 3. 健康检查

服务已配置健康检查，可通过以下端点验证：

```bash
curl http://localhost:8000/health
```

### 4. 数据持久化

确保以下 volume 被正确挂载和备份：

- `postgres_data`: PostgreSQL 数据
- `seaweedfs_data`: SeaweedFS 对象存储数据
- `dockingvina_logs`: 应用日志
- `dockingvina_temp`: 临时文件（可选备份）

## 故障排除

### 镜像构建失败

1. 检查 `env.yml` 文件是否存在
2. 确保网络连接正常（需要下载 conda 包）
3. 查看构建日志定位问题

### 服务启动失败

1. 检查数据库是否可访问
2. 验证环境变量配置
3. 查看容器日志：`./docker-manage.sh logs`

### 容器内调试

```bash
# 进入容器
./docker-manage.sh shell

# 在容器内激活环境
# (已自动激活 dockingvina 环境)

# 测试 Python 环境
python -c "import vina; print('Vina OK')"
python -c "from rdkit import Chem; print('RDKit OK')"
```

## 清理资源

```bash
# 停止并删除服务
./docker-manage.sh down

# 清理未使用的 Docker 资源
./docker-manage.sh clean

# 删除所有相关 volume (谨慎!)
docker volume rm dockingvina-postgres-data dockingvina-logs dockingvina-temp
```
