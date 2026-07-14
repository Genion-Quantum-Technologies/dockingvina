#!/usr/bin/env python3
"""
DockingVina Workflow Module

This module provides the complete molecular docking workflow:
- SMILES to PDBQT conversion via Gypsum-DL
- AutoDock Vina docking
- PDBQT to SDF conversion
- BINANA binding mode analysis

Main entry point: vina_docking_from_list()
"""

import argparse
import os
import sys
import uuid
import shutil
import copy
import random
import functools
import logging
from pathlib import Path
from glob import glob
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any

import pandas as pd
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from vina import Vina
from meeko import PDBQTMolecule, RDKitMolCreate

# Project paths
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parent.parent.parent  # src/dockingvina/core -> project root

# Add my_toolsets to path
_toolsets_path = PROJECT_ROOT / "my_toolsets"
if _toolsets_path.exists() and str(_toolsets_path) not in sys.path:
    sys.path.append(str(_toolsets_path))

try:
    from my_toolset.my_utils import get_mol, canonic_smiles, mapper
except ImportError:
    # Fallback mapper implementation
    def mapper(n_jobs):
        def _mapper(func, iterable):
            return list(map(func, iterable))
        return _mapper

# Python environment
PYTHON_BIN = Path(sys.executable)
ENV_ROOT = str(PYTHON_BIN.parent)

# Gypsum-DL path
GYPSUM_PATH = str(PROJECT_ROOT / "gypsum_dl" / "run_gypsum_dl.py")

# Logger
logger = logging.getLogger(__name__)

# =============================================================================
# BINANA Integration
# =============================================================================

BINANA_AVAILABLE = False
BINANA_CONFIG = {"enabled": False}
BindingAnalyzer = None

def _init_binana():
    """Initialize BINANA integration."""
    global BINANA_AVAILABLE, BINANA_CONFIG, BindingAnalyzer
    
    try:
        from dockingvina.analysis.binana_analyzer import (
            DockingVinaBindingAnalyzer,
            BINANA_AVAILABLE as _binana_avail
        )
        
        if _binana_avail:
            BindingAnalyzer = DockingVinaBindingAnalyzer
            BINANA_CONFIG = {
                "enabled": True,
                "auto_analyze": True,
                "timeout": 300,
                "binana_path": None,
                "save_intermediate_files": False,
                "analysis_output_dir": "docked/binding_analysis"
            }
            BINANA_AVAILABLE = True
            logger.info("BINANA analysis available")
        else:
            logger.warning("BINANA module found but not available")
            
    except ImportError as e:
        logger.warning(f"BINANA analysis not available: {e}")
        BINANA_AVAILABLE = False


# Initialize BINANA on module load
_init_binana()


# =============================================================================
# Utility Functions
# =============================================================================

