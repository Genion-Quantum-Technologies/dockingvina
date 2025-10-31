# BINANA 分析失败问题修复报告

## 🐛 问题描述

从日志中发现 BINANA 分析失败：
```
Warning: Ligand file not found for analog_1-1: analog_1-1-p0.sdf
Warning: Ligand file not found for analog_1-2: analog_1-2-p0.sdf
✅ Binding analysis completed: 0/2 successful
```

## 🔍 根本原因

在 `perform_binding_analysis()` 函数中：

1. **错误的文件类型：** 代码尝试使用 CSV 中的 `file` 列值作为配体文件路径
   - CSV 中的 `file` 列：`analog_1-1-p0.sdf` （SDF 文件名）
   - BINANA 需要：`.pdbqt` 文件

2. **错误的路径：** CSV 中只有文件名，没有完整路径
   - CSV 存储：`analog_1-1-p0.sdf`（相对文件名）
   - 实际需要：`/path/to/docked/analog_1-1.pdbqt`（绝对路径）

3. **错误的文件名：** PDBQT 文件名与 SDF 文件名不匹配
   - SDF 文件：`analog_1-1-p0.sdf`（包含 pose 编号）
   - PDBQT 文件：`analog_1-1.pdbqt`（不包含 pose 编号）

## 实际文件结构

```
docked/
├── analog_1-1.pdbqt          ← BINANA 需要这个
├── analog_1-1-p0.sdf         ← CSV 中记录的是这个
├── analog_1-1-p0.csv
├── analog_1-2.pdbqt          ← BINANA 需要这个
├── analog_1-2-p0.sdf         ← CSV 中记录的是这个
├── analog_1-2-p0.csv
└── binding_analysis_summary.json
```

## ✅ 修复方案

修改 `Vina/vina_workflow.py` 中的 `perform_binding_analysis()` 函数：

### 修改前（❌ 错误）
```python
for idx, row in dfRes.iterrows():
    enhanced_row = row.copy()
    
    try:
        # 直接使用 CSV 中的 file 列（错误！）
        ligand_file = row.get('file', '')  # 得到 "analog_1-1-p0.sdf"
        if not ligand_file or not os.path.exists(ligand_file):
            # 文件不存在！
            print(f"Warning: Ligand file not found: {ligand_file}")
```

### 修改后（✅ 正确）
```python
for idx, row in dfRes.iterrows():
    enhanced_row = row.copy()
    
    try:
        # 从 title 列构建正确的 PDBQT 文件路径
        compound_id = row.get('title', f'compound_{idx}')  # 得到 "analog_1-1"
        
        # 构建 PDBQT 文件的完整路径
        ligand_pdbqt = os.path.join(parent_path, 'docked', f'{compound_id}.pdbqt')
        # 得到 "/path/to/docked/analog_1-1.pdbqt"
        
        if not os.path.exists(ligand_pdbqt):
            print(f"Warning: Ligand PDBQT file not found for {compound_id}: {ligand_pdbqt}")
            enhanced_row['binding_analysis'] = {"error": "Ligand PDBQT file not found", "success": False}
        else:
            # 使用正确的 PDBQT 文件进行 BINANA 分析
            binana_output_dir = os.path.join(parent_path, 'docked', 'binding_analysis', compound_id)
            
            result = analyzer.analyze_docking_result(
                receptor_file=receptor_path,
                ligand_file=ligand_pdbqt,  # ✅ 使用 .pdbqt 文件
                compound_id=compound_id,
                output_dir=binana_output_dir
            )
```

## 🎯 修复效果

修复后，BINANA 分析将：

1. ✅ **正确找到 PDBQT 文件**
   - 从 CSV 的 `title` 列获取化合物ID：`analog_1-1`
   - 构建 PDBQT 路径：`docked/analog_1-1.pdbqt`
   - 使用绝对路径：`{parent_path}/docked/analog_1-1.pdbqt`

2. ✅ **成功执行 BINANA 分析**
   - 运行 BINANA 对接后分析
   - 生成详细的交互分析结果

3. ✅ **生成所有预期文件**
   ```
   docked/
   ├── binding_analysis/
   │   ├── analog_1-1/
   │   │   ├── output.json                  ← BINANA 详细结果
   │   │   ├── binding_mode_summary.csv     ← 残基交互摘要
   │   │   └── output_resid.csv             ← 残基交互摘要（兼容版）
   │   └── analog_1-2/
   │       ├── output.json
   │       ├── binding_mode_summary.csv
   │       └── output_resid.csv
   └── binding_analysis_summary.json        ← 总体摘要
   ```

## 📋 预期日志输出

修复后，下次对接任务的日志应该显示：

```
Running binding mode analysis for 2 docking results...
✅ Binding analysis completed: 2/2 successful
📁 Binding analysis summary saved to: .../docked/binding_analysis_summary.json
```

**binding_analysis_summary.json 内容：**
```json
{
  "total_compounds": 2,
  "successful_analyses": 2,        ← 从 0 变为 2
  "analysis_success_rate": 1.0,    ← 从 0.0 变为 1.0
  "binana_available": true,
  "timestamp": "2025-10-28T13:45:00.000000"
}
```

## 🚀 应用修复

**需要重启 DockingVina 服务：**
```bash
cd /home/davis/projects/dockingvina
./service restart
```

**运行新的对接任务验证修复效果。**

## 📝 文件对应关系总结

| 用途 | 文件类型 | 文件名示例 | 位置 |
|------|---------|-----------|------|
| 对接计算 | PDBQT | `analog_1-1.pdbqt` | `docked/` |
| 结果可视化 | SDF | `analog_1-1-p0.sdf` | `docked/` |
| 结果摘要 | CSV | `analog_1-1-p0.csv` | `docked/` |
| **BINANA 输入** | **PDBQT** | **`analog_1-1.pdbqt`** | **`docked/`** ✅ |
| BINANA 详细输出 | JSON | `output.json` | `docked/binding_analysis/{compound_id}/` |
| **BINANA 残基摘要** | **CSV** | **`output_resid.csv`** | **`docked/binding_analysis/{compound_id}/`** ✅ |
| BINANA 残基摘要 | CSV | `binding_mode_summary.csv` | `docked/binding_analysis/{compound_id}/` |
| BINANA 总摘要 | JSON | `binding_analysis_summary.json` | `docked/` |

**关键点：**
- BINANA 需要 `.pdbqt` 文件（包含所有 poses）
- 文件名使用 compound ID（如 `analog_1-1`），不包含 pose 编号
- 使用完整的绝对路径，不是相对路径或文件名
