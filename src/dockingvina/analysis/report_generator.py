#!/usr/bin/env python3
"""
Report generation utilities for DockingVina binding analysis.

This module provides utilities for generating various report formats
from BINANA binding analysis results.
"""

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generate reports from DockingVina binding analysis results.
    
    Supports multiple output formats:
    - Summary dictionary (for JSON API responses)
    - CSV reports
    - Enhanced docking results
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialize the report generator.
        
        Args:
            output_dir: Default output directory for reports
        """
        self.output_dir = output_dir
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def generate_summary_dict(self, analysis_result: Dict) -> Dict:
        """
        Generate a compact summary dict suitable for JSON API responses.
        
        Args:
            analysis_result: Raw analysis result from DockingVinaBindingAnalyzer
            
        Returns:
            Compact summary dict
        """
        if not analysis_result.get("success"):
            return {
                "success": False,
                "error": analysis_result.get("error", "Unknown error")
            }
        
        interaction_summary = analysis_result.get("interaction_summary", {})
        
        return {
            "success": True,
            "compound_id": analysis_result.get("compound_id"),
            "total_interactions": interaction_summary.get("total_interactions", 0),
            "unique_residues": interaction_summary.get("unique_residues", 0),
            "interaction_types": interaction_summary.get("interaction_counts", {}),
            "key_residues": interaction_summary.get("key_residues", {})
        }
    
    def generate_csv_report(
        self,
        results: List[Dict],
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate a CSV report from multiple analysis results.
        
        Args:
            results: List of analysis results
            output_path: Output file path. If None, uses default output_dir.
            
        Returns:
            Path to generated CSV file
        """
        if output_path is None:
            if self.output_dir is None:
                raise ValueError("No output path specified and no default output_dir set")
            output_path = str(Path(self.output_dir) / "binding_analysis_report.csv")
        
        # Ensure parent directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Collect all interaction types for headers
        all_interaction_types = set()
        for result in results:
            if result.get("success"):
                interaction_counts = result.get("interaction_summary", {}).get("interaction_counts", {})
                all_interaction_types.update(interaction_counts.keys())
        
        interaction_types = sorted(all_interaction_types)
        
        # Write CSV
        headers = ["compound_id", "total_interactions", "unique_residues"] + interaction_types
        
        with open(output_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for result in results:
                if result.get("success"):
                    summary = result.get("interaction_summary", {})
                    row = {
                        "compound_id": result.get("compound_id", "unknown"),
                        "total_interactions": summary.get("total_interactions", 0),
                        "unique_residues": summary.get("unique_residues", 0)
                    }
                    
                    interaction_counts = summary.get("interaction_counts", {})
                    for itype in interaction_types:
                        row[itype] = interaction_counts.get(itype, 0)
                    
                    writer.writerow(row)
        
        logger.info(f"CSV report generated: {output_path}")
        return output_path
    
    def enhance_docking_results(
        self,
        docking_results: List[Dict],
        binding_analyses: List[Dict]
    ) -> List[Dict]:
        """
        Enhance docking results with binding analysis data.
        
        Args:
            docking_results: List of docking result dicts
            binding_analyses: List of binding analysis results
            
        Returns:
            Enhanced docking results with binding analysis data
        """
        # Create lookup by compound_id
        analysis_lookup = {}
        for analysis in binding_analyses:
            compound_id = analysis.get("compound_id")
            if compound_id:
                analysis_lookup[compound_id] = analysis
        
        enhanced_results = []
        for docking_result in docking_results:
            enhanced = docking_result.copy()
            
            compound_id = docking_result.get("compound_id") or docking_result.get("name")
            if compound_id and compound_id in analysis_lookup:
                analysis = analysis_lookup[compound_id]
                if analysis.get("success"):
                    enhanced["binding_analysis"] = self.generate_summary_dict(analysis)
                else:
                    enhanced["binding_analysis"] = {"success": False, "error": analysis.get("error")}
            
            enhanced_results.append(enhanced)
        
        return enhanced_results
    
    def create_analysis_summary(self, results: List[Dict]) -> Dict:
        """
        Create an overall summary of multiple analysis results.
        
        Args:
            results: List of analysis results
            
        Returns:
            Summary statistics
        """
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        if not successful:
            return {
                "total_analyzed": len(results),
                "successful": 0,
                "failed": len(failed),
                "average_interactions": 0,
                "average_residues": 0,
                "all_interaction_types": []
            }
        
        total_interactions = sum(
            r.get("interaction_summary", {}).get("total_interactions", 0)
            for r in successful
        )
        total_residues = sum(
            r.get("interaction_summary", {}).get("unique_residues", 0)
            for r in successful
        )
        
        all_interaction_types = set()
        for r in successful:
            interaction_counts = r.get("interaction_summary", {}).get("interaction_counts", {})
            all_interaction_types.update(interaction_counts.keys())
        
        return {
            "total_analyzed": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "average_interactions": total_interactions / len(successful),
            "average_residues": total_residues / len(successful),
            "all_interaction_types": sorted(all_interaction_types)
        }


__all__ = ['ReportGenerator']
