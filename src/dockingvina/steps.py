"""Stateless CLI step for Argo Workflows (ADR 0012 P1/P2).

    python -m dockingvina.steps dock --work-dir /work    # CPU only

Replaces `core/task_processor.py`, whose "claim" was a bare
`SELECT ... WHERE status='pending' AND task_type='docking'` + `fetchall()` — no row lock,
no LIMIT, and on an autocommit connection. Its correctness rested entirely on `replicas: 1`;
scaling it to 2 would have double-run every job. That whole class of bug is gone: Argo owns
the claim, and there is nothing left here to get wrong.

## One step, not three

The design sketched `prep → dock → analyze`. In the code they are not separable: they are
phases *inside* `vina_docking_from_list()`, which chdirs into a run directory and drives
its own `multiprocessing.Pool` across ligands. Splitting them would mean surgery on the
science code for no benefit — docking has no GPU phase, so there is no card to hand back
mid-run, and on one node sharding across pods cannot extract more cores than the Pool
already does.

What docking actually needed was a CPU quota and a deadline, and it now has both:
`activeDeadlineSeconds` in the template (it had NO timeout at all, while `exhaustiveness`
is quadratic), and `VINA_CPU_PER_WORKER=1` so that `Pool(n_jobs)` × Vina's default
`cpu=0` ("use every core on the host, ignoring cgroups") stops meaning ~192 threads.
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("docking-step")


def _load_params(work_dir: Path) -> Dict[str, Any]:
    return json.loads((work_dir / "params.json").read_text())


def _write_ligands_csv(ligands: list[dict], dest: Path) -> int:
    """Same shape task_processor._create_smiles_file produced."""
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write("SMILES,Title\n")
        for lig in ligands:
            fh.write(f"{lig.get('smiles', '')},{lig.get('title', '')}\n")
    return len(ligands)


def stage_dock(work_dir: Path, params: Dict[str, Any]) -> None:
    from dockingvina.core.vina_workflow import vina_docking_from_list

    inp = work_dir / "input"
    out = work_dir / "output"
    out.mkdir(parents=True, exist_ok=True)

    ligands = params.get("ligands") or []
    if not ligands:
        raise ValueError("input.json carries no `ligands`")

    receptor = inp / "receptor.pdbqt"
    if not receptor.exists():
        raise FileNotFoundError(
            "receptor.pdbqt is missing — the docking receptor lives at "
            "`uploads/{user_id}/…` (pointed to by receptor_storage_key), not under the "
            "job prefix, and `astra-step fetch` is responsible for pulling it"
        )

    ligands_csv = inp / "ligands.csv"
    n = _write_ligands_csv(ligands, ligands_csv)

    vina_box = {
        "center": [
            float(params.get("center_x", 0.0)),
            float(params.get("center_y", 0.0)),
            float(params.get("center_z", 0.0)),
        ],
        "box_size": [
            float(params.get("box_size_x", 20.0)),
            float(params.get("box_size_y", 20.0)),
            float(params.get("box_size_z", 20.0)),
        ],
        "exhaustiveness": int(params.get("exhaustiveness", 8)),
        "n_poses": int(params.get("n_poses", 10)),
    }
    logger.info("docking %d ligand(s); box=%s", n, vina_box)

    # vina_docking_from_list writes its run dir as a SIBLING OF THE RECEPTOR (not into any
    # output dir we choose) and returns the path — an old quirk we work around rather than
    # change, exactly as the worker did.
    run_dir = Path(
        vina_docking_from_list(
            ligands=ligands,
            receptor_pdbqt=str(receptor),
            vina_box_config=vina_box,
            min_ph=float(params.get("min_ph", 6.0)),
            max_ph=float(params.get("max_ph", 8.0)),
            n_jobs=int(params.get("n_jobs", 8)),
            exhaustiveness=int(params.get("exhaustiveness", 8)),
            n_poses=int(params.get("n_poses", 10)),
        )
    )

    res = run_dir / "dockRes.json"
    if not res.exists():
        raise RuntimeError(f"docking produced no dockRes.json in {run_dir}")
    shutil.copy2(res, out / "dockRes.json")

    docked = run_dir / "docked"
    if docked.is_dir():
        dst = out / "docked"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(docked, dst)

    scored = json.loads(res.read_text())
    logger.info("docked %d pose record(s)", len(scored))


STAGES = {"dock": stage_dock}


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    p = argparse.ArgumentParser(prog="dockingvina.steps")
    p.add_argument("stage", choices=sorted(STAGES))
    p.add_argument("--work-dir", default="/work")
    args = p.parse_args()

    work_dir = Path(args.work_dir)
    params = _load_params(work_dir)
    logger.info("stage=%s work_dir=%s", args.stage, work_dir)

    try:
        STAGES[args.stage](work_dir, params)
    except Exception as e:
        print(f"FATAL [{args.stage}] {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
