# async_task_processor.py 注意事项

## 状态：可能已过时

`dockingvina/async_task_processor.py` 文件中的 `_run_docking_sync` 方法使用了与当前 `vina_docking_from_list()` 函数不兼容的参数。

### 当前代码问题

该方法调用：
```python
result = vina_docking_from_list(
    receptor_path=receptor_path,
    ligand_smiles_list=ligand_smiles_list,
    output_dir=output_dir,
    center=center,
    size=size,
    exhaustiveness=exhaustiveness,
    num_modes=num_modes
)
```

但 `vina_docking_from_list()` 的实际签名是：
```python
def vina_docking_from_list(ligands: list,
                           receptor_pdbqt: str,
                           min_ph: float = 6.0,
                           max_ph: float = 8.0,
                           n_jobs: int = 8,
                           exhaustiveness: int = 8,
                           n_poses: int = 10) -> str:
```

### 实际使用情况

根据 `main.py` 的分析：
- ✅ **实际使用**: `docking_task_processor.py` 中的 `DockingTaskProcessor`（已修复）
- ⚠️ **已初始化但未使用**: `async_task_processor.py` 中的 `AsyncTaskProcessor`

`AsyncTaskProcessor` 被初始化但它的 docking 方法似乎没有被实际调用。真正处理 docking 任务的是通过 `background_task_runner()` 启动的定时任务。

### 建议

如果 `async_task_processor.py` 需要保留以供将来使用或其他目的，应该：

1. 更新 `_run_docking_sync` 方法以匹配新的函数签名
2. 或者标记为废弃并使用 `DockingTaskProcessor` 代替

当前的修复已经涵盖了实际运行的代码路径（`docking_task_processor.py`），因此不会影响生产环境。
