"""
Production simulation chunker for long trajectories
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any


class ProductionChunker:
    """Handles chunked production simulation generation"""
    
    def __init__(self, chunk_length_ns: int = 10, total_chunks: int = 10):
        self.chunk_length_ns = chunk_length_ns
        self.total_chunks = total_chunks
        self.total_length_ns = total_chunks * chunk_length_ns
        self.chunk_size = chunk_length_ns
        self.steps_per_ns = 500000  # For dt=0.002 ps
    
    def generate_chunk_scripts(self, base_path: str, mdp_template: str = "step7_production.mdp") -> List[str]:
        """Generate production chunk scripts based on existing MDP template"""
        base_path = Path(base_path)
        mdp_path = base_path / mdp_template
        
        if not mdp_path.exists():
            raise FileNotFoundError(f"MDP template not found: {mdp_path}")
        
        # Analyze original MDP to get parameters
        original_params = self._analyze_production_mdp(mdp_path)
        scripts = []
        
        for chunk in range(1, self.total_chunks + 1):
            script_name = f"prod_chunk{chunk}.sh"
            script_path = base_path / script_name
            
            script_content = self._generate_chunk_script(chunk, mdp_template, original_params, base_path)
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            os.chmod(script_path, 0o755)
            scripts.append(script_name)
        
        return scripts
    
    def _analyze_production_mdp(self, mdp_path: Path) -> Dict[str, str]:
        """Analyze production MDP file to extract key parameters"""
        params = {}
        
        with open(mdp_path, 'r') as f:
            content = f.read()
        
        # Extract key parameters
        dt_match = re.search(r'dt\s*=\s*([\d.]+)', content)
        params['dt'] = dt_match.group(1) if dt_match else "0.002"
        
        # Calculate steps per ns based on dt
        dt_value = float(params['dt'])
        self.steps_per_ns = int(1000 / dt_value)  # 1000 ps / dt
        
        return params
    
    def _generate_chunk_script(self, chunk_num: int, mdp_template: str, original_params: Dict[str, str], base_path: Path) -> str:
        """Generate individual chunk script"""
        nsteps = self.chunk_length_ns * self.steps_per_ns
        is_first_chunk = chunk_num == 1
        
        # Determine input structure based on chunk number
        if is_first_chunk:
            prev_structure = self._find_last_equilibration_file(base_path)
            prev_checkpoint = ""
        else:
            prev_structure = f"modelbound_{chunk_num-1}"
            prev_checkpoint = f"modelbound_{chunk_num-1}.cpt"
        
        script_parts = [
            "#!/bin/bash",
            f"# Production Chunk {chunk_num}: {self.chunk_length_ns} ns",
            f"# Generated from template: {mdp_template}",
            "",
            "set -euo pipefail",
            "",
            "# Load required modules",
            "module purge", 
            "module load gromacs/2023.3_mpi",
            "",
            "# Configuration",
            "export OMP_NUM_THREADS=2",
            f"CHUNK_NUM={chunk_num}",
            f"OUTPUT_PREFIX=\"modelbound_${{CHUNK_NUM}}\"",
            f"MDP_TEMPLATE=\"{mdp_template}\"",
            f"CHUNK_MDP=\"chunk${{CHUNK_NUM}}_production.mdp\"",
            "",
            f"echo \"=== Production Chunk $CHUNK_NUM ({self.chunk_length_ns} ns) ===\"",
            "",
            "# Generate chunk-specific MDP",
            f"cp \"$MDP_TEMPLATE\" \"$CHUNK_MDP\"",
            f"sed -i 's/nsteps.*/nsteps = {nsteps}/' \"$CHUNK_MDP\"",
            "",
        ]
        
        if is_first_chunk:
            script_parts.extend([
                "# First chunk - start from equilibration",
                f"echo \"Starting from equilibration: {prev_structure}\"",
                "gmx_mpi grompp -f \"$CHUNK_MDP\" \\",
                f"    -c \"{prev_structure}.gro\" \\",
                "    -p topol.top \\",
                "    -n index.ndx \\",
                "    -o \"${OUTPUT_PREFIX}.tpr\" \\",
                "    -maxwarn 1",
            ])
        else:
            script_parts.extend([
                f"# Continuation chunk - extend from chunk {chunk_num-1}",
                f"echo \"Continuing from chunk {chunk_num-1}\"",
                "gmx_mpi grompp -f \"$CHUNK_MDP\" \\",
                f"    -c \"{prev_structure}.gro\" \\",
                f"    -t \"{prev_checkpoint}\" \\",
                "    -p topol.top \\",
                "    -n index.ndx \\",
                "    -o \"${OUTPUT_PREFIX}.tpr\"",
            ])
        
        script_parts.extend([
            "",
            "# Run production simulation",
            "echo \"Running production chunk $CHUNK_NUM...\"",
            "srun gmx_mpi mdrun -v -deffnm \"$OUTPUT_PREFIX\" -dlb auto -nstlist 10 -ntomp 2",
            "",
            "# Validate output",
            "if [[ ! -f \"${OUTPUT_PREFIX}.gro\" ]]; then",
            "    echo \"ERROR: Production chunk $CHUNK_NUM failed\"",
            "    exit 1",
            "fi",
            "",
            "# Clean up chunk MDP",
            "rm -f \"$CHUNK_MDP\"",
            "",
            f"echo \"Chunk {chunk_num} completed: ${{OUTPUT_PREFIX}}.xtc, ${{OUTPUT_PREFIX}}.gro\"",
            ""
        ])
        
        return "\n".join(script_parts)
    
    def _find_last_equilibration_file(self, base_path: Path) -> str:
        """Find the last equilibration output file"""
        # Look for step6.6_equilibration first, then step6.X_equilibration
        for step in ["6.6", "6.5", "6.4", "6.3", "6.2", "6.1"]:
            filename = f"step{step}_equilibration"
            if (base_path / f"{filename}.gro").exists():
                return filename
        
        return "step6.6_equilibration"  # Default fallback
    
    def show_chunk_summary(self):
        """Display chunk configuration summary"""
        print(f"\n=== Production Chunk Configuration ===")
        print(f"Total chunks: {self.total_chunks}")
        print(f"Chunk length: {self.chunk_length_ns} ns")
        print(f"Total simulation time: {self.total_length_ns} ns")
        print(f"Steps per chunk: {self.chunk_length_ns * self.steps_per_ns}")
        print(f"Steps per ns: {self.steps_per_ns}")
        print("=" * 39)

    def get_chunk_names(self, prefix: str) -> list:
        """Get list of chunk names"""
        return [f"{prefix}{i+1}" for i in range(self.total_chunks)]
        
    def generate_scripts(self, output_dir: str, prefix: str = "prod_chunk", mdp_template: str = None) -> list:
        """Generate chunk scripts"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        scripts = []
        for i in range(self.total_chunks):
            script_name = f"{prefix}{i+1}.sh"
            script_path = output_dir / script_name
            
            with open(script_path, 'w') as f:
                f.write(self._generate_chunk_script(i+1, mdp_template))
            
            script_path.chmod(0o755)  # Make executable
            scripts.append(str(script_path))
            
        return scripts
        
    def _generate_chunk_script(self, chunk_num: int, mdp_template: str = None) -> str:
        """Generate individual chunk script content"""
        script = [
            "#!/bin/bash",
            "",
            f"# Production chunk {chunk_num}/{self.total_chunks}",
            f"# Duration: {self.chunk_length_ns} ns",
            "",
            "# Load configuration",
            'MDP_FILE="${MDP_FILE:-' + (mdp_template or 'step7_production.mdp') + '}"',
            'TPR_FILE="${TPR_FILE:-topol.tpr}"',
            f'OUTPUT_PREFIX="${{OUTPUT_PREFIX:-prod_chunk{chunk_num}}}"',
            "",
            "# Run production",
            "gmx_mpi mdrun -deffnm $OUTPUT_PREFIX -maxh 71"
        ]
        return "\n".join(script)