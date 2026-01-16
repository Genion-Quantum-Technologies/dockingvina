#!/usr/bin/env python3
"""
DockingVina BINANA Binding Mode Analyzer

This module provides DockingVina-specific enhancements on top of the base
BINANA toolkit, including specialized output formats, batch processing,
and integration with the docking workflow.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# BINANA import - supports multiple installation methods
BINANA_AVAILABLE = False
BaseBindingAnalyzer = None


def _import_binana():
    """Try multiple methods to import BINANA BindingAnalyzer."""
    global BINANA_AVAILABLE, BaseBindingAnalyzer
    
    # Method 1: Import as installed binana package (pip install)
    try:
        from binana.binding_analyzer import BindingAnalyzer as _BaseAnalyzer
        BINANA_AVAILABLE = True
        return _BaseAnalyzer
    except ImportError:
        pass
    
    # Method 2: Import from environment variable path
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
    
    # Method 3: Import from binana_toolkit subdirectory (symlink or copy)
    try:
        # Try relative import from vendor directory
        vendor_path = Path(__file__).parent.parent.parent.parent / "vendor" / "binana"
        if vendor_path.exists() and str(vendor_path) not in sys.path:
            sys.path.insert(0, str(vendor_path))
        from binding_analyzer import BindingAnalyzer as _BaseAnalyzer
        BINANA_AVAILABLE = True
        return _BaseAnalyzer
    except ImportError:
        pass
    
    return None


BaseBindingAnalyzer = _import_binana()

if not BINANA_AVAILABLE:
    import warnings
    warnings.warn(
        "BINANA module not found. Please install it using one of these methods:\n"
        "  1. pip install -e /path/to/binana  (recommended for Docker)\n"
        "  2. Set BINANA_PROJECT_PATH environment variable\n"
        "  3. Copy binana to vendor/binana directory"
    )
    
    # Create a placeholder class
    class BaseBindingAnalyzer:
        def __init__(self, *args, **kwargs):
            raise ImportError("BINANA module not available")


class DockingVinaBindingAnalyzer(BaseBindingAnalyzer):
    """
    DockingVina-specific BINANA analyzer.
    
    Adds DockingVina-specific functionality on top of base BindingAnalyzer:
    - analyze_docking_result(): Compact output format for docking results
    - Auto path detection for built-in BINANA
    - Output structure compatible with DockingVina API
    """
    
    def __init__(self, binana_path: Optional[str] = None, show_output: bool = False):
        """
        Initialize the DockingVina-specific analyzer.
        
        Args:
            binana_path: Path to run_binana.py. If None, auto-detects.
            show_output: Whether to show detailed BINANA output.
        """
        if not BINANA_AVAILABLE:
            raise ImportError("BINANA module not available")
            
        if binana_path is None:
            binana_path = self._find_bundled_binana()
        
        super().__init__(binana_path=binana_path, show_output=show_output)
    
    def _find_bundled_binana(self) -> str:
        """
        Auto-detect BINANA installation with DockingVina-specific priority.
        
        Priority order:
        1. BINANA_PATH environment variable
        2. binana package installation path
        3. vendor/binana directory
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
        
        # Priority 3: Check vendor directory
        vendor_binana = Path(__file__).parent.parent.parent.parent / "vendor" / "binana" / "python" / "run_binana.py"
        if vendor_binana.exists():
            return str(vendor_binana)
        
        raise FileNotFoundError(
            "Could not find BINANA run_binana.py. Please ensure:\n"
            "  1. Set BINANA_PATH environment variable to run_binana.py path, or\n"
            "  2. pip install -e /path/to/binana, or\n"
            "  3. Set BINANA_PROJECT_PATH to binana project directory"
        )
    
    def analyze_docking_result(
        self,
        receptor_file: str,
        ligand_file: str,
        compound_id: Optional[str] = None,
        output_dir: Optional[str] = None
    ) -> Dict:
        """
        Analyze a single docking result for binding interactions.
        
        This is the DockingVina-specific method that returns a compact
        JSON-compatible format suitable for use in docking workflows.
        
        Args:
            receptor_file: Path to receptor PDBQT file
            ligand_file: Path to ligand PDBQT file
            compound_id: Identifier for this compound
            output_dir: Output directory. If None, uses temporary directory.
            
        Returns:
            Compact analysis results suitable for JSON serialization:
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
                residues = residue_df[
                    residue_df['interaction_type'] == interaction_type
                ]['receptor_residue'].tolist()
                key_residues[interaction_type] = residues[:5]  # Top 5 per type
            
            # Compact result structure
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


# Backward compatibility alias
BindingAnalyzer = DockingVinaBindingAnalyzer


# =============================================================================
# Convenience Functions
# =============================================================================

def analyze_binding_quick(
    receptor_pdbqt: str,
    ligand_pdbqt: str,
    compound_id: Optional[str] = None
) -> Dict:
    """
    Quick binding mode analysis with minimal setup for DockingVina integration.
    
    Args:
        receptor_pdbqt: Path to receptor PDBQT file
        ligand_pdbqt: Path to ligand PDBQT file
        compound_id: Optional compound identifier
        
    Returns:
        Compact analysis results
        
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
        receptor_pdbqt: Path to receptor PDBQT file
        ligand_pdbqt: Path to ligand PDBQT file
        
    Returns:
        Interaction summary or error dict
    """
    result = analyze_binding_quick(receptor_pdbqt, ligand_pdbqt)
    if result.get("success"):
        return result["interaction_summary"]
    else:
        return {"error": result.get("error", "Analysis failed")}


def find_key_residues(
    receptor_pdbqt: str,
    ligand_pdbqt: str,
    top_n: int = 10
) -> List[str]:
    """
    Find the most important interacting residues in DockingVina results.
    
    Args:
        receptor_pdbqt: Path to receptor PDBQT file
        ligand_pdbqt: Path to ligand PDBQT file
        top_n: Number of top residues to return
        
    Returns:
        List of key residue identifiers (e.g., ["A:GLU123", "A:TRP45"])
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


def batch_analyze_docking_results(
    receptor_file: str,
    ligand_files: List[Dict[str, str]],
    output_base_dir: str = "./batch_analysis/"
) -> List[Dict]:
    """
    Batch analyze multiple docking results for DockingVina.
    
    Args:
        receptor_file: Path to receptor PDBQT file
        ligand_files: List of dicts with 'file' and 'compound_id' keys
        output_base_dir: Base directory for output
        
    Returns:
        List of analysis results
        
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


__all__ = [
    'DockingVinaBindingAnalyzer',
    'BindingAnalyzer',
    'analyze_binding_quick',
    'get_interaction_summary',
    'find_key_residues',
    'batch_analyze_docking_results',
    'BINANA_AVAILABLE'
]
