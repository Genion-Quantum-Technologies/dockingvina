#!/usr/bin/env python3
"""
Example: Integrate BINANA analysis into DockingVina workflow
演示如何在对接流程中无缝集成 BINANA 分析

Updated to use the new layered architecture:
- binana_toolkit: Base BINANA functionality
- dockingvina_integration: DockingVina-specific enhancements
"""

from pathlib import Path

# Use the new integration layer (recommended)
from dockingvina_integration import (
    DockingVinaBindingAnalyzer,
    analyze_binding_quick,
    batch_analyze_docking_results
)

# Note: You can also use the compatibility layer for existing code:
# from binana_analyzer import BindingAnalyzer, analyze_binding_quick

def example_1_basic_usage():
    """示例1: 基本使用 - 分析单个对接结果"""
    print("\n" + "="*60)
    print("示例1: 基本 BINANA 分析")
    print("="*60)
    
    # 使用项目资源中的蛋白
    receptor = "/home/davis/projects/dockingvina/resource/protein_7UDP.pdbqt"
    
    # 使用测试配体
    ligand = "/home/davis/projects/dockingvina/analysis/binana_toolkit/ligand_1.pdbqt"
    
    if not Path(receptor).exists():
        print("⚠️ Receptor 文件不存在，使用测试文件")
        receptor = "/home/davis/projects/dockingvina/analysis/binana_toolkit/receptorH.pdbqt"
    
    # 快速分析（一行代码）
    result = analyze_binding_quick(receptor, ligand, compound_id="DEMO_COMPOUND")
    
    if result["success"]:
        print("✅ 分析成功！")
        summary = result["interaction_summary"]
        print(f"\n📊 交互作用统计:")
        print(f"   总交互数: {summary['total_interactions']}")
        print(f"   涉及残基数: {summary['unique_residues']}")
        
        print(f"\n🔬 详细分类:")
        for interaction_type, count in summary['interaction_counts'].items():
            print(f"   - {interaction_type}: {count}")
        
        print(f"\n🎯 关键残基:")
        for interaction_type, residues in summary['key_residues'].items():
            if residues:
                print(f"   - {interaction_type}: {', '.join(residues[:3])}")
    else:
        print(f"❌ 分析失败: {result.get('error')}")

def example_2_batch_analysis():
    """示例2: 批量分析多个对接结果"""
    print("\n" + "="*60)
    print("示例2: 批量分析工作流")
    print("="*60)
    
    # 模拟多个对接结果
    receptor = "/home/davis/projects/dockingvina/analysis/binana_toolkit/receptorH.pdbqt"
    ligands = [
        {
            "file": "/home/davis/projects/dockingvina/analysis/binana_toolkit/ligand_1.pdbqt",
            "id": "COMPOUND_A",
            "score": -8.5
        },
        # 可以添加更多配体...
    ]
    
    # 初始化分析器（复用实例提高效率）
    analyzer = DockingVinaBindingAnalyzer(show_output=False)
    
    results = []
    for ligand_info in ligands:
        print(f"\n分析 {ligand_info['id']}...")
        
        result = analyzer.analyze_docking_result(
            receptor_file=receptor,
            ligand_file=ligand_info["file"],
            compound_id=ligand_info["id"]
        )
        
        if result["success"]:
            # 合并对接分数和交互分析
            combined = {
                "compound_id": ligand_info["id"],
                "docking_score": ligand_info["score"],
                "interactions": result["interaction_summary"]
            }
            results.append(combined)
            
            print(f"  ✅ 对接分数: {ligand_info['score']}")
            print(f"  ✅ 交互数: {result['interaction_summary']['total_interactions']}")
    
    # 按交互数量排序
    results.sort(key=lambda x: x["interactions"]["total_interactions"], reverse=True)
    
    print(f"\n📈 排序结果（按交互数量）:")
    for i, res in enumerate(results, 1):
        print(f"  {i}. {res['compound_id']}: "
              f"score={res['docking_score']}, "
              f"interactions={res['interactions']['total_interactions']}")

