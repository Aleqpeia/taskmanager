"""
Script generator with configurable templates and parameters
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from taskmanager.config import SlurmConfig

class ScriptGenerator:
    """Generate configurable GROMACS scripts from templates"""
    
    def __init__(self, config: SlurmConfig, template_dir: str = None):
        self.config = config  # Add config reference
        if template_dir is None:
            # Default to taskmanager/templates directory
            self.template_dir = Path(__file__).parent / "templates"
        else:
            self.template_dir = Path(template_dir)
        
        self.template_dir.mkdir(exist_ok=True)
        self._ensure_default_templates()
    
    def _ensure_default_templates(self):
        """Create default templates if they don't exist"""
        templates = {
            "minimization_steep.sh.template": self._get_steep_template(),
            "minimization_cg.sh.template": self._get_cg_template(),
            "equilibration.sh.template": self._get_equilibration_template(),
            "production.sh.template": self._get_production_template()
        }
        
        for template_name, content in templates.items():
            template_path = self.template_dir / template_name
            if not template_path.exists():
                with open(template_path, 'w') as f:
                    f.write(content)
    
    def _get_steep_template(self) -> str:
        """Template for steepest descent minimization"""
        return '''#!/bin/bash
# Steepest descent minimization - Production template for Eagle/Altair

set -euo pipefail

# Load required modules
module purge
module load gromacs/2023.3_mpi

# Configuration variables
export OMP_NUM_THREADS=2
INPUT_STRUCTURE="${INPUT_STRUCTURE:-step5_input.gro}"
MDP_FILE="${MDP_FILE:-step6.0_steep.mdp}"
TOPOLOGY_FILE="${TOPOLOGY_FILE:-topol.top}"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-steep}"
MAX_WARNINGS="${MAX_WARNINGS:-1}"
VERBOSE_OUTPUT="${VERBOSE_OUTPUT:-true}"

echo "=== Steepest Descent Minimization ==="
echo "Input structure: $INPUT_STRUCTURE"
echo "MDP file: $MDP_FILE"
echo "Output prefix: $OUTPUT_PREFIX"

# Check prerequisites
if [[ ! -f "$INPUT_STRUCTURE" ]]; then
    echo "ERROR: Input structure not found: $INPUT_STRUCTURE"
    exit 1
fi

if [[ ! -f "$MDP_FILE" ]]; then
    echo "ERROR: MDP file not found: $MDP_FILE"
    exit 1
fi

if [[ ! -f "$TOPOLOGY_FILE" ]]; then
    echo "ERROR: Topology file not found: $TOPOLOGY_FILE"
    exit 1
fi

# Generate TPR file
echo "Generating TPR file..."
gmx_mpi grompp -f "$MDP_FILE" -c "$INPUT_STRUCTURE" -p "$TOPOLOGY_FILE" \\
           -o "${OUTPUT_PREFIX}.tpr" -maxwarn "$MAX_WARNINGS" -r step5_input.pdb

# Run minimization with srun for proper MPI execution
echo "Running steepest descent minimization..."
if [[ "$VERBOSE_OUTPUT" == "true" ]]; then
    srun gmx_mpi mdrun -v -deffnm "$OUTPUT_PREFIX" -ntomp 2
else
    srun gmx_mpi mdrun -deffnm "$OUTPUT_PREFIX" -ntomp 2
fi

# Validate output
if [[ ! -f "${OUTPUT_PREFIX}.gro" ]]; then
    echo "ERROR: Minimization failed - output file not found"
    exit 1
fi

echo "Steepest descent minimization completed"
echo "Output: ${OUTPUT_PREFIX}.gro, ${OUTPUT_PREFIX}.edr, ${OUTPUT_PREFIX}.log"
'''
    
    def _get_cg_template(self) -> str:
        """Template for conjugate gradient minimization"""
        return '''#!/bin/bash
# Conjugate gradient minimization - Template version

set -euo pipefail

# Configuration variables
INPUT_STRUCTURE="${INPUT_STRUCTURE:-step6.0_steep.gro}"
MDP_FILE="${MDP_FILE:-step6.0_cg.mdp}"
TOPOLOGY_FILE="${TOPOLOGY_FILE:-topol.top}"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-step6.0_cg}"
MAX_WARNINGS="${MAX_WARNINGS:-1}"
VERBOSE_OUTPUT="${VERBOSE_OUTPUT:-true}"

echo "=== Conjugate Gradient Minimization ==="
echo "Input structure: $INPUT_STRUCTURE"
echo "MDP file: $MDP_FILE"
echo "Output prefix: $OUTPUT_PREFIX"

# Check prerequisites
if [[ ! -f "$INPUT_STRUCTURE" ]]; then
    echo "ERROR: Input structure not found: $INPUT_STRUCTURE"
    exit 1
fi

if [[ ! -f "$MDP_FILE" ]]; then
    echo "ERROR: MDP file not found: $MDP_FILE"
    exit 1
fi

if [[ ! -f "$TOPOLOGY_FILE" ]]; then
    echo "ERROR: Topology file not found: $TOPOLOGY_FILE"
    exit 1
fi

# Generate TPR file
echo "Generating TPR file..."
gmx grompp -f "$MDP_FILE" -c "$INPUT_STRUCTURE" -p "$TOPOLOGY_FILE" \\
           -o "${OUTPUT_PREFIX}.tpr" -maxwarn "$MAX_WARNINGS"

# Run minimization
echo "Running conjugate gradient minimization..."
if [[ "$VERBOSE_OUTPUT" == "true" ]]; then
    gmx_mpi  mdrun -v -deffnm "$OUTPUT_PREFIX"
else
    gmx_mpi mdrun -deffnm "$OUTPUT_PREFIX"
fi

echo "Conjugate gradient minimization completed"
echo "Output: ${OUTPUT_PREFIX}.gro, ${OUTPUT_PREFIX}.edr"
'''
    
    def _get_equilibration_template(self) -> str:
        """Template for equilibration"""
        return '''#!/bin/bash
# Equilibration template

set -euo pipefail

# Configuration variables
INPUT_STRUCTURE="${INPUT_STRUCTURE:-step6.0_cg.gro}"
INPUT_CHECKPOINT="${INPUT_CHECKPOINT:-}"
MDP_FILE="${MDP_FILE:-step6.1_equilibration.mdp}"
TOPOLOGY_FILE="${TOPOLOGY_FILE:-topol.top}"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-step6.1_equilibration}"
MAX_WARNINGS="${MAX_WARNINGS:-1}"
STAGE_NAME="${STAGE_NAME:-Equilibration}"

echo "=== $STAGE_NAME ==="
echo "Input structure: $INPUT_STRUCTURE"
echo "MDP file: $MDP_FILE"
echo "Output prefix: $OUTPUT_PREFIX"

# Check prerequisites
if [[ ! -f "$INPUT_STRUCTURE" ]]; then
    echo "ERROR: Input structure not found: $INPUT_STRUCTURE"
    exit 1
fi

# Generate TPR file
echo "Generating TPR file..."
grompp_cmd="gmx grompp -f $MDP_FILE -c $INPUT_STRUCTURE -p $TOPOLOGY_FILE -o ${OUTPUT_PREFIX}.tpr -maxwarn $MAX_WARNINGS"

if [[ -n "$INPUT_CHECKPOINT" && -f "$INPUT_CHECKPOINT" ]]; then
    grompp_cmd="$grompp_cmd -t $INPUT_CHECKPOINT"
    echo "Using checkpoint: $INPUT_CHECKPOINT"
fi

eval "$grompp_cmd"

# Run equilibration
echo "Running equilibration..."
gmx_mpi mdrun -v -deffnm "$OUTPUT_PREFIX"

echo "$STAGE_NAME completed"
echo "Output: ${OUTPUT_PREFIX}.gro, ${OUTPUT_PREFIX}.cpt, ${OUTPUT_PREFIX}.edr"
'''
    
    def _get_production_template(self) -> str:
        """Template for production runs"""
        return '''#!/bin/bash
# Production simulation template

set -euo pipefail

# Configuration variables
INPUT_STRUCTURE="${INPUT_STRUCTURE:-step6.6_equilibration.gro}"
INPUT_CHECKPOINT="${INPUT_CHECKPOINT:-step6.6_equilibration.cpt}"
MDP_FILE="${MDP_FILE:-step7_production.mdp}"
TOPOLOGY_FILE="${TOPOLOGY_FILE:-topol.top}"
OUTPUT_PREFIX="${OUTPUT_PREFIX:-step7_production}"
MAX_WARNINGS="${MAX_WARNINGS:-1}"

echo "=== Production Simulation ==="
echo "Input structure: $INPUT_STRUCTURE"
echo "Input checkpoint: $INPUT_CHECKPOINT"
echo "MDP file: $MDP_FILE"
echo "Output prefix: $OUTPUT_PREFIX"

# Check prerequisites
for file in "$INPUT_STRUCTURE" "$INPUT_CHECKPOINT" "$MDP_FILE" "$TOPOLOGY_FILE"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Required file not found: $file"
        exit 1
    fi
done

# Generate TPR file
echo "Generating TPR file..."
gmx_mpi grompp -f "$MDP_FILE" -c "$INPUT_STRUCTURE" -t "$INPUT_CHECKPOINT" \\
           -p "$TOPOLOGY_FILE" -o "${OUTPUT_PREFIX}.tpr" -maxwarn "$MAX_WARNINGS"

# Run production
echo "Starting production simulation..."
gmx_mpi mdrun -v -deffnm "$OUTPUT_PREFIX"

echo "Production simulation completed"
echo "Output: ${OUTPUT_PREFIX}.xtc, ${OUTPUT_PREFIX}.edr, ${OUTPUT_PREFIX}.gro"
'''
    
    def generate_script(self, script_type: str, output_path: str, custom_config: Dict[str, Any] = None) -> str:
        """Generate script from template with SLURM headers"""
        template_path = self.template_dir / f"{script_type}.sh.template"
        
        if not template_path.exists():
            available = self.list_available_templates()
            raise FileNotFoundError(
                f"Template not found: {script_type}\n"
                f"Available templates: {', '.join(available)}"
            )
        
        # Load template
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Apply configuration
        config = custom_config or {}
        script_content = self._apply_template_config(template_content, config)
        
        # Add SLURM headers if not present
        if not script_content.startswith('#SBATCH'):
            script_content = self._add_slurm_headers(script_content, script_type)
        
        # Write script
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write(script_content)
        
        # Make executable
        os.chmod(output_file, 0o755)
        
        return str(output_file)
    
    def _add_slurm_headers(self, content: str, script_type: str) -> str:
        """Add SLURM headers to script content"""
        lines = content.split('\n')
        
        # Find where to insert headers (after shebang)
        insert_idx = 1 if lines[0].startswith('#!') else 0
        
        # Get properly formatted SLURM headers
        sbatch_headers = self.config.format_sbatch_headers(script_type)
        
        # Split headers into lines and skip the shebang (we already have one)
        header_lines = sbatch_headers.split('\n')[1:]  # Skip #!/bin/bash
        
        # Insert headers
        lines[insert_idx:insert_idx] = header_lines
        
        return '\n'.join(lines)
    
    def _apply_template_config(self, content: str, config: Dict[str, Any]) -> str:
        """Apply configuration to template content"""
        for key, value in config.items():
            # Replace template variables
            content = content.replace(f"${{{key}}}", str(value))
            content = content.replace(f"${key}", str(value))
        
        return content
    
    def list_available_templates(self) -> List[str]:
        """List available script templates"""
        templates = []
        for template_file in self.template_dir.glob("*.template"):
            template_name = template_file.stem.replace('.sh', '')
            templates.append(template_name)
        return sorted(templates)

    def _format_sbatch_headers(self, job_type: str, nodes: int = None) -> str:
        """Format SBATCH headers for the script"""
        headers = []
        headers.append("#!/bin/bash\n")
        headers.append("# SLURM job parameters")
        
        params = self.config.get_job_params(job_type, nodes)
        for key, value in params.items():
            if key == 'OUTPUT_DIR':
                continue
            if key == 'OUTPUT_PATTERN':
                headers.append(f"#SBATCH --output={params.get('OUTPUT_DIR', 'logs')}/{value}")
            elif key == 'ERROR_PATTERN':
                headers.append(f"#SBATCH --error={params.get('OUTPUT_DIR', 'logs')}/{value}")
            else:
                headers.append(f"#SBATCH --{key.lower()}={value}")
        
        return "\n".join(headers)