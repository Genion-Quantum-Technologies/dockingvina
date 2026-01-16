#!/bin/bash
# ============================================================
# DockingVina Docker 管理脚本
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$SCRIPT_DIR"

# 默认值
COMPOSE_FILE="docker-compose.yml"
IMAGE_NAME="dockingvina"
CONTAINER_NAME="dockingvina-app"

# 帮助信息
show_help() {
    echo -e "${BLUE}DockingVina Docker 管理脚本${NC}"
    echo ""
    echo "用法: $0 <命令> [选项]"
    echo ""
    echo "命令:"
    echo "  build       构建 Docker 镜像"
    echo "  up          启动所有服务"
    echo "  down        停止并删除所有服务"
    echo "  start       启动已存在的服务"
    echo "  stop        停止服务"
    echo "  restart     重启服务"
    echo "  logs        查看日志"
    echo "  shell       进入容器 shell"
    echo "  status      查看服务状态"
    echo "  clean       清理未使用的资源"
    echo ""
    echo "选项:"
    echo "  -d, --dev   使用开发环境配置"
    echo "  -s, --storage  包含 SeaweedFS 存储服务"
    echo "  -f, --follow   持续跟踪日志"
    echo "  -h, --help     显示帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 build                    # 构建镜像"
    echo "  $0 up                       # 启动服务"
    echo "  $0 up -d                    # 使用开发配置启动"
    echo "  $0 up -s                    # 启动并包含 SeaweedFS"
    echo "  $0 logs -f                  # 持续查看日志"
    echo "  $0 shell                    # 进入容器"
}

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 构建镜像
build() {
    log_info "构建 Docker 镜像..."
    cd "$PROJECT_DIR"
    
    if [[ "$DEV_MODE" == "true" ]]; then
        docker build -t ${IMAGE_NAME}:dev -f docker/Dockerfile .
        log_info "开发镜像构建完成: ${IMAGE_NAME}:dev"
    else
        docker build -t ${IMAGE_NAME}:latest -f docker/Dockerfile .
        log_info "镜像构建完成: ${IMAGE_NAME}:latest"
    fi
}

# 启动服务
up() {
    log_info "启动服务..."
    cd "$DOCKER_DIR"
    
    local compose_cmd="docker compose -f $COMPOSE_FILE"
    
    if [[ "$INCLUDE_STORAGE" == "true" ]]; then
        compose_cmd="$compose_cmd --profile storage"
    fi
    
    $compose_cmd up -d
    
    log_info "服务已启动"
    log_info "API 地址: http://localhost:8000"
    log_info "健康检查: http://localhost:8000/health"
}

# 停止服务
down() {
    log_info "停止并删除服务..."
    cd "$DOCKER_DIR"
    
    local compose_cmd="docker compose -f $COMPOSE_FILE"
    
    if [[ "$INCLUDE_STORAGE" == "true" ]]; then
        compose_cmd="$compose_cmd --profile storage"
    fi
    
    $compose_cmd down
    
    log_info "服务已停止"
}

# 启动服务
start() {
    log_info "启动服务..."
    cd "$DOCKER_DIR"
    docker compose -f $COMPOSE_FILE start
}

# 停止服务
stop() {
    log_info "停止服务..."
    cd "$DOCKER_DIR"
    docker compose -f $COMPOSE_FILE stop
}

# 重启服务
restart() {
    log_info "重启服务..."
    cd "$DOCKER_DIR"
    docker compose -f $COMPOSE_FILE restart
}

# 查看日志
logs() {
    cd "$DOCKER_DIR"
    
    if [[ "$FOLLOW_LOGS" == "true" ]]; then
        docker compose -f $COMPOSE_FILE logs -f app
    else
        docker compose -f $COMPOSE_FILE logs --tail=100 app
    fi
}

# 进入容器 shell
shell() {
    log_info "进入容器 shell..."
    docker exec -it $CONTAINER_NAME mamba run -n dockingvina /bin/bash
}

# 查看服务状态
status() {
    log_info "服务状态:"
    cd "$DOCKER_DIR"
    docker compose -f $COMPOSE_FILE ps
}

# 清理未使用的资源
clean() {
    log_info "清理未使用的 Docker 资源..."
    docker system prune -f
    log_info "清理完成"
}

# 解析参数
DEV_MODE="false"
INCLUDE_STORAGE="false"
FOLLOW_LOGS="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dev)
            DEV_MODE="true"
            COMPOSE_FILE="docker-compose.dev.yml"
            CONTAINER_NAME="dockingvina-dev-app"
            shift
            ;;
        -s|--storage)
            INCLUDE_STORAGE="true"
            shift
            ;;
        -f|--follow)
            FOLLOW_LOGS="true"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        build|up|down|start|stop|restart|logs|shell|status|clean)
            COMMAND=$1
            shift
            ;;
        *)
            log_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 执行命令
if [[ -z "$COMMAND" ]]; then
    show_help
    exit 1
fi

case $COMMAND in
    build)
        build
        ;;
    up)
        up
        ;;
    down)
        down
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs
        ;;
    shell)
        shell
        ;;
    status)
        status
        ;;
    clean)
        clean
        ;;
    *)
        log_error "未知命令: $COMMAND"
        show_help
        exit 1
        ;;
esac
