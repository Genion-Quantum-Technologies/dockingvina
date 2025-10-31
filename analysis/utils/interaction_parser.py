"""
Interaction parser utilities for BINANA analysis results.
"""

import json
from typing import Dict, List, Tuple
from pathlib import Path


class InteractionParser:
    """Parser for BINANA output with enhanced data extraction."""
    
    @staticmethod
    def parse_json_output(json_path: str) -> Dict:
        """Parse BINANA JSON output file."""
        with open(json_path, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def extract_residue_contacts(binana_data: Dict, interaction_type: str) -> List[Dict]:
        """Extract residue contact information for specific interaction type."""
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
        
        json_key = type_mapping.get(interaction_type, interaction_type)
        entries = binana_data.get(json_key, [])
        
        for entry in entries:
            interaction_info = {
                "type": interaction_type,
                "receptor_atoms": entry.get("receptorAtoms", []),
                "ligand_atoms": entry.get("ligandAtoms", []),
                "distance": entry.get("distance", None),
                "angle": entry.get("angle", None)
            }
            interactions.append(interaction_info)
        
        return interactions
    
    @staticmethod
    def get_unique_residues(binana_data: Dict) -> List[str]:
        """Get list of all unique receptor residues involved in interactions."""
        residues = set()
        
        type_mapping = {
            "hydrogen_bonds": "hydrogenBonds",
            "salt_bridges": "saltBridges", 
            "hydrophobic_contacts": "hydrophobicContacts",
            "pi_pi_stackings": "piStackings",
            "pi_cation_interactions": "piCationInteractions",
            "metal_complexes": "metalComplexes",
            "close_contacts": "closeContacts"
        }
        
        for json_key in type_mapping.values():
            interactions = binana_data.get(json_key, [])
            
            for entry in interactions:
                for atom in entry.get("receptorAtoms", []):
                    res_name = atom.get("resName", "")
                    res_id = atom.get("resID", "")  
                    chain = atom.get("chain", "")
                    
                    if res_name and res_id:
                        residue_str = f"{chain}:{res_name}{res_id}"
                        residues.add(residue_str)
        
        return sorted(list(residues))
    
    @staticmethod
    def summarize_interactions(binana_data: Dict) -> Dict[str, int]:
        """Get count summary of each interaction type."""
        summary = {}
        
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
            interactions = binana_data.get(json_key, [])
            summary[interaction_type] = len(interactions)
        
        return summary