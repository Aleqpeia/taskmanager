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
        
        # Determine last equilibration file
        last_equil_file = self._find_last_equilibration_file(base_path)
        
        script_parts = [
            "#!/bin/bash",
            f"# Production Chunk {chunk_num}: {self.chunk_length_ns} ns",
            f"# Generated from template: {mdp_template}",
            "",
            "set -euo pipefail",
            "",
            f"echo \"=== Production Chunk {chunk_num} ({self.chunk_length_ns} ns) ===\"",
            "",
            "# Chunk configuration",
            f"readonly CHUNK_NUM={chunk_num}",
            f"readonly CHUNK_LENGTH_NS={self.chunk_length_ns}",
            f"readonly NSTEPS={nsteps}",
            f"readonly MDP_TEMPLATE=\"{mdp_template}\"",
            "",
        ]
        
        if is_first_chunk:
            script_parts.extend([
                "# First chunk: start from final equilibration",
                f"INPUT_GRO=\"{last_equil_file}.gro\"",
                f"INPUT_CPT=\"{last_equil_file}.cpt\"",
                "OUTPUT_PREFIX=\"step7_chunk1\"",
                "",
                "if [[ ! -f \"$INPUT_GRO\" || ! -f \"$INPUT_CPT\" ]]; then",
                "    echo \"ERROR: Final equilibration files not found\"",
                "    echo \"Expected: $INPUT_GRO, $INPUT_CPT\"",
                "    exit 1",
                "fi",
            ])
        else:
            prev_chunk = chunk_num - 1
            script_parts.extend([
                f"# Chunk {chunk_num}: continue from previous chunk",
                f"INPUT_GRO=\"step7_chunk{prev_chunk}.gro\"", 
                f"INPUT_CPT=\"step7_chunk{prev_chunk}.cpt\"",
                f"OUTPUT_PREFIX=\"step7_chunk{chunk_num}\"",
                "",
                "if [[ ! -f \"$INPUT_GRO\" || ! -f \"$INPUT_CPT\" ]]; then",
                f"    echo \"ERROR: Previous chunk files not found (chunk {prev_chunk})\"",
                "    echo \"Expected: $INPUT_GRO, $INPUT_CPT\"",
                "    exit 1",
                "fi",
            ])
        
        script_parts.extend([
            "",
            "# Create chunk-specific MDP file",
            "echo \"Creating chunk-specific MDP file...\"",
            f"sed \"s/nsteps.*/nsteps = $NSTEPS/\" \"$MDP_TEMPLATE\" > \"chunk${{CHUNK_NUM}}_production.mdp\"",
            "",
            "# Verify MDP file creation",
            "if [[ ! -f \"chunk${CHUNK_NUM}_production.mdp\" ]]; then",
            "    echo \"ERROR: Failed to create chunk MDP file\"",
            "    exit 1",
            "fi",
            "",
            "# Generate TPR file",
            "echo \"Generating TPR file for chunk $CHUNK_NUM...\"",
            "gmx grompp -f \"chunk${CHUNK_NUM}_production.mdp\" \\",
            "           -c \"$INPUT_GRO\" \\",
            "           -t \"$INPUT_CPT\" \\",
            "           -p topol.top \\",
            "           -o \"${OUTPUT_PREFIX}.tpr\" \\",
            "           -maxwarn 1",
            "",
            "# Verify TPR file creation",
            "if [[ ! -f \"${OUTPUT_PREFIX}.tpr\" ]]; then",
            "    echo \"ERROR: Failed to create TPR file\"",
            "    exit 1",
            "fi",
            "",
            "# Run production simulation",
            "echo \"Starting production chunk $CHUNK_NUM...\"",
            "echo \"Simulation time: ${CHUNK_LENGTH_NS} ns\"",
            "echo \"Total steps: $NSTEPS\"",
            f"echo \"Timestep: {original_params['dt']} ps\"",
            "",
            "gmx mdrun -v -deffnm \"$OUTPUT_PREFIX\"",
            "",
            "# Verify output",
            "if [[ ! -f \"${OUTPUT_PREFIX}.xtc\" ]]; then",
            "    echo \"ERROR: Chunk $CHUNK_NUM failed - no trajectory output\"",
            "    exit 1",
            "fi",
            "",
            "# Quick statistics",
            "echo \"Chunk $CHUNK_NUM completed successfully\"",
            "",
            "# Trajectory information",
            "echo \"Trajectory information:\"",
            "gmx check -f \"${OUTPUT_PREFIX}.xtc\" 2>/dev/null | head -n 3",
            "",
            "# File sizes",
            "echo \"Output file sizes:\"",
            "ls -lh \"${OUTPUT_PREFIX}\".{xtc,edr,gro,log} 2>/dev/null || true",
            "",
            "# Clean up chunk MDP",
            "rm -f \"chunk${CHUNK_NUM}_production.mdp\"",
            "",
            f"echo \"Chunk {chunk_num} output: ${{OUTPUT_PREFIX}}.xtc, ${{OUTPUT_PREFIX}}.edr, ${{OUTPUT_PREFIX}}.gro\"",
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
        print(f"Total simulation time: {self.total_chunks * self.chunk_length_ns} ns")
        print(f"Steps per chunk: {self.chunk_length_ns * self.steps_per_ns}")
        print(f"Steps per ns: {self.steps_per_ns}")
        print("=" * 39)