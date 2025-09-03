#!/bin/bash

# DockingVinaApp 启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 设置环境变量
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# 检查Python环境
echo "检查Python环境..."
python3 -c "import sys; print(f'Python版本: {sys.version}')"

# 检查必要的依赖
echo "检查必要依赖..."
python3 -c "
import sys
try:
    import fastapi
    import aiomysql
    import pandas
    import rdkit
    import vina
    import meeko
    print('所有依赖检查通过')
except ImportError as e:
    print(f'缺少依赖: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "依赖检查失败，请安装必要的Python包"
    exit 1
fi

# 创建日志目录
mkdir -p logs

# 启动应用
echo "启动DockingVinaApp..."
python3 main.py
