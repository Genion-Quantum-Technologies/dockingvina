# ============================================================
# DockingVina Docker Image
# 使用 Mamba 进行环境管理
# 包含 AutoDock Vina, RDKit, OpenBabel, Meeko 等分子对接工具
# ============================================================

FROM condaforge/mambaforge:latest AS base

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ============================================================
# 依赖安装阶段 - 利用 Docker 缓存
# ============================================================
FROM base AS dependencies

# 复制环境配置文件
COPY env.yml ./

# 使用 mamba 创建环境 (包含 vina, rdkit, openbabel, meeko 等)
RUN mamba env create -f env.yml \
    && mamba clean --all --yes

# ============================================================
# 最终镜像
# ============================================================
FROM dependencies AS final

# 复制项目文件
COPY . /app/

# 激活环境并安装本地包
SHELL ["mamba", "run", "-n", "dockingvina", "/bin/bash", "-c"]

# 安装本地 my_toolsets 包
RUN pip install -e ./my_toolsets --no-deps

# gypsum_dl 是脚本项目，添加到 PYTHONPATH 即可使用
ENV PYTHONPATH="/app/gypsum_dl"

# 安装主项目包
RUN pip install -e . --no-deps

# 创建必要的目录
RUN mkdir -p /app/logs /tmp/docking_vina_app/resource

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
ENTRYPOINT ["mamba", "run", "--no-capture-output", "-n", "dockingvina"]
CMD ["uvicorn", "dockingvina.app:app", "--host", "0.0.0.0", "--port", "8000"]
