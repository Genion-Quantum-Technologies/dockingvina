"""
Report generator for binding analysis results.
"""

import json
import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path


class ReportGenerator:
    """Generate various report formats from binding analysis results."""
    
    @staticmethod
    def generate_summary_dict(analysis_result: Dict) -> Dict:
        """Generate a concise summary dictionary for API responses."""
        if not analysis_result.get("success", False):
            return {"error": analysis_result.get("error", "Analysis failed")}
        
        summary = analysis_result.get("interaction_summary", {})
        return {
            "success": True,
            "total_interactions": summary.get("total_interactions", 0),
            "unique_residues": summary.get("unique_residues", 0),
            "interaction_breakdown": summary.get("interaction_counts", {}),
            "key_binding_residues": summary.get("key_residues", {})
        }
    
    @staticmethod
    def generate_csv_report(binana_data: Dict, output_path: str) -> str:
        """Generate CSV report from BINANA data."""
        interactions = []
        
        type_mapping = {
            "hydrogen_bonds": "hydrogenBonds",
            "salt_bridges": "saltBridges", 
            "hydrophobic_contacts": "hydrophobicContacts",
            "pi_pi_stackings": "piStackings",
            "pi_cation_interactions": "piCationInteractions",
            "metal_complexes": "metalComplexes",
            "close_contacts": "closeContacts"
        }
        
        for interaction_type, json_key in type_mapping.items():
            entries = binana_data.get(json_key, [])
            
            for entry in entries:
                for receptor_atom in entry.get("receptorAtoms", []):
                    for ligand_atom in entry.get("ligandAtoms", []):
                        interaction = {
                            "interaction_type": interaction_type,
                            "receptor_chain": receptor_atom.get("chain", ""),
                            "receptor_residue": receptor_atom.get("resName", ""),
                            "receptor_resid": receptor_atom.get("resID", ""),
                            "receptor_atom": receptor_atom.get("atomName", ""),
                            "ligand_atom": ligand_atom.get("atomName", ""),
                            "distance": entry.get("distance", ""),
                            "angle": entry.get("angle", "")
                        }
                        interactions.append(interaction)
        
        df = pd.DataFrame(interactions)
        df.to_csv(output_path, index=False)
        return output_path
    
    @staticmethod
    def enhance_docking_results(docking_results: List[Dict], 
                              binding_analyses: Dict[str, Dict]) -> List[Dict]:
        """Enhance docking results with binding mode analysis data."""
        enhanced_results = []
        
        for result in docking_results:
            enhanced_result = result.copy()
            
            # Try to find matching binding analysis
            compound_id = result.get("title", "")
            if compound_id in binding_analyses:
                binding_data = binding_analyses[compound_id]
                
                if binding_data.get("success"):
                    enhanced_result["binding_analysis"] = ReportGenerator.generate_summary_dict(binding_data)
                else:
                    enhanced_result["binding_analysis"] = {"error": "Analysis failed"}
            else:
                enhanced_result["binding_analysis"] = {"error": "No analysis available"}
            
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    @staticmethod
    def create_analysis_summary(results: List[Dict]) -> Dict:
        """Create overall analysis summary from multiple results."""
        total_compounds = len(results)
        successful_analyses = sum(1 for r in results if r.get("binding_analysis", {}).get("success", False))
        
        # Aggregate interaction statistics
        all_interaction_counts = {}
        all_residues = set()
        
        for result in results:
            binding_analysis = result.get("binding_analysis", {})
            if binding_analysis.get("success"):
                interaction_counts = binding_analysis.get("interaction_breakdown", {})
                for interaction_type, count in interaction_counts.items():
                    all_interaction_counts[interaction_type] = all_interaction_counts.get(interaction_type, 0) + count
                
                # Collect all residues
                key_residues = binding_analysis.get("key_binding_residues", {})
                for residue_list in key_residues.values():
                    all_residues.update(residue_list)
        
        return {
            "dataset_summary": {
                "total_compounds": total_compounds,
                "successful_analyses": successful_analyses,
                "analysis_success_rate": successful_analyses / total_compounds if total_compounds > 0 else 0
            },
            "aggregate_interactions": all_interaction_counts,
            "unique_binding_residues": sorted(list(all_residues)),
            "total_unique_residues": len(all_residues)
        }