# BINANA 输出文件说明

## 📁 生成的文件对比

### 1. 独立 BINANA 脚本 (`/home/davis/projects/binana/binding_mode.py`)
```
binana_results/
├── output.json              # BINANA 原始 JSON 输出
└── output_resid.csv         # 受体残基交互摘要（手动生成）
```

### 2. DockingVina 集成版本（修改后）
```
{output_dir}/
├── output.json              # BINANA 原始 JSON 输出
├── binding_mode_summary.csv # 受体残基交互摘要（新名称）
└── output_resid.csv         # 受体残基交互摘要（兼容性副本）✅ 新增
```

## 📊 文件内容说明

### output_resid.csv 和 binding_mode_summary.csv
**格式：完全相同**

| 列名 | 说明 | 示例 |
|------|------|------|
| `interaction_type` | 交互类型 | `hydrophobic_contacts`, `close_contacts`, `hydrogen_bonds` 等 |
| `receptor_residue` | 受体残基标识 | `A:THR221`, `A:TRP125`, `A:ARG127` 等 |

**示例内容：**
```csv
interaction_type,receptor_residue
hydrophobic_contacts,A:THR221
hydrophobic_contacts,A:TRP125
hydrophobic_contacts,A:TRP189
close_contacts,A:ARG127
close_contacts,A:ASP155
close_contacts,A:ASP156
close_contacts,A:GLN226
hydrogen_bonds,A:GLU146
salt_bridges,A:LYS129
```

### output.json
**格式：BINANA 原始 JSON 输出**

包含所有交互的详细信息，包括：
- 氢键 (`hydrogenBonds`)
- 盐桥 (`saltBridges`)
- 疏水接触 (`hydrophobicContacts`)
- π-π 堆积 (`piStackings`)
- π-阳离子交互 (`piCationInteractions`)
- 金属配位 (`metalComplexes`)
- 紧密接触 (`closeContacts`)

每个交互包含：
- 受体原子详细信息 (`receptorAtoms`)
- 配体原子详细信息 (`ligandAtoms`)
- 交互距离和角度等参数

## 🔄 修改内容

### binding_analyzer.py 修改
```python
def analyze(self, receptor_file, ligand_file, output_dir, save_csv=True):
    # ... 分析代码 ...
    
    if save_csv:
        # 保存为 binding_mode_summary.csv（新名称）
        csv_path = os.path.join(output_dir, 'binding_mode_summary.csv')
        residue_df.to_csv(csv_path, index=False)
        
        # 同时保存为 output_resid.csv（兼容性）✅ 新增
        resid_csv_path = os.path.join(output_dir, 'output_resid.csv')
        residue_df.to_csv(resid_csv_path, index=False)
    
    results = {
        'csv_file': csv_path,
        'resid_csv_file': resid_csv_path,  # ✅ 新增字段
        # ... 其他结果 ...
    }
```

## 📍 在对接流程中的位置

### DockingVina 对接结果目录结构
```
{parent_path}/
├── docked/
│   ├── {ligand}.pdbqt              # 对接结果
│   ├── {ligand}.csv                # 对接分数
│   ├── binding_analysis_summary.json  # BINANA 分析汇总
│   └── binding_analysis/           # BINANA 详细分析结果
│       └── {compound_id}/
│           ├── output.json         # BINANA 原始输出
│           ├── binding_mode_summary.csv  # 残基摘要
│           └── output_resid.csv    # 残基摘要（兼容版）✅ 新增
└── dockRes.json                    # 完整对接结果（包含 binding_analysis 字段）
```

## 🎯 使用场景

### 1. 读取交互残基信息
```python
import pandas as pd

# 两种文件名都可以使用
df = pd.read_csv('output_resid.csv')
# 或
df = pd.read_csv('binding_mode_summary.csv')

# 查看所有交互类型
print(df['interaction_type'].unique())

# 查看特定交互类型的残基
hydrophobic = df[df['interaction_type'] == 'hydrophobic_contacts']
print(hydrophobic['receptor_residue'].tolist())
```

### 2. 统计交互类型分布
```python
interaction_counts = df['interaction_type'].value_counts()
print(interaction_counts)

# 输出示例:
# close_contacts          10
# hydrophobic_contacts     3
# hydrogen_bonds           2
# salt_bridges             1
```

### 3. 识别关键残基
```python
# 找出参与多种交互的残基
residue_counts = df['receptor_residue'].value_counts()
key_residues = residue_counts[residue_counts > 1]
print("参与多种交互的关键残基:")
print(key_residues)
```

## ✅ 验证测试

### 测试脚本
```bash
cd /home/davis/projects/dockingvina
micromamba run -n dockingvina python test_output_resid.py
```

### 预期输出
```
✅ output.json generated (59705 bytes)
✅ binding_mode_summary.csv generated (436 bytes)
✅ output_resid.csv generated (436 bytes)
✅ TEST PASSED: All expected files generated
```

## 📝 总结

| 特性 | 独立 binana | DockingVina 集成（修改前） | DockingVina 集成（修改后） |
|------|------------|------------------------|------------------------|
| 生成 `output.json` | ✅ | ✅ | ✅ |
| 生成 `output_resid.csv` | ✅ | ❌ | ✅ |
| 生成 `binding_mode_summary.csv` | ❌ | ✅ | ✅ |
| 文件内容 | 相同 | 相同 | 相同 |
| 命名兼容性 | - | 部分 | 完全 ✅ |

**结论：** 修改后的 DockingVina 现在会同时生成两个相同内容的 CSV 文件，确保与独立 BINANA 脚本和现有代码的完全兼容性。