def example_3_custom_output():
    """示例3: 自定义输出目录"""
    print("\n" + "="*60)
    print("示例3: 自定义输出路径")
    print("="*60)
    
    receptor = "/home/davis/projects/dockingvina/analysis/binana_toolkit/receptorH.pdbqt"
    ligand = "/home/davis/projects/dockingvina/analysis/binana_toolkit/ligand_1.pdbqt"
    
    # 指定输出目录
    output_dir = "/tmp/binana_results_demo"
    
    analyzer = DockingVinaBindingAnalyzer()
    result = analyzer.analyze_docking_result(
        receptor_file=receptor,
        ligand_file=ligand,
        compound_id="CUSTOM_OUTPUT",
        output_dir=output_dir
    )
    
    if result["success"]:
        print(f"✅ 分析完成")
        print(f"📁 结果保存在: {result['analysis_files']['output_directory']}")
        print(f"📄 JSON 文件: {result['analysis_files']['binana_output']}")

def example_4_integration_workflow():
    """示例4: 完整的 DockingVina + BINANA 工作流"""
    print("\n" + "="*60)
    print("示例4: 完整工作流集成")
    print("="*60)
    
    # 模拟完整的对接+分析流程
    print("\n步骤1: 准备输入文件...")
    receptor = "/home/davis/projects/dockingvina/analysis/binana_toolkit/receptorH.pdbqt"
    ligand = "/home/davis/projects/dockingvina/analysis/binana_toolkit/ligand_1.pdbqt"
    
    print("步骤2: 执行分子对接...")
    # 这里会调用 vina_workflow.dock_molecule()
    docking_result = {
        "compound_id": "WORKFLOW_DEMO",
        "best_score": -8.5,
        "best_pose_file": ligand,  # 实际是对接输出
    }
    print(f"  ✅ 对接完成，最佳分数: {docking_result['best_score']}")
    
    print("\n步骤3: BINANA 交互分析...")
    analyzer = DockingVinaBindingAnalyzer(show_output=False)
    binding_analysis = analyzer.analyze_docking_result(
        receptor_file=receptor,
        ligand_file=docking_result["best_pose_file"],
        compound_id=docking_result["compound_id"]
    )
    
    print("\n步骤4: 合并结果...")
    if binding_analysis["success"]:
        final_result = {
            "compound_id": docking_result["compound_id"],
            "docking": {
                "score": docking_result["best_score"],
                "pose_file": docking_result["best_pose_file"]
            },
            "binding_analysis": binding_analysis["interaction_summary"],
            "status": "completed"
        }
        
        print("✅ 工作流完成！")
        print(f"\n📊 最终结果:")
        print(f"   化合物ID: {final_result['compound_id']}")
        print(f"   对接分数: {final_result['docking']['score']}")
        print(f"   交互作用数: {final_result['binding_analysis']['total_interactions']}")
        print(f"   涉及残基数: {final_result['binding_analysis']['unique_residues']}")
        
        return final_result
    else:
        print(f"❌ 交互分析失败: {binding_analysis.get('error')}")
        return None

def main():
    """运行所有示例"""
    print("\n" + "🧬 "*20)
    print("BINANA 集成使用示例")
    print("DockingVina Analysis Module")
    print("🧬 "*20)
    
    try:
        example_1_basic_usage()
        example_2_batch_analysis()
        example_3_custom_output()
        example_4_integration_workflow()
        
        print("\n" + "="*60)
        print("✅ 所有示例运行完成！")
        print("="*60)
        print("\n💡 提示:")
        print("   1. BINANA 已完全集成到 dockingvina")
        print("   2. 无需配置外部路径")
        print("   3. 可直接在对接流程中使用")
        print("   4. 支持批量分析和自定义输出")
        
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