def try_except_decorator(func):
    """Decorator to catch and log exceptions."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            return None
    return wrapper


@try_except_decorator
def pdbqt2sdf(pdbqt_file: str) -> Optional[str]:
    """
    Convert PDBQT file to SDF format.
    
    Args:
        pdbqt_file: Path to PDBQT file
        
    Returns:
        Path to generated CSV file, or None on failure
    """
    pdbqt_path = Path(pdbqt_file)
    pdbqt_mol = PDBQTMolecule.from_file(pdbqt_file, skip_typing=True)
    
    for imol in pdbqt_mol:
        rdkitmol = RDKitMolCreate.from_pdbqt_mol(copy.deepcopy(imol))
        rdkitmol0 = rdkitmol[0]
        sdf_file = f'{pdbqt_path.parent}/{imol.name}-p{imol.pose_id}.sdf'
        
        writer = Chem.SDWriter(sdf_file)
        rdkitmol0.SetProp("vinaScore", str(imol.score))
        ismi = Chem.MolToSmiles(Chem.RemoveHs(rdkitmol0))
        rdkitmol0.SetProp("smiles", ismi)
        writer.write(rdkitmol0)
        writer.close()

        result_dict = {
            'title': [imol.name],
            'pose': [imol.pose_id],
            'score': [imol.score],
            'smiles': [ismi],
            'file': [f"{imol.name}-p{imol.pose_id}.sdf"]
        }
        df = pd.DataFrame.from_dict(result_dict)
        csv_path = f'{pdbqt_path.parent}/{imol.name}-p{imol.pose_id}.csv'
        df.to_csv(csv_path, index=False)
        
        return csv_path  # Only output Top1 pose
    
    return None


def csv2gypSmi(input_csv: str, dir: str = '.') -> str:
    """
    Convert input CSV to Gypsum-DL SMILES format.
    
    Args:
        input_csv: Path to input CSV file
        dir: Output directory
        
    Returns:
        Path to generated .smi file
    """
    df_input = pd.read_csv(input_csv)
    smiles_headers = ['SMILES', 'Smiles']
    out_path = f'{dir}/input.smi'
    
    if 'smiles' not in df_input.columns:
        smiles_exists = False
        for header in smiles_headers:
            if header in df_input.columns:
                df_input['smiles'] = df_input[header]
                smiles_exists = True
                break
        if not smiles_exists:
            raise ValueError('Input file must have a smiles column!')
    
    if 'title' not in df_input.columns:
        for idx, _ in df_input.iterrows():
            df_input.loc[idx, 'title'] = f"ID-{idx}"
    
    df_input[['smiles', 'title']].to_csv(out_path, sep='\t', index=False)
    return out_path


def smi2pdbqt(
    input_smi: str,
    min_ph: float = 5.0,
    max_ph: float = 9.0,
    num_processors: int = None,
    dir: str = '.'
) -> None:
    """
    Convert SMILES to PDBQT files via Gypsum-DL.
    
    Args:
        input_smi: Path to input .smi file
        min_ph: Minimum pH for protonation
        max_ph: Maximum pH for protonation
        num_processors: Number of parallel processors
        dir: Working directory
    """
    if num_processors is None:
        num_processors = os.cpu_count() or 1
    
    gypsum_output_dir = f"{dir}/gypsumFolder"
    os.makedirs(gypsum_output_dir, exist_ok=True)
    
    logger.info("Running Gypsum-DL for molecule preparation...")
    gypsum_cmd = (
        f"mpirun -n {num_processors} python3 -m mpi4py "
        f"{GYPSUM_PATH} --source {input_smi} --output_folder {dir}/gypsumFolder "
        f"--min_ph {min_ph} --max_ph {max_ph} --pka_precision 1 "
        f"--skip_optimize_geometry --2d_output_only --use_durrant_lab_filters "
        f"--max_variants_per_compound 5"
    )
    
    result = os.system(gypsum_cmd)
    if result != 0:
        logger.warning("Gypsum-DL had issues, continuing with available output...")
    
    # Process Gypsum-DL output
    smi_list = []
    try:
        supplier = Chem.SDMolSupplier(f"{dir}/gypsumFolder/gypsum_dl_success.sdf")
        mol_name_count = {}
        
        for mol in supplier:
            if mol is not None:
                mol_name = mol.GetProp('_Name') if mol.HasProp('_Name') else 'NoName'
                if mol_name not in mol_name_count:
                    mol_name_count[mol_name] = 1
                else:
                    mol_name_count[mol_name] += 1
                
                smi = mol.GetProp('SMILES') if mol.HasProp('SMILES') else ''
                if smi:
                    smi_list.append([smi, f"{mol_name}-{mol_name_count[mol_name]}"])
                    
    except Exception as e:
        logger.warning(f"Could not read Gypsum-DL output: {e}")
    
    # Fallback: process original SMILES directly
    if not smi_list:
        logger.warning("No molecules from Gypsum-DL, trying direct SMILES processing...")
        try:
            original_df = pd.read_csv(input_smi, sep='\t', header=None, names=['smiles', 'title'])
            for idx, row in original_df.iterrows():
                smiles = row['smiles']
                title = row['title'] if pd.notna(row['title']) else f"mol_{idx}"
                smi_list.append([smiles, title])
        except Exception as e:
            raise RuntimeError(f"Failed to process SMILES: {e}")
    
    if not smi_list:
        raise RuntimeError("No valid molecules to process")
    
    df_smi = pd.DataFrame(smi_list, columns=['smiles', 'title'])
    df_smi.to_csv(f'{dir}/input_prepared.smi', sep='\t', index=False, header=False)
    
    # Generate 3D coordinates
    _generate_3d_and_pdbqt(dir)


def _generate_3d_and_pdbqt(dir: str) -> None:
    """Generate 3D coordinates and convert to PDBQT."""
    # Try Open Babel first
    babel_cmd = f"{ENV_ROOT}/obabel -ismi input_prepared.smi -osdf -O input_prepared.sdf --gen3d"
    result = os.system(babel_cmd)
    
    sdf_valid = False
    if os.path.exists(f'{dir}/input_prepared.sdf'):
        try:
            test_supplier = Chem.SDMolSupplier(f'{dir}/input_prepared.sdf')
            valid_mols = sum(1 for mol in test_supplier if mol is not None)
            if valid_mols > 0:
                sdf_valid = True
                logger.info(f"Open Babel generated {valid_mols} valid molecules")
        except:
            pass
    
    # Fallback to RDKit
    if not sdf_valid:
        logger.info("Using RDKit for 3D coordinate generation...")
        _generate_3d_rdkit(dir)
    
    # Convert to PDBQT
    _convert_to_pdbqt(dir)


def _generate_3d_rdkit(dir: str) -> None:
    """Generate 3D coordinates using RDKit."""
    df_molecules = pd.read_csv(f'{dir}/input_prepared.smi', sep='\t', header=None, names=['smiles', 'title'])
    sdf_writer = Chem.SDWriter(f'{dir}/input_prepared.sdf')
    successful_count = 0
    
    for _, row in df_molecules.iterrows():
        try:
            mol = Chem.MolFromSmiles(row['smiles'])
            if mol is None:
                continue
            
            mol = Chem.AddHs(mol, explicitOnly=False, addCoords=False)
            
            # Try multiple embedding methods
            embed_success = False
            for method in [
                lambda m: AllChem.EmbedMolecule(m, AllChem.ETKDG()),
                lambda m: AllChem.EmbedMolecule(m, AllChem.ETKDG(), randomSeed=42),
                lambda m: AllChem.EmbedMolecule(m, randomSeed=42),
            ]:
                try:
                    if method(mol) == 0:
                        embed_success = True
                        break
                except:
                    pass
            
            if embed_success:
                try:
                    AllChem.OptimizeMolecule(mol, maxIters=200)
                except:
                    pass
                
                mol.SetProp('_Name', str(row['title']))
                sdf_writer.write(mol)
                successful_count += 1
                
        except Exception as e:
            logger.warning(f"Error processing molecule {row['title']}: {e}")
    
    sdf_writer.close()
    logger.info(f"RDKit generated 3D coordinates for {successful_count} molecules")
    
    if successful_count == 0:
        raise RuntimeError("No molecules could be converted to 3D structures")


def _convert_to_pdbqt(dir: str) -> None:
    """Convert SDF to PDBQT format."""
    logger.info("Converting SDF to PDBQT format...")
    
    # Try with keep_nonpolar_hydrogens
    prepare_cmd = f"{ENV_ROOT}/mk_prepare_ligand.py -i input_prepared.sdf --multimol_outdir pdbqts --keep_nonpolar_hydrogens"
    result = os.system(prepare_cmd)
    
    if result != 0:
        # Fallback without the flag
        prepare_cmd_backup = f"{ENV_ROOT}/mk_prepare_ligand.py -i input_prepared.sdf --multimol_outdir pdbqts"
        os.system(prepare_cmd_backup)
    
    pdbqt_files = glob(f"{dir}/pdbqts/*.pdbqt")
    logger.info(f"Generated {len(pdbqt_files)} PDBQT files")
    
    if not pdbqt_files:
        # Try alternative method
        try:
            basic_cmd = f"{ENV_ROOT}/mk_prepare_ligand.py -i input_prepared.sdf --multimol_outdir pdbqts --rigid_macrocycles"
            os.system(basic_cmd)
            pdbqt_files = glob(f"{dir}/pdbqts/*.pdbqt")
        except:
            pass
    
    if not pdbqt_files:
        raise RuntimeError("Failed to generate any PDBQT files for docking")


def vina_dock(
    lig: str,
    recpt: str = '',
    center: List[float] = None,
    box_size: List[float] = None,
    dir: str = '.',
    exhaustiveness: int = 8,
    n_poses: int = 10
) -> None:
    """
    Perform molecular docking with AutoDock Vina.
    
    Args:
        lig: Path to ligand PDBQT file
        recpt: Path to receptor PDBQT file
        center: Docking box center [x, y, z]
        box_size: Docking box size [x, y, z]
        dir: Working directory
        exhaustiveness: Vina exhaustiveness parameter
        n_poses: Number of poses to generate
    """
    if center is None:
        center = [0, 0, 0]
    if box_size is None:
        box_size = [20, 20, 20]
    
    lig_path = Path(lig)
    docked_dir = f'{dir}/docked'
    
    # Check for existing results
    if os.path.exists(f'{docked_dir}/{lig_path.stem}.pdbqt'):
        logger.info(f"Using existing results for {lig_path.stem}")
        if not os.path.exists(f"{docked_dir}/{lig_path.stem}-p0.csv"):
            try:
                pdbqt2sdf(f"{docked_dir}/{lig_path.stem}.pdbqt")
            except Exception as e:
                logger.warning(f"Error generating CSV for {lig_path.stem}: {e}")
        return
    
    try:
        # Validate files
        if not os.path.exists(recpt):
            raise FileNotFoundError(f"Receptor file not found: {recpt}")
        if not os.path.exists(lig):
            raise FileNotFoundError(f"Ligand file not found: {lig}")
        
        with open(lig, 'r') as f:
            ligand_content = f.read().strip()
            if len(ligand_content) < 10:
                raise ValueError(f"Ligand file appears empty: {lig}")
        
        logger.info(f"Docking {lig_path.stem} with center={center}, box_size={box_size}")
        
        # Setup Vina
        # ADR 0012 P0-3: 必须显式传 cpu=。Vina 的默认 cpu=0 表示"自动用满所有核",
        # 而它读的是宿主机核数(hardware_concurrency)、读不到 cgroup 限额;这个函数又跑在
        # multiprocessing.Pool(n_jobs) 的每个子进程里 → n_jobs × 宿主机核数 个线程
        # (8 × 24 ≈ 192)。并行度本来就由 Pool 提供,所以每个子进程只需要 1 个线程。
        v = Vina(sf_name='vina', cpu=int(os.environ.get("VINA_CPU_PER_WORKER", "1")))
        
        # Set receptor
        try:
            v.set_receptor(str(recpt))
        except Exception:
            v.set_receptor(rigid_pdbqt_filename=str(recpt))
        
        # Set ligand
        v.set_ligand_from_file(str(lig))
        
        # Compute maps and dock
        v.compute_vina_maps(
            center=np.array(center, dtype=float),
            box_size=np.array(box_size, dtype=float)
        )
        
        v.dock(exhaustiveness=exhaustiveness, n_poses=n_poses)
        
        # Write results
        os.makedirs(docked_dir, exist_ok=True)
        output_file = f'{docked_dir}/{lig_path.stem}.pdbqt'
        v.write_poses(output_file, n_poses=5, overwrite=True)
        
        # Generate CSV
        pdbqt2sdf(output_file)
        logger.info(f"Docking completed for {lig_path.stem}")
        
    except Exception as e:
        logger.error(f"Docking failed for {lig}: {e}")
        
        # Handle assertion errors gracefully
        if "Assertion failed" in str(e) or "nrm >= epsilon_fl" in str(e):
            error_dir = f'{dir}/errors'
            os.makedirs(error_dir, exist_ok=True)
            with open(f'{error_dir}/{lig_path.stem}_error.txt', 'w') as f:
                f.write(f"Docking failed: {e}\n")
            return
        
        raise


def read_csv(file_path: str) -> pd.DataFrame:
    """Read a CSV file."""
    return pd.read_csv(file_path)


def combine_csv(file_paths: List[str]) -> pd.DataFrame:
    """Combine multiple CSV files into one DataFrame."""
    with ThreadPoolExecutor() as executor:
        dataframes = list(executor.map(read_csv, file_paths))
    return pd.concat(dataframes, ignore_index=True)


def clean_intermediate_files(work_dir: str) -> None:
    """Clean up intermediate files, keeping docking results."""
    keep_files = {"70.csv", "dockRes.json", "protein_7UDP.pdbqt"}
    
    paths_to_remove = [
        f"{work_dir}/input.smi",
        f"{work_dir}/input_prepared.smi",
        f"{work_dir}/input_prepared.sdf",
        f"{work_dir}/gypsumFolder",
        f"{work_dir}/pdbqts",
    ]
    
    extra_patterns = [
        f"{work_dir}/*.sdf",
        f"{work_dir}/*.pdbqt",
        f"{work_dir}/*.csv",
    ]
    
    for path in paths_to_remove:
        if os.path.isfile(path) and os.path.basename(path) not in keep_files:
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
    
    for pattern in extra_patterns:
        for f in glob(pattern):
            if os.path.basename(f) not in keep_files:
                os.remove(f)
    
    logger.info(f"✅ Intermediate files cleaned. Results in: {work_dir}/docked/")


def perform_binding_analysis(
    df_res: pd.DataFrame,
    receptor_path: str,
    parent_path: str
) -> pd.DataFrame:
    """
    Perform BINANA binding mode analysis on docking results.
    
    Args:
        df_res: DataFrame with docking results
        receptor_path: Path to receptor PDBQT file
        parent_path: Parent directory containing docking results
        
    Returns:
        Enhanced DataFrame with binding analysis data
    """
    import json
    
    enhanced_results = []
    
    if not BINANA_AVAILABLE or BindingAnalyzer is None:
        logger.warning("BINANA not available, skipping binding analysis")
        for _, row in df_res.iterrows():
            enhanced_row = row.copy()
            enhanced_row['binding_analysis'] = {"error": "BINANA not available", "success": False}
            enhanced_results.append(enhanced_row)
    else:
        try:
            analyzer = BindingAnalyzer(show_output=False)
            
            for idx, row in df_res.iterrows():
                enhanced_row = row.copy()
                compound_id = row.get('title', f'compound_{idx}')
                ligand_pdbqt = os.path.join(parent_path, 'docked', f'{compound_id}.pdbqt')
                
                if not os.path.exists(ligand_pdbqt):
                    enhanced_row['binding_analysis'] = {"error": "Ligand not found", "success": False}
                else:
                    try:
                        binana_output_dir = os.path.join(parent_path, 'docked', 'binding_analysis', compound_id)
                        
                        result = analyzer.analyze_docking_result(
                            receptor_file=receptor_path,
                            ligand_file=ligand_pdbqt,
                            compound_id=compound_id,
                            output_dir=binana_output_dir
                        )
                        
                        # Move binding summary file
                        if result.get('success'):
                            old_csv = os.path.join(binana_output_dir, 'binding_mode_summary.csv')
                            if os.path.exists(old_csv):
                                new_csv = os.path.join(parent_path, 'docked', 'binding_analysis',
                                                       f"{compound_id}_binding_mode_summary.csv")
                                shutil.move(old_csv, new_csv)
                                if 'analysis_files' in result:
                                    result['analysis_files']['binding_mode_summary'] = new_csv
                        
                        enhanced_row['binding_analysis'] = result
                        
                    except Exception as e:
                        enhanced_row['binding_analysis'] = {"error": str(e), "success": False}
                
                enhanced_results.append(enhanced_row)
                
        except Exception as e:
            logger.error(f"BINANA initialization failed: {e}")
            for _, row in df_res.iterrows():
                enhanced_row = row.copy()
                enhanced_row['binding_analysis'] = {"error": str(e), "success": False}
                enhanced_results.append(enhanced_row)
    
    enhanced_df = pd.DataFrame(enhanced_results)
    
    # Save summary
    try:
        docked_dir = os.path.join(parent_path, 'docked')
        os.makedirs(docked_dir, exist_ok=True)
        
        binding_summary_path = os.path.join(docked_dir, 'binding_analysis_summary.json')
        successful = [r for r in enhanced_results if r.get('binding_analysis', {}).get('success')]
        
        summary = {
            "total_compounds": len(enhanced_results),
            "successful_analyses": len(successful),
            "analysis_success_rate": len(successful) / len(enhanced_results) if enhanced_results else 0,
            "binana_available": BINANA_AVAILABLE,
            "timestamp": pd.Timestamp.now().isoformat()
        }
        
        with open(binding_summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"✅ Binding analysis: {len(successful)}/{len(enhanced_results)} successful")
        
        # Cleanup compound folders
        binding_dir = os.path.join(docked_dir, 'binding_analysis')
        if os.path.exists(binding_dir):
            for item in os.listdir(binding_dir):
                item_path = os.path.join(binding_dir, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path, ignore_errors=True)
                    
    except Exception as e:
        logger.warning(f"Could not save binding analysis summary: {e}")
    
    return enhanced_df


# =============================================================================
# Main API
# =============================================================================

def vina_docking_from_list(
    ligands: List[Dict[str, str]],
    receptor_pdbqt: str,
    vina_box_config: Dict[str, Any] = None,
    min_ph: float = 6.0,
    max_ph: float = 8.0,
    n_jobs: int = 8,
    exhaustiveness: int = 8,
    n_poses: int = 10
) -> str:
    """
    Molecular docking interface: process ligand list with Vina box configuration.
    
    Args:
        ligands: List of molecule dicts, e.g., [{"smiles": "C=CCNC...", "title": "ID1"}, ...]
        receptor_pdbqt: Path to receptor PDBQT file
        vina_box_config: Vina box config dict with 'center' and 'box_size'
        min_ph: Minimum pH value for protonation
        max_ph: Maximum pH value for protonation
        n_jobs: Number of parallel jobs
        exhaustiveness: Vina exhaustiveness parameter
        n_poses: Number of poses to generate
        
    Returns:
        Path to run directory containing results
        
    Example:
        >>> ligands = [
        ...     {"smiles": "CCO", "title": "ethanol"},
        ...     {"smiles": "CC(=O)O", "title": "acetic_acid"}
        ... ]
        >>> vina_box = {
        ...     "center": [10.0, 20.0, 30.0],
        ...     "box_size": [20, 20, 20]
        ... }
        >>> result_dir = vina_docking_from_list(ligands, "protein.pdbqt", vina_box)
    """
    import json
    
    if vina_box_config is None:
        raise ValueError("vina_box_config must be provided with 'center' and 'box_size'")
    
    if 'center' not in vina_box_config:
        raise ValueError("vina_box_config must contain 'center' key")
    
    orig_cwd = os.getcwd()
    
    # Validate receptor
    recept_path = Path(receptor_pdbqt).absolute()
    if not recept_path.exists():
        raise FileNotFoundError(f"Receptor file not found: {recept_path}")
    
    # Validate ligands
    if not isinstance(ligands, list):
        raise ValueError("ligands must be a list")
    for mol in ligands:
        if 'smiles' not in mol or 'title' not in mol:
            raise ValueError("Each ligand must have 'smiles' and 'title' keys")
    
    # Create run directory
    orig_parent = recept_path.parent
    run_id = uuid.uuid4().hex
    run_dir = orig_parent / run_id
    os.makedirs(run_dir, exist_ok=True)
    
    # Write input CSV
    csv_path = run_dir / "input.csv"
    df_lig = pd.DataFrame(ligands)
    df_lig.to_csv(csv_path, index=False)
    
    # Change to run directory
    os.chdir(run_dir)
    parent_path = str(run_dir)
    
    try:
        # Prepare molecules
        smi_path = csv2gypSmi(str(csv_path), dir=parent_path)
        smi2pdbqt(smi_path, min_ph=min_ph, max_ph=max_ph, num_processors=n_jobs, dir=parent_path)
        
        # Get ligand files
        pdbqt_list = glob(f"{parent_path}/pdbqts/*.pdbqt")
        if not pdbqt_list:
            raise RuntimeError("No PDBQT files generated")
        
        logger.info(f"Found {len(pdbqt_list)} PDBQT files for docking")
        random.shuffle(pdbqt_list)
        
        # Dock all ligands
        box_size = vina_box_config.get('box_size', [20, 20, 20])
        vina_dock_partial = partial(
            vina_dock,
            recpt=recept_path.as_posix(),
            center=vina_box_config['center'],
            box_size=box_size,
            dir=parent_path,
            exhaustiveness=exhaustiveness,
            n_poses=n_poses
        )
        mapper(n_jobs)(vina_dock_partial, pdbqt_list)
        
        # Combine results
        csv_paths = glob(f"{parent_path}/docked/*.csv")
        if csv_paths:
            df_res = combine_csv(csv_paths)
            df_res = df_res.sort_values(by='score', ascending=True)
        else:
            df_res = pd.DataFrame(columns=['title', 'pose', 'score', 'smiles', 'file', 'protein_path'])
        
        df_res['protein_path'] = str(recept_path)
        
        # Run BINANA analysis
        if BINANA_AVAILABLE and BINANA_CONFIG.get("auto_analyze", True) and len(df_res) > 0:
            logger.info(f"Running binding analysis for {len(df_res)} results...")
            df_res = perform_binding_analysis(df_res, str(recept_path), parent_path)
        
        # Save results
        df_res.to_json(f"{parent_path}/dockRes.json", orient="records", force_ascii=False, indent=2)
        
        # Cleanup
        clean_intermediate_files(parent_path)
        
    finally:
        os.chdir(orig_cwd)
    
    return str(run_dir)


__all__ = [
    'vina_docking_from_list',
    'vina_dock',
    'pdbqt2sdf',
    'csv2gypSmi',
    'smi2pdbqt',
    'perform_binding_analysis',
    'clean_intermediate_files',
    'BINANA_AVAILABLE',
    'BINANA_CONFIG',
]


if __name__ == "__main__":
    print("This module is designed to be imported.")
    print("Use vina_docking_from_list() function for docking workflows.")
