#!/usr/bin/env python3
"""
BINANA Binding Mode Analyzer for DockingVina Integration
Enhanced wrapper for BINANA analysis with dockingvina-specific adaptations.
"""

import subprocess
import json
import pandas as pd
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union


class BindingAnalyzer:
    """Enhanced wrapper for BINANA analysis integrated with DockingVina workflow."""
    
    def __init__(self, binana_path: Optional[str] = None, show_output: bool = False):
        """
        Initialize the BindingAnalyzer for DockingVina integration.
        
        Args:
            binana_path (str, optional): Path to run_binana.py. If None, uses auto-detection.
            show_output (bool): Whether to show detailed BINANA output during analysis.
        """
        if binana_path is None:
            # Try to find BINANA in the projects directory
            self.binana_path = self._find_binana_path()
        else:
            self.binana_path = binana_path
            
        self.show_output = show_output
        
        # Interaction type mappings from BINANA JSON keys to readable names
        self.interaction_keys = {
            "hydrogen_bonds": "hydrogenBonds",
            "salt_bridges": "saltBridges", 
            "hydrophobic_contacts": "hydrophobicContacts",
            "pi_pi_stackings": "piStackings",
            "pi_cation_interactions": "piCationInteractions",
            "metal_complexes": "metalComplexes",
            "close_contacts": "closeContacts"
        }
    
    def _find_binana_path(self) -> str:
        """Auto-detect BINANA installation path."""
        possible_paths = [
            # Look in projects directory for our cleaned BINANA
            "/home/davis/projects/binana/python/run_binana.py",
            "/home/davis/projects/BINANA/python/run_binana.py",
            # Look in current project structure  
            str(Path(__file__).parent.parent / "binana" / "python" / "run_binana.py"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        raise FileNotFoundError(
            "Could not find BINANA installation. Please specify binana_path parameter."
        )
    
    def validate_inputs(self, receptor_file: str, ligand_file: str) -> None:
        """Validate that input files exist and are readable."""
        if not os.path.exists(receptor_file):
            raise FileNotFoundError(f"Receptor file not found: {receptor_file}")
        if not os.path.exists(ligand_file):
            raise FileNotFoundError(f"Ligand file not found: {ligand_file}")
        if not os.path.exists(self.binana_path):
            raise FileNotFoundError(f"BINANA executable not found: {self.binana_path}")
    
    def run_binana(self, receptor_file: str, ligand_file: str, output_dir: str) -> bool:
        """
        Execute BINANA analysis.
        
        Args:
            receptor_file (str): Path to receptor PDBQT file
            ligand_file (str): Path to ligand PDBQT file  
            output_dir (str): Directory to save BINANA output
            
        Returns:
            bool: True if analysis succeeded, False otherwise
        """
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare command
        command = [
            "python3", self.binana_path,
            "-receptor", receptor_file,
            "-ligand", ligand_file,
            "-output_dir", output_dir,
        ]
        
        if self.show_output:
            print(f"Running BINANA analysis...")
            print(f"Command: {' '.join(command)}")
        
        try:
            # Run quietly for integration
            result = subprocess.run(
                command, 
                check=True, 
                capture_output=True, 
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if self.show_output:
                print("✅ BINANA analysis completed successfully!")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ BINANA analysis failed: {e}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"Error details: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            print("❌ BINANA analysis timed out")
            return False
    
    def parse_binana_output(self, output_dir: str) -> Tuple[pd.DataFrame, Dict]:
        """
        Parse BINANA JSON output and extract interaction information.
        
        Args:
            output_dir (str): Directory containing BINANA output files
            
        Returns:
            Tuple[pd.DataFrame, Dict]: Residue interaction summary and full data
        """
        output_json_path = os.path.join(output_dir, 'output.json')
        
        if not os.path.exists(output_json_path):
            raise FileNotFoundError(f"BINANA output file not found: {output_json_path}")
        
        # Load BINANA results
        with open(output_json_path, 'r') as f:
            binana_data = json.load(f)
        
        # Extract receptor residue interactions
        receptor_residue_summary = defaultdict(set)
        
        for interaction_name, json_key in self.interaction_keys.items():
            interactions = binana_data.get(json_key, [])
            
            for entry in interactions:
                for atom in entry.get("receptorAtoms", []):
                    res_name = atom.get("resName", "")
                    res_id = atom.get("resID", "")  
                    chain = atom.get("chain", "")
                    
                    if res_name and res_id:
                        residue_str = f"{chain}:{res_name}{res_id}"
                        receptor_residue_summary[interaction_name].add(residue_str)
        
        # Convert to DataFrame
        residue_rows = []
        for interaction_type, residues in receptor_residue_summary.items():
            for res in sorted(residues):
                residue_rows.append({
                    "interaction_type": interaction_type,
                    "receptor_residue": res
                })
        
        residue_df = pd.DataFrame(residue_rows)
        
        return residue_df, binana_data
    
    def analyze_docking_result(self, 
                             receptor_file: str, 
                             ligand_file: str, 
                             compound_id: Optional[str] = None,
                             output_dir: Optional[str] = None) -> Dict:
        """
        Analyze a single docking result for binding interactions.
        
        Args:
            receptor_file (str): Path to receptor PDBQT file
            ligand_file (str): Path to ligand PDBQT file
            compound_id (str): Identifier for this compound
            output_dir (str): Output directory. If None, uses temporary directory.
            
        Returns:
            Dict: Compact analysis results suitable for JSON serialization
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
            
            # Generate compact statistics for integration
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
                    "output_directory": output_dir
                }
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Analysis parsing failed: {str(e)}", "success": False}
    
    def analyze(self, 
                receptor_file: str, 
                ligand_file: str, 
                output_dir: str = "./binana_analysis/",
                save_csv: bool = True) -> Dict:
        """
        Perform complete binding mode analysis (compatibility method).
        
        Args:
            receptor_file (str): Path to receptor PDBQT file
            ligand_file (str): Path to ligand PDBQT file
            output_dir (str): Output directory for results
            save_csv (bool): Whether to save CSV summary
            
        Returns:
            Dict: Analysis results with DataFrames and statistics
        """
        # Validate inputs
        self.validate_inputs(receptor_file, ligand_file)
        
        # Run BINANA analysis
        if not self.run_binana(receptor_file, ligand_file, output_dir):
            raise RuntimeError("BINANA analysis failed")
        
        # Parse results
        residue_df, full_data = self.parse_binana_output(output_dir)
        
        # Save CSV summary if requested
        csv_path = None
        if save_csv:
            csv_path = os.path.join(output_dir, 'binding_mode_summary.csv')
            residue_df.to_csv(csv_path, index=False)
            
        # Generate statistics
        interaction_stats = residue_df['interaction_type'].value_counts().to_dict()
        unique_residues = residue_df['receptor_residue'].nunique()
        
        results = {
            'residue_summary': residue_df,
            'full_binana_data': full_data,
            'interaction_statistics': interaction_stats,
            'unique_residues_count': unique_residues,
            'output_directory': output_dir,
            'csv_file': csv_path
        }
        
        return results


# Quick analysis functions for convenience
def analyze_binding_quick(receptor_pdbqt: str, ligand_pdbqt: str, compound_id: Optional[str] = None) -> Dict:
    """Quick binding mode analysis with minimal setup."""
    analyzer = BindingAnalyzer()
    return analyzer.analyze_docking_result(receptor_pdbqt, ligand_pdbqt, compound_id)


def get_interaction_summary(receptor_pdbqt: str, ligand_pdbqt: str) -> Dict:
    """Get basic interaction statistics."""
    result = analyze_binding_quick(receptor_pdbqt, ligand_pdbqt)
    if result.get("success"):
        return result["interaction_summary"]
    else:
        return {"error": result.get("error", "Analysis failed")}


def find_key_residues(receptor_pdbqt: str, ligand_pdbqt: str, top_n: int = 10) -> List[str]:
    """Find the most important interacting residues."""
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