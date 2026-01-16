"""
DockingVina FastAPI Application

Main application module for the molecular docking service.
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from dockingvina.config.logging_config import setup_logging, get_log_file_path
from dockingvina.config import storage as storage_config
from dockingvina.services.storage import get_storage
from dockingvina.core.async_processor import AsyncTaskProcessor
from dockingvina.core.task_processor import background_task_runner

# Configure logging
log_file = get_log_file_path()
setup_logging(level="INFO", log_file=log_file)
logger = logging.getLogger(__name__)

# BINANA module availability check
try:
    from dockingvina.analysis.binana_analyzer import BindingAnalyzer, analyze_binding_quick
    from dockingvina.analysis.report_generator import ReportGenerator
    BINANA_AVAILABLE = True
    logger.info("BINANA analysis module loaded successfully")
except ImportError as e:
    logger.warning(f"BINANA analysis not available: {e}")
    BINANA_AVAILABLE = False
    BindingAnalyzer = None
    analyze_binding_quick = None
    ReportGenerator = None


# Global state
async_processor: Optional[AsyncTaskProcessor] = None
background_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    global async_processor, background_task
    
    # === Startup ===
    logger.info("Starting Docking Vina API...")
    
    logger.info("Initializing async task processor...")
    async_processor = AsyncTaskProcessor()
    
    logger.info("Starting background task runner...")
    background_task = asyncio.create_task(background_task_runner())
    
    logger.info("Docking Vina API startup complete")
    yield
    
    # === Shutdown ===
    logger.info("Shutting down Docking Vina API...")
    
    if background_task:
        logger.info("Cancelling background task...")
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            logger.info("Background task cancelled successfully")
    
    if async_processor:
        await async_processor.shutdown()
    
    logger.info("Docking Vina API shutdown complete")


# Create FastAPI application
app = FastAPI(
    lifespan=lifespan,
    title="Docking Vina API",
    description="Molecular docking service using AutoDock Vina with database task management.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Exception Handlers
# =============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.error(f"Validation error: {exc}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body}
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.error(f"HTTP error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# =============================================================================
# Basic Routes
# =============================================================================

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "Docking Vina API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_tasks": async_processor.get_task_count() if async_processor else 0
    }


@app.get("/status")
async def get_status():
    """Get service status."""
    if not async_processor:
        return {"status": "initializing"}
    
    return {
        "status": "running",
        "active_tasks": async_processor.get_task_count(),
        "active_task_ids": async_processor.get_active_tasks(),
        "binana_available": BINANA_AVAILABLE
    }


# =============================================================================
# BINANA Binding Analysis Endpoints
# =============================================================================

@app.post("/analyze_binding")
async def analyze_binding_mode(
    receptor_storage_key: str,
    ligand_storage_key: str,
    compound_id: Optional[str] = None
):
    """
    Analyze binding mode between receptor and ligand using BINANA.
    
    Files are downloaded from SeaweedFS.
    
    Args:
        receptor_storage_key: Receptor file path in SeaweedFS
        ligand_storage_key: Ligand file path in SeaweedFS
        compound_id: Optional identifier for the compound
    
    Returns:
        Binding analysis results including interaction statistics and key residues
    """
    if not BINANA_AVAILABLE:
        raise HTTPException(status_code=503, detail="BINANA analysis not available")
    
    try:
        storage = get_storage()
        
        # Create temporary directory
        storage_config.ensure_temp_dir()
        temp_dir = storage_config.temp_dir / (compound_id or "analysis")
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Download files from SeaweedFS
        receptor_file = temp_dir / "receptor.pdbqt"
        ligand_file = temp_dir / "ligand.pdbqt"
        
        await storage.download_file(receptor_storage_key, receptor_file)
        await storage.download_file(ligand_storage_key, ligand_file)
        
        # Run analysis
        result = analyze_binding_quick(str(receptor_file), str(ligand_file), compound_id)
        
        # Cleanup temporary files
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Analysis failed: {result.get('error', 'Unknown error')}"
            )
        
        return result
        
    except FileNotFoundError as e:
        logger.error(f"File not found in SeaweedFS: {str(e)}")
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
    except Exception as e:
        logger.error(f"Binding analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/analyze_docking_results/{task_id}")
async def analyze_docking_results(task_id: str):
    """
    Analyze binding modes for all results from a docking run.
    
    Reads docking results from SeaweedFS.
    
    Args:
        task_id: Task ID
        
    Returns:
        Enhanced docking results with binding analysis for each compound
    """
    if not BINANA_AVAILABLE:
        raise HTTPException(status_code=503, detail="BINANA analysis not available")
    
    try:
        storage = get_storage()
        
        # Create temporary directory
        storage_config.ensure_temp_dir()
        temp_dir = storage_config.temp_dir / task_id
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Download docking results from SeaweedFS
        results_key = f"jobs/docking/{task_id}/output/dockRes.json"
        results_file = temp_dir / "dockRes.json"
        
        try:
            await storage.download_file(results_key, results_file)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Docking results not found for task: {task_id}"
            )
        
        # Load existing results
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        # Check if binding analysis already exists
        if results and 'binding_analysis' in results[0]:
            logger.info(f"Binding analysis already exists for task {task_id}")
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            return {
                "task_id": task_id,
                "results": results,
                "analysis_status": "existing"
            }
        
        # Download receptor file
        receptor_key = f"jobs/docking/{task_id}/input/receptor.pdbqt"
        receptor_file = temp_dir / "receptor.pdbqt"
        
        try:
            await storage.download_file(receptor_key, receptor_file)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Receptor file not found in task")
        
        # Run binding analysis for each result
        analyzer = BindingAnalyzer(show_output=False)
        enhanced_results = []
        
        for result in results:
            enhanced_result = result.copy()
            
            compound_id = result.get('title', 'unknown')
            ligand_key = f"jobs/docking/{task_id}/output/docked/{compound_id}.pdbqt"
            ligand_file = temp_dir / f"{compound_id}.pdbqt"
            
            try:
                await storage.download_file(ligand_key, ligand_file)
                
                analysis_output_dir = temp_dir / 'binding_analysis' / compound_id
                analysis_output_dir.mkdir(parents=True, exist_ok=True)
                
                analysis_result = analyzer.analyze_docking_result(
                    receptor_file=str(receptor_file),
                    ligand_file=str(ligand_file),
                    compound_id=compound_id,
                    output_dir=str(analysis_output_dir)
                )
                enhanced_result['binding_analysis'] = analysis_result
            except FileNotFoundError:
                enhanced_result['binding_analysis'] = {
                    "error": "Ligand file not found",
                    "success": False
                }
            except Exception as e:
                enhanced_result['binding_analysis'] = {
                    "error": str(e),
                    "success": False
                }
            
            enhanced_results.append(enhanced_result)
        
        # Save enhanced results
        enhanced_file = temp_dir / "dockRes_with_binding.json"
        with open(enhanced_file, 'w') as f:
            json.dump(enhanced_results, f, indent=2)
        
        # Upload enhanced results to SeaweedFS
        enhanced_key = f"jobs/docking/{task_id}/output/dockRes_with_binding.json"
        await storage.upload_file(enhanced_file, enhanced_key)
        
        # Generate summary
        summary = ReportGenerator.create_analysis_summary(enhanced_results)
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return {
            "task_id": task_id,
            "results": enhanced_results,
            "summary": summary,
            "analysis_status": "completed"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Docking results analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/binding_analysis_summary/{task_id}")
async def get_binding_analysis_summary(task_id: str):
    """
    Get summary of binding analysis for a docking run.
    
    Reads from SeaweedFS.
    """
    if not BINANA_AVAILABLE:
        raise HTTPException(status_code=503, detail="BINANA analysis not available")
    
    try:
        storage = get_storage()
        
        summary_key = f"jobs/docking/{task_id}/output/binding_analysis_summary.json"
        
        try:
            summary_bytes = await storage.download_bytes(summary_key)
            summary = json.loads(summary_bytes.decode('utf-8'))
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Binding analysis summary not found for task: {task_id}"
            )
        
        return {
            "task_id": task_id,
            "summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summary retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve summary: {str(e)}")


# =============================================================================
# Server Runner
# =============================================================================

def run_server(host: str = "0.0.0.0", port: int = 8002, reload: bool = False):
    """Run the uvicorn server programmatically."""
    import uvicorn
    uvicorn.run("dockingvina.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    run_server()
