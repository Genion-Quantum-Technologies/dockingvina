#!/usr/bin/env python3
"""
DockingVinaApp 测试脚本
用于验证系统的各个组件是否正常工作
"""

import os
import sys
import json
import asyncio
import tempfile
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

async def test_database_connection():
    """测试数据库连接"""
    print("测试数据库连接...")
    try:
        from database.db import get_db_connection
        connection = await get_db_connection()
        if connection:
            print("✅ 数据库连接成功")
            connection.close()
            return True
        else:
            print("❌ 数据库连接失败")
            return False
    except Exception as e:
        print(f"❌ 数据库连接测试失败: {e}")
        return False

def test_imports():
    """测试必要的模块导入"""
    print("测试模块导入...")
    try:
        import fastapi
        import aiomysql
        import pandas as pd
        import rdkit
        from vina import Vina
        from meeko import PDBQTMolecule
        print("✅ 所有必要模块导入成功")
        return True
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False

def test_vina_workflow():
    """测试vina_workflow模块"""
    print("测试Vina工作流模块...")
    try:
        sys.path.append(str(current_dir / "Vina"))
        from vina_workflow import vina_docking_from_list
        print("✅ Vina工作流模块导入成功")
        return True
    except Exception as e:
        print(f"❌ Vina工作流模块测试失败: {e}")
        return False

async def test_task_processor():
    """测试任务处理器"""
    print("测试任务处理器...")
    try:
        from docking_task_processor import DockingTaskProcessor
        processor = DockingTaskProcessor()
        print("✅ 任务处理器创建成功")
        return True
    except Exception as e:
        print(f"❌ 任务处理器测试失败: {e}")
        return False

def create_test_task():
    """创建一个测试任务目录结构"""
    print("创建测试任务...")
    try:
        # 创建临时目录
        test_dir = Path(tempfile.mkdtemp(prefix="docking_test_"))
        print(f"测试目录: {test_dir}")
        
        # 创建输入目录
        input_dir = test_dir / "input"
        input_dir.mkdir()
        
        # 创建输出目录
        output_dir = test_dir / "output"
        output_dir.mkdir()
        
        # 创建测试SMILES文件
        smiles_data = [
            {"smiles": "CCO", "title": "ethanol"},
            {"smiles": "CC(=O)O", "title": "acetic_acid"}
        ]
        
        import pandas as pd
        df = pd.DataFrame(smiles_data)
        df.to_csv(input_dir / "input.csv", index=False)
        
        # 创建配置文件
        config = {
            "smiles_file": "input.csv",
            "protein_file": "protein.pdbqt",
            "vina_box_file": "vina_box.json",
            "num_poses": 5,
            "num_cpu": 2
        }
        
        with open(test_dir / "docking_config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✅ 测试任务目录创建成功")
        print(f"测试目录结构:")
        for item in test_dir.rglob("*"):
            if item.is_file():
                print(f"  {item.relative_to(test_dir)}")
        
        return str(test_dir)
        
    except Exception as e:
        print(f"❌ 创建测试任务失败: {e}")
        return None

def test_file_structure():
    """测试文件结构"""
    print("测试文件结构...")
    required_files = [
        "main.py",
        "docking_task_processor.py",
        "config.py",
        "database/__init__.py",
        "database/config.py",
        "database/db.py",
        "Vina/vina_workflow.py",
        "my_toolsets/my_toolset/my_utils.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = current_dir / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 缺少必要文件: {missing_files}")
        return False
    else:
        print("✅ 文件结构完整")
        return True

async def main():
    """运行所有测试"""
    print("=" * 50)
    print("DockingVinaApp 系统测试")
    print("=" * 50)
    
    tests = [
        ("文件结构", test_file_structure),
        ("模块导入", test_imports),
        ("Vina工作流", test_vina_workflow),
        ("数据库连接", test_database_connection),
        ("任务处理器", test_task_processor),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}测试:")
        if asyncio.iscoroutinefunction(test_func):
            result = await test_func()
        else:
            result = test_func()
        results.append((test_name, result))
    
    # 创建测试任务
    print(f"\n📋 测试任务创建:")
    test_dir = create_test_task()
    
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if test_dir:
        print(f"\n💡 测试任务目录: {test_dir}")
        print("   可以使用此目录结构来测试实际的docking流程")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统已准备就绪。")
        return True
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败，请检查相关配置。")
        return False

if __name__ == "__main__":
    asyncio.run(main())
