"""
SLURM Task Manager Package
Modular helper for SLURM job submission and execution
"""

__version__ = "1.0.0"

from .config import SlurmConfig
from .batch import BatchManager
from .interactive import InteractiveManager
from .job_parser import JobParser
from .script_generator import ScriptGenerator
from .equilibration_generator import EquilibrationGenerator
from .production_chunker import ProductionChunker
from .utils import setup_logging, validate_paths

__all__ = [
    'SlurmConfig', 
    'BatchManager', 
    'InteractiveManager',
    'JobParser',
    'ScriptGenerator',
    'EquilibrationGenerator',
    'ProductionChunker',
    'setup_logging', 
    'validate_paths'
    ]