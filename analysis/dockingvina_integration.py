#!/usr/bin/env python3
"""
DockingVina Integration Layer for BINANA Analysis
专门为 DockingVina 项目设计的 BINANA 分析集成层

This module provides DockingVina-specific enhancements on top of the base
BINANA toolkit, including specialized output formats, batch processing,
and integration with the docking workflow.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# BINANA 导入 - 支持多种安装方式
BINANA_AVAILABLE = False
BaseBindingAnalyzer = None

def _import_binana():
    """尝试多种方式导入 BINANA BindingAnalyzer"""
    global BINANA_AVAILABLE, BaseBindingAnalyzer
    
    # 方式 1: 作为已安装的 binana 包导入 (pip install)
    try:
        from binana.binding_analyzer import BindingAnalyzer as _BaseAnalyzer
        BINANA_AVAILABLE = True
        return _BaseAnalyzer
    except ImportError:
        pass
    
    # 方式 2: 从环境变量指定的路径导入
    binana_project_path = os.environ.get("BINANA_PROJECT_PATH")
    if binana_project_path and os.path.isdir(binana_project_path):
        if binana_project_path not in sys.path:
            sys.path.insert(0, binana_project_path)
        try:
            from binding_analyzer import BindingAnalyzer as _BaseAnalyzer
            BINANA_AVAILABLE = True
            return _BaseAnalyzer
        except ImportError:
            pass
    
    # 方式 3: 从 binana_toolkit 子目录导入 (符号链接或复制)
    try:
        from .binana_toolkit.binding_analyzer import BindingAnalyzer as _BaseAnalyzer
        BINANA_AVAILABLE = True
        return _BaseAnalyzer
    except ImportError:
        pass
    
    return None

BaseBindingAnalyzer = _import_binana()

if not BINANA_AVAILABLE:
    raise ImportError(
        "BINANA module not found. Please install it using one of these methods:\n"
        "  1. pip install -e /path/to/binana  (recommended for Docker)\n"
        "  2. Set BINANA_PROJECT_PATH environment variable\n"
        "  3. Create symlink: ln -s /path/to/binana analysis/binana_toolkit"
    )


class DockingVinaBindingAnalyzer(BaseBindingAnalyzer):
    """
    DockingVina 专用的 BINANA 分析器
    
    在基础 BindingAnalyzer 之上添加了 DockingVina 特定的功能：
    - analyze_docking_result(): 专门用于对接结果分析的紧凑输出格式
    - 自动路径查找优先使用内置 binana_toolkit
    - 与 DockingVina API 兼容的输出结构
    """
    
    def __init__(self, binana_path: Optional[str] = None, show_output: bool = False):
        """
        Initialize the DockingVina-specific analyzer.
        
        Args:
            binana_path (str, optional): Path to run_binana.py. If None, auto-detects.
            show_output (bool): Whether to show detailed BINANA output.
        """
        if binana_path is None:
            binana_path = self._find_bundled_binana()
        
        super().__init__(binana_path=binana_path, show_output=show_output)
    
    def _find_bundled_binana(self) -> str:
        """
        Auto-detect BINANA installation with DockingVina-specific priority.
        
        优先级顺序：
        1. 环境变量指定的 BINANA_PATH
        2. binana 包安装路径
        3. binana_toolkit 子目录
        """
        # Priority 0: Check environment variable
        env_binana_path = os.getenv("BINANA_PATH")
        if env_binana_path and os.path.exists(env_binana_path):
            return env_binana_path
        
        # Priority 1: Try to find from installed binana package
        try:
            import binana
            binana_dir = Path(binana.__file__).parent
            binana_script = binana_dir / "python" / "run_binana.py"
            if binana_script.exists():
                return str(binana_script)
        except ImportError:
            pass
        
        # Priority 2: Check BINANA_PROJECT_PATH environment variable
        binana_project_path = os.environ.get("BINANA_PROJECT_PATH")
        if binana_project_path:
            binana_script = Path(binana_project_path) / "python" / "run_binana.py"
            if binana_script.exists():
                return str(binana_script)
        
        # Priority 3: Use bundled BINANA toolkit within dockingvina
        bundled_path = Path(__file__).parent / "binana_toolkit" / "python" / "run_binana.py"
        if bundled_path.exists():
            return str(bundled_path)
        
        raise FileNotFoundError(
            "Could not find BINANA run_binana.py. Please ensure:\n"
            "  1. Set BINANA_PATH environment variable to run_binana.py path, or\n"
            "  2. pip install -e /path/to/binana, or\n"
            "  3. Set BINANA_PROJECT_PATH to binana project directory"
        )
    
    def analyze_docking_result(self, 
                             receptor_file: str, 
                             ligand_file: str, 
                             compound_id: Optional[str] = None,
                             output_dir: Optional[str] = None) -> Dict:
        """
        Analyze a single docking result for binding interactions.
        
        这是 DockingVina 特定的方法，返回紧凑的 JSON 兼容格式，
        适合在对接流程中使用和存储。
        
        Args:
            receptor_file (str): Path to receptor PDBQT file
            ligand_file (str): Path to ligand PDBQT file
            compound_id (str): Identifier for this compound
            output_dir (str): Output directory. If None, uses temporary directory.
            
        Returns:
            Dict: Compact analysis results suitable for JSON serialization
                {
                    "success": bool,
                    "compound_id": str,
                    "interaction_summary": {
                        "total_interactions": int,
                        "unique_residues": int,
                        "interaction_counts": dict,
                        "key_residues": dict
                    },
                    "analysis_files": {...}
                }
        """
        # Set default output directory
        if output_dir is None:
            base_dir = os.path.dirname(ligand_file) if os.path.exists(ligand_file) else "."
            output_dir = os.path.join(base_dir, "binana_tmp")
        
        # Validate inputs
        try:
            self.validate_inputs(receptor_file, ligand_file)
        except FileNotFoundError as e:
            return {"error": str(e), "success": False}
        
        # Run BINANA analysis
        if not self.run_binana(receptor_file, ligand_file, output_dir):
            return {"error": "BINANA analysis failed", "success": False}
        
        try:
            # Parse results
            residue_df, full_data = self.parse_binana_output(output_dir)
            
            # Save CSV output
            csv_path = os.path.join(output_dir, 'binding_mode_summary.csv')
            residue_df.to_csv(csv_path, index=False)
            
            # Generate statistics
            interaction_stats = residue_df['interaction_type'].value_counts().to_dict()
            unique_residues = residue_df['receptor_residue'].nunique()
            
            # Get key residues for each interaction type
            key_residues = {}
            for interaction_type in interaction_stats.keys():
                residues = residue_df[residue_df['interaction_type'] == interaction_type]['receptor_residue'].tolist()
                key_residues[interaction_type] = residues[:5]  # Top 5 residues per type
            
            # Compact result structure for dockingvina integration
            result = {
                "success": True,
                "compound_id": compound_id,
                "interaction_summary": {
                    "total_interactions": len(residue_df),
                    "unique_residues": unique_residues,
                    "interaction_counts": interaction_stats,
                    "key_residues": key_residues
                },
                "analysis_files": {
                    "binana_output": os.path.join(output_dir, 'output.json'),
                    "binding_mode_summary": csv_path,
                    "output_directory": output_dir
                }
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Analysis parsing failed: {str(e)}", "success": False}


# Quick analysis functions for DockingVina workflow
def analyze_binding_quick(receptor_pdbqt: str, ligand_pdbqt: str, compound_id: Optional[str] = None) -> Dict:
    """
    Quick binding mode analysis with minimal setup for DockingVina integration.
    
    This is a convenience function for one-line analysis in docking workflows.
    
    Args:
        receptor_pdbqt (str): Path to receptor PDBQT file
        ligand_pdbqt (str): Path to ligand PDBQT file
        compound_id (str, optional): Compound identifier
        
    Returns:
        Dict: Compact analysis results
        
    Example:
        >>> result = analyze_binding_quick("protein.pdbqt", "ligand.pdbqt", "ZINC12345")
        >>> if result["success"]:
        >>>     print(result["interaction_summary"])
    """
    analyzer = DockingVinaBindingAnalyzer()
    return analyzer.analyze_docking_result(receptor_pdbqt, ligand_pdbqt, compound_id)


def get_interaction_summary(receptor_pdbqt: str, ligand_pdbqt: str) -> Dict:
    """
    Get basic interaction statistics for DockingVina results.
    
    Args:
        receptor_pdbqt (str): Path to receptor PDBQT file
        ligand_pdbqt (str): Path to ligand PDBQT file
        
    Returns:
        Dict: Interaction summary or error dict
        
    Example:
        >>> summary = get_interaction_summary("protein.pdbqt", "ligand.pdbqt")
        >>> print(f"Total interactions: {summary['total_interactions']}")
    """
    result = analyze_binding_quick(receptor_pdbqt, ligand_pdbqt)
    if result.get("success"):
        return result["interaction_summary"]
    else:
        return {"error": result.get("error", "Analysis failed")}


def find_key_residues(receptor_pdbqt: str, ligand_pdbqt: str, top_n: int = 10) -> List[str]:
    """
    Find the most important interacting residues in DockingVina results.
    
    Args:
        receptor_pdbqt (str): Path to receptor PDBQT file
        ligand_pdbqt (str): Path to ligand PDBQT file
        top_n (int): Number of top residues to return
        
    Returns:
        List[str]: List of key residue identifiers (e.g., ["A:GLU123", "A:TRP45"])
        
    Example:
        >>> residues = find_key_residues("protein.pdbqt", "ligand.pdbqt", top_n=5)
        >>> print(f"Top binding residues: {', '.join(residues)}")
    """
    result = analyze_binding_quick(receptor_pdbqt, ligand_pdbqt)
    if result.get("success"):
        all_residues = []
        for residue_list in result["interaction_summary"]["key_residues"].values():
            all_residues.extend(residue_list)
        # Remove duplicates and return top N
        unique_residues = list(dict.fromkeys(all_residues))
        return unique_residues[:top_n]
    else:
        return []


def batch_analyze_docking_results(receptor_file: str, 
                                  ligand_files: List[Dict[str, str]],
                                  output_base_dir: str = "./batch_analysis/") -> List[Dict]:
    """
    Batch analyze multiple docking results for DockingVina.
    
    Args:
        receptor_file (str): Path to receptor PDBQT file
        ligand_files (List[Dict]): List of dicts with 'file' and 'compound_id' keys
        output_base_dir (str): Base directory for output
        
    Returns:
        List[Dict]: List of analysis results
        
    Example:
        >>> ligands = [
        >>>     {"file": "ligand1.pdbqt", "compound_id": "ZINC001"},
        >>>     {"file": "ligand2.pdbqt", "compound_id": "ZINC002"}
        >>> ]
        >>> results = batch_analyze_docking_results("protein.pdbqt", ligands)
    """
    analyzer = DockingVinaBindingAnalyzer(show_output=False)
    results = []
    
    os.makedirs(output_base_dir, exist_ok=True)
    
    for ligand_info in ligand_files:
        ligand_file = ligand_info.get("file")
        if not ligand_file:
            continue
            
        compound_id = ligand_info.get("compound_id") or os.path.basename(ligand_file)
        output_dir = os.path.join(output_base_dir, compound_id)
        
        result = analyzer.analyze_docking_result(
            receptor_file=receptor_file,
            ligand_file=ligand_file,
            compound_id=compound_id,
            output_dir=output_dir
        )
        
        results.append(result)
    
    return results
