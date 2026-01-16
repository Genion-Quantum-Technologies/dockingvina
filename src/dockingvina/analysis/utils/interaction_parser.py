"""
Interaction parser utilities for BINANA analysis results.
"""

import json
from typing import Dict, List
from pathlib import Path


class InteractionParser:
    """Parser for BINANA output with enhanced data extraction."""
    
    # Mapping from internal names to BINANA JSON keys
    TYPE_MAPPING = {
        "hydrogen_bonds": "hydrogenBonds",
        "salt_bridges": "saltBridges", 
        "hydrophobic_contacts": "hydrophobicContacts",
        "pi_pi_stackings": "piStackings",
        "pi_cation_interactions": "piCationInteractions",
        "metal_complexes": "metalComplexes",
        "close_contacts": "closeContacts"
    }
    
    @staticmethod
    def parse_json_output(json_path: str) -> Dict:
        """
        Parse BINANA JSON output file.
        
        Args:
            json_path: Path to the BINANA output.json file
            
        Returns:
            Parsed JSON data as dictionary
        """
        with open(json_path, 'r') as f:
            return json.load(f)
    
    @classmethod
    def extract_residue_contacts(cls, binana_data: Dict, interaction_type: str) -> List[Dict]:
        """
        Extract residue contact information for specific interaction type.
        
        Args:
            binana_data: Parsed BINANA output data
            interaction_type: Type of interaction to extract
            
        Returns:
            List of interaction details
        """
        interactions = []
        
        json_key = cls.TYPE_MAPPING.get(interaction_type, interaction_type)
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
    
    @classmethod
    def get_unique_residues(cls, binana_data: Dict) -> List[str]:
        """
        Get list of all unique receptor residues involved in interactions.
        
        Args:
            binana_data: Parsed BINANA output data
            
        Returns:
            Sorted list of unique residue identifiers (e.g., ["A:GLU123", "A:TRP45"])
        """
        residues = set()
        
        for json_key in cls.TYPE_MAPPING.values():
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
    
    @classmethod
    def summarize_interactions(cls, binana_data: Dict) -> Dict[str, int]:
        """
        Get count summary of each interaction type.
        
        Args:
            binana_data: Parsed BINANA output data
            
        Returns:
            Dictionary mapping interaction type to count
        """
        summary = {}
        
        for interaction_type, json_key in cls.TYPE_MAPPING.items():
            interactions = binana_data.get(json_key, [])
            summary[interaction_type] = len(interactions)
        
        return summary
    
    @classmethod
    def get_all_interactions(cls, binana_data: Dict) -> List[Dict]:
        """
        Extract all interactions from BINANA output.
        
        Args:
            binana_data: Parsed BINANA output data
            
        Returns:
            List of all interaction details
        """
        all_interactions = []
        
        for interaction_type in cls.TYPE_MAPPING.keys():
            interactions = cls.extract_residue_contacts(binana_data, interaction_type)
            all_interactions.extend(interactions)
        
        return all_interactions


__all__ = ['InteractionParser']
