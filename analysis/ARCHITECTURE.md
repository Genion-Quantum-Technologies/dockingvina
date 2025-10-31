```
🏗️  DockingVina Analysis 模块 - 分层架构图 (v2.0)

┌─────────────────────────────────────────────────────────────────────┐
│                        应用层 (Application Layer)                    │
│                                                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ example_usage.py │  │report_generator.py│ │  其他应用脚本     │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
└───────────────────────────────┬───────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              DockingVina 集成层 (Integration Layer) ⭐               │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │         dockingvina_integration.py (新增)                    │   │
│  │                                                               │   │
│  │  • DockingVinaBindingAnalyzer (继承自 BaseBindingAnalyzer)  │   │
│  │  • analyze_binding_quick()  - 快速分析                       │   │
│  │  • get_interaction_summary() - 获取摘要                      │   │
│  │  • find_key_residues()      - 查找关键残基                  │   │
│  │  • batch_analyze_docking_results() - 批量分析               │   │
│  │                                                               │   │
│  │  特性:                                                        │   │
│  │  ✓ JSON 兼容的紧凑输出                                       │   │
│  │  ✓ 自动 BINANA 路径发现                                     │   │
│  │  ✓ DockingVina API 适配                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬───────────────────────────────────┘
                                │ 继承
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              底层工具包 (Base Toolkit Layer)                          │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              binana_toolkit/ (通用可复用)                    │   │
│  │                                                               │   │
│  │  • BindingAnalyzer (基础类)                                  │   │
│  │  • quick_analysis.py                                         │   │
│  │  • binding_mode.py                                           │   │
│  │  • examples.py                                               │   │
│  │                                                               │   │
│  │  • python/                                                   │   │
│  │    └── run_binana.py (BINANA 核心)                          │   │
│  │        └── binana/ (BINANA 包)                               │   │
│  │                                                               │   │
│  │  特性:                                                        │   │
│  │  ✓ 通用 BINANA 包装                                          │   │
│  │  ✓ 详细的 DataFrame 输出                                     │   │
│  │  ✓ 可被其他项目复用                                          │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                   兼容层 (Compatibility Layer) ⚠️                     │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  binana_analyzer.py (薄包装层，已弃用)                       │   │
│  │                                                               │   │
│  │  class BindingAnalyzer(DockingVinaBindingAnalyzer):         │   │
│  │      pass  # 仅为向后兼容                                    │   │
│  │                                                               │   │
│  │  ⚠️  保持旧代码兼容，新代码请使用 dockingvina_integration    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  interaction_parser.py (兼容导入)                            │   │
│  │                                                               │   │
│  │  from .utils.interaction_parser import InteractionParser    │   │
│  │                                                               │   │
│  │  ⚠️  实际代码已移至 utils/，此处仅为兼容                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      工具模块 (Utilities)                             │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    utils/                                     │   │
│  │                                                               │   │
│  │  • interaction_parser.py - BINANA 结果解析                   │   │
│  │  • (未来可添加更多工具)                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘


📊 数据流示例:

用户代码
  │
  ├─ 新代码 (推荐) ────────────────────────────────┐
  │                                                  │
  │  from analysis.dockingvina_integration import  │
  │      DockingVinaBindingAnalyzer                │
  │                                                  │
  │  analyzer = DockingVinaBindingAnalyzer()       │
  │  result = analyzer.analyze_docking_result(...)  │
  │                                                  │
  └──────────────────────────────────────────────────┘
  │
  ├─ 旧代码 (兼容) ────────────────────────────────┐
  │                                                  │
  │  from analysis.binana_analyzer import          │
  │      BindingAnalyzer                           │
  │                                                  │
  │  analyzer = BindingAnalyzer()  # 实际调用新类  │
  │  result = analyzer.analyze_docking_result(...)  │
  │                                                  │
  └──────────────────────────────────────────────────┘
  │
  ▼
DockingVinaBindingAnalyzer (集成层)
  │
  │ 继承
  ▼
BindingAnalyzer (binana_toolkit 基础类)
  │
  │ 调用
  ▼
run_binana.py (BINANA 核心)
  │
  ▼
BINANA 分析结果


🎯 主要改进:

1. ✅ 消除代码重复
   - binana_analyzer.py 现在仅是薄包装层
   - 核心功能在 dockingvina_integration.py

2. ✅ 清晰的职责分离
   - binana_toolkit: 通用工具
   - dockingvina_integration: 项目特定功能
   - utils: 辅助工具

3. ✅ 完全向后兼容
   - 旧代码无需修改
   - 新代码使用改进的 API

4. ✅ 便于维护
   - 修改只需在一处进行
   - 结构清晰，易于理解

5. ✅ 灵活部署
   - binana_toolkit 可独立使用
   - dockingvina_integration 提供增强功能
```
