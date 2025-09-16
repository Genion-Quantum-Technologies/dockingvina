# DockingVinaApp

基于AutoDock Vina的分子对接应用，仿照peptide_opt的设计模式，从数据库获取任务参数并执行docking计算。

## 功能特点

- **数据库驱动**: 从MySQL数据库tasks表获取待处理的docking任务
- **异步处理**: 使用FastAPI + asyncio实现异步任务处理
- **自动化流程**: 自动处理从SMILES到docking结果的完整流程
- **结果管理**: 结构化保存docking结果到指定目录

## 架构设计

```
dockingVinaApp/
├── main.py                    # FastAPI主应用
├── docking_task_processor.py  # 任务处理器
├── config.py                  # 配置文件
├── database/                  # 数据库模块
│   ├── __init__.py
│   ├── config.py              # 数据库配置
│   └── db.py                  # 数据库操作
├── Vina/                      # Vina相关模块
│   └── vina_workflow.py       # Vina工作流
├── models/                    # 数据模型
├── resource/                  # 资源文件
└── gypsum_dl/                 # Gypsum-DL模块
```

## 数据库任务格式

### 任务表结构
```sql
SELECT id, user_id, task_type, job_dir, status 
FROM tasks 
WHERE status = 'pending' AND task_type = 'docking'
```

### 任务配置文件
在`job_dir`目录下需要包含：

1. **输入目录** (`input/`):
   - `input.csv`: SMILES分子文件，包含`smiles`和`title`列
   - `protein.pdbqt`: 蛋白质受体文件
   - `vina_box.json`: 对接盒子配置

2. **配置文件** (`docking_config.json`):
```json
{
    "smiles_file": "input.csv",
    "protein_file": "protein.pdbqt", 
    "vina_box_file": "vina_box.json",
    "num_poses": 10,
    "energy_range": 3,
    "exhaustiveness": 8,
    "num_cpu": 8,
    "seed": 0,
    "min_ph": 6.0,
    "max_ph": 8.0
}
```

3. **输出目录** (`output/`):
   - 自动创建，保存docking结果

## 使用方法

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置数据库
修改`database/config.py`中的数据库连接参数。

### 3. 启动应用
```bash
./start.sh
```

或直接运行：
```bash
python main.py
```

### 4. API接口

- `GET /`: 根路径，返回服务状态
- `GET /health`: 健康检查
- `POST /trigger-task-check`: 手动触发任务检查（测试用）

## 工作流程

1. **任务监控**: 应用每3分钟查询数据库中状态为`pending`的`docking`任务
2. **任务处理**: 
   - 读取任务配置文件
   - 验证输入文件
   - 执行SMILES → PDBQT转换
   - 运行AutoDock Vina对接
   - 转换结果格式
3. **状态更新**: 自动更新任务状态为`running`、`finished`或`failed`
4. **结果保存**: 将结果保存到指定的输出目录

## 与peptide_opt的对比

| 特性 | peptide_opt | dockingVinaApp |
|------|------------|----------------|
| 任务类型 | peptide_optimization | docking |
| 端口 | 8001 | 8002 |
| 查询间隔 | 5分钟 | 3分钟 |
| 配置文件 | optimization_config.txt | docking_config.json |
| 输入格式 | FASTA + PDB | CSV + PDBQT |

## 注意事项

1. 确保resource目录下有必要的资源文件
2. 数据库连接配置正确
3. AutoDock Vina和相关依赖正确安装
4. 有足够的磁盘空间存储中间文件和结果

## 故障排除

1. **数据库连接失败**: 检查database/config.py中的连接参数
2. **Vina运行失败**: 检查AutoDock Vina是否正确安装
3. **文件路径错误**: 确保所有输入文件路径正确且文件存在
4. **权限问题**: 确保应用有权限读写工作目录



git clone https://github.com/durrantlab/gypsum_dl.git
# or
git clone git@github.com:durrantlab/gypsum_dl.git
git clone https://github.com/SongyouZhong/gypsum_dl.git

<!-- # 需要修改gypsum_dl/Start.py的源码
# replace 'os.mkdir(params["output_folder"])' with os.makedirs(params["output_folder"], exist_ok=True) -->