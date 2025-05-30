#!/bin/bash
# SLURM Task Manager - Production Wrapper for PCSS Eagle Altair
# Compatible with modelmembrane.yaml workflow

set -euo pipefail

# Configuration
PYTHON_MODULE="taskmanager"
DEFAULT_CONFIG=".slurmparams"

error_exit() {
    echo "Error: $1" >&2
    exit 1
}

check_environment() {
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        error_exit "python3 is required but not found"
    fi
    
    # Check for SLURM
    if ! command -v sbatch &> /dev/null; then
        error_exit "sbatch (SLURM) is required but not found"
    fi
    
    # Check if taskmanager module is available
    if ! python3 -c "import $PYTHON_MODULE" 2>/dev/null; then
        error_exit "taskmanager module not found. Install with: pip install -e ."
    fi
    
    # Check for GROMACS module (Eagle/Altair specific)
    if ! module avail gromacs 2>/dev/null | grep -q gromacs; then
        echo "Warning: GROMACS module may not be available" >&2
    fi
}

show_usage() {
    cat << 'EOF'
SLURM Task Manager - Production Version for Eagle/Altair

Usage:
  ./taskmanager.sh batch --job-file modelmembrane.yaml [--dry-run]
  ./taskmanager.sh generate-chunks --chunks 50 --length-ns 10 --path modelmembrane
  ./taskmanager.sh show-config
  ./taskmanager.sh validate-workflow --job-file modelmembrane.yaml

Examples:
  # Submit membrane protein workflow
  ./taskmanager.sh batch --job-file modelmembrane.yaml
  
  # Generate 50 production chunks of 10ns each  
  ./taskmanager.sh generate-chunks --chunks 50 --length-ns 10 --path modelmembrane
  
  # Check SLURM configuration (supports GPU resources)
  ./taskmanager.sh show-config

Compatible with Eagle/Altair cluster using:
- GROMACS 2023.3_mpi module
- GPU resources (GRES parameter)
- MPI execution via srun

EOF
}

main() {
    check_environment
    
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 0
    fi
    
    # Pass all arguments directly to Python module
    python3 -m "$PYTHON_MODULE" "$@"
}

main "$@" 