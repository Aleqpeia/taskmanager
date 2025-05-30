"""
Equilibration script generator for existing MDP files - optimized for modelbound structure
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


class EquilibrationGenerator:
    """Generates shell scripts for existing MDP files in modelbound structure"""
    
    def __init__(self, mdp_directory: str = "modelbound"):
        self.mdp_directory = Path(mdp_directory)
        self.discovered_mdps = self.discover_mdp_files()
    
    def discover_mdp_files(self) -> Dict[str, List[str]]:
        """Discover and categorize existing MDP files for modelbound structure"""
        mdp_files = {
            "minimization": [],
            "equilibration": [], 
            "production": []
        }
        
        if not self.mdp_directory.exists():
            print(f"Warning: Directory {self.mdp_directory} not found")
            return mdp_files
        
        for mdp_file in self.mdp_directory.glob("*.mdp"):
            filename = mdp_file.name.lower()
            
            # Minimization: step6.0_steep.mdp, step6.0_cg.mdp
            if filename in ["step6.0_steep.mdp", "step6.0_cg.mdp"]:
                mdp_files["minimization"].append(mdp_file.name)
            # Equilibration: step6.1 through step6.6
            elif re.match(r"step6\.[1-6]_equilibration\.mdp", filename):
                mdp_files["equilibration"].append(mdp_file.name)
            # Production: step7_production.mdp
            elif filename == "step7_production.mdp":
                mdp_files["production"].append(mdp_file.name)
        
        # Sort files properly
        mdp_files["minimization"].sort(key=lambda x: self._extract_step_number(x))
        mdp_files["equilibration"].sort(key=lambda x: self._extract_step_number(x))
        
        return mdp_files
    
    def _extract_step_number(self, filename: str) -> float:
        """Extract step number from filename for sorting"""
        # Handle step6.0_steep.mdp -> 6.01, step6.0_cg.mdp -> 6.02  
        if "step6.0_steep" in filename:
            return 6.01
        elif "step6.0_cg" in filename:
            return 6.02
        
        # Handle step6.X_equilibration.mdp
        match = re.search(r"step(\d+)\.(\d+)", filename)
        if match:
            return float(f"{match.group(1)}.{match.group(2)}")
        
        return 0
    
    def generate_scripts(self, output_dir: str = None, overwrite: bool = False) -> Dict[str, List[str]]:
        """Generate shell scripts for discovered MDP files"""
        if output_dir is None:
            output_dir = self.mdp_directory
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        generated_scripts = {
            "minimization": [],
            "equilibration": [],
            "production": []
        }
        
        # Generate minimization scripts
        for mdp_file in self.discovered_mdps["minimization"]:
            if "steep" in mdp_file:
                script_name = "min_steep.sh"
            else:
                script_name = "min_cg.sh"
            
            if self._should_generate_script(output_path / script_name, overwrite):
                self._generate_minimization_script(mdp_file, script_name, output_path)
                generated_scripts["minimization"].append(script_name)
        
        # Generate equilibration scripts  
        for i, mdp_file in enumerate(self.discovered_mdps["equilibration"], 1):
            script_name = f"equil_stage{i}.sh"
            
            if self._should_generate_script(output_path / script_name, overwrite):
                self._generate_equilibration_script(mdp_file, i, script_name, output_path)
                generated_scripts["equilibration"].append(script_name)
        
        return generated_scripts
    
    def _should_generate_script(self, script_path: Path, overwrite: bool) -> bool:
        """Check if script should be generated"""
        if not script_path.exists():
            return True
        
        if overwrite:
            # Backup existing file
            backup_path = script_path.with_suffix('.sh.bak')
            script_path.rename(backup_path)
            print(f"Backed up existing script to {backup_path}")
            return True
        
        print(f"Skipping {script_path.name} (already exists)")
        return False
    
    def _generate_minimization_script(self, mdp_file: str, script_name: str, output_path: Path):
        """Generate minimization script for specific MDP file"""
        
        if "steep" in mdp_file:
            # Steepest descent script
            script_content = f"""#!/bin/bash
# Steepest descent minimization using {mdp_file}

set -euo pipefail

echo "=== Steepest Descent Minimization ==="

# Check prerequisites
required_files=("{mdp_file}" "step5_input.gro" "topol.top")
for file in "${{required_files[@]}}"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Required file missing: $file"
        exit 1
    fi
done

# Generate TPR file
echo "Generating TPR file for steepest descent..."
gmx grompp -f {mdp_file} -c step5_input.gro -p topol.top -o step6.0_steep.tpr -maxwarn 1

# Run minimization
echo "Running steepest descent minimization..."
gmx mdrun -v -deffnm step6.0_steep

# Check convergence
if gmx check -f step6.0_steep.log 2>/dev/null | grep -q "converged"; then
    echo "Steepest descent converged successfully"
else
    echo "Warning: Steepest descent may not have converged fully"
fi

# Quick energy check
echo "Final potential energy:"
if [[ -f "step6.0_steep.edr" ]]; then
    echo "0" | gmx energy -f step6.0_steep.edr -o potential_steep.xvg -xvg none << EOF > /dev/null
Potential
EOF
    if [[ -f "potential_steep.xvg" ]]; then
        tail -n 1 potential_steep.xvg | awk '{{printf "%.2f kJ/mol\\n", $2}}'
        rm -f potential_steep.xvg
    fi
fi

echo "Steepest descent minimization completed"
echo "Output: step6.0_steep.gro, step6.0_steep.edr, step6.0_steep.log"
"""
        else:
            # Conjugate gradient script  
            script_content = f"""#!/bin/bash
# Conjugate gradient minimization using {mdp_file}

set -euo pipefail

echo "=== Conjugate Gradient Minimization ==="

# Check prerequisites
if [[ ! -f "step6.0_steep.gro" ]]; then
    echo "ERROR: step6.0_steep.gro not found. Run steepest descent first."
    exit 1
fi

if [[ ! -f "{mdp_file}" ]]; then
    echo "ERROR: {mdp_file} not found"
    exit 1
fi

# Generate TPR file
echo "Generating TPR file for conjugate gradient..."
gmx grompp -f {mdp_file} -c step6.0_steep.gro -p topol.top -o step6.0_cg.tpr -maxwarn 1

# Run minimization
echo "Running conjugate gradient minimization..."
gmx mdrun -v -deffnm step6.0_cg

# Check final energy
echo "Final potential energy:"
if [[ -f "step6.0_cg.edr" ]]; then
    echo "0" | gmx energy -f step6.0_cg.edr -o potential_cg.xvg -xvg none << EOF > /dev/null
Potential
EOF
    if [[ -f "potential_cg.xvg" ]]; then
        tail -n 1 potential_cg.xvg | awk '{{printf "%.2f kJ/mol\\n", $2}}'
        rm -f potential_cg.xvg
    fi
fi

echo "Conjugate gradient minimization completed"
echo "Output: step6.0_cg.gro, step6.0_cg.edr, step6.0_cg.log"
echo "System ready for equilibration"
"""
        
        script_path = output_path / script_name
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        print(f"Generated {script_name}")
    
    def _generate_equilibration_script(self, mdp_file: str, stage_num: int, script_name: str, output_path: Path):
        """Generate equilibration script for specific stage"""
        
        # Determine input files based on stage
        if stage_num == 1:
            input_gro = "step6.0_cg.gro"
            input_cpt = ""
            continuation_flag = ""
        else:
            prev_stage = stage_num - 1
            input_gro = f"step6.{prev_stage}_equilibration.gro"
            input_cpt = f"-t step6.{prev_stage}_equilibration.cpt"
            continuation_flag = ""
        
        # Get stage description
        stage_info = self._analyze_mdp_stage(mdp_file)
        output_prefix = mdp_file.replace('.mdp', '')
        
        script_content = f"""#!/bin/bash
# Equilibration Stage {stage_num}: {stage_info['description']}
# Using {mdp_file} ({stage_info['duration']}, {stage_info['ensemble']})

set -euo pipefail

echo "=== Equilibration Stage {stage_num}: {stage_info['description']} ==="

# Check prerequisites
required_files=("{mdp_file}" "{input_gro}" "topol.top")
for file in "${{required_files[@]}}"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Required file missing: $file"
        exit 1
    fi
done

# Generate TPR file
echo "Generating TPR file for stage {stage_num} equilibration..."
gmx grompp -f {mdp_file} \\
           -c {input_gro} \\
           -r {input_gro} \\
           {input_cpt} \\
           -p topol.top \\
           -o {output_prefix}.tpr \\
           -maxwarn 1

# Verify TPR creation
if [[ ! -f "{output_prefix}.tpr" ]]; then
    echo "ERROR: Failed to create TPR file"
    exit 1
fi

# Run equilibration
echo "Running stage {stage_num} equilibration ({stage_info['duration']}, {stage_info['ensemble']})..."
gmx mdrun -v -deffnm {output_prefix}

# Verify output
if [[ ! -f "{output_prefix}.gro" ]]; then
    echo "ERROR: Stage {stage_num} equilibration failed - no output structure"
    exit 1
fi

# Quick analysis
echo "Stage {stage_num} analysis:"
if [[ -f "{output_prefix}.edr" ]]; then
    # Temperature
    echo "0" | gmx energy -f {output_prefix}.edr -o temp_stage{stage_num}.xvg -xvg none << EOF > /dev/null 2>&1
Temperature
EOF
    if [[ -f "temp_stage{stage_num}.xvg" ]]; then
        avg_temp=$(awk '{{sum+=$2; count++}} END {{if(count>0) printf "%.1f", sum/count}}' temp_stage{stage_num}.xvg)
        echo "  Average temperature: $avg_temp K"
        rm -f temp_stage{stage_num}.xvg
    fi
    
    # Pressure (if NPT)
    if [[ "{stage_info['ensemble']}" == "NPT" ]]; then
        echo "0" | gmx energy -f {output_prefix}.edr -o press_stage{stage_num}.xvg -xvg none << EOF > /dev/null 2>&1
Pressure
EOF
        if [[ -f "press_stage{stage_num}.xvg" ]]; then
            avg_press=$(awk '{{sum+=$2; count++}} END {{if(count>0) printf "%.1f", sum/count}}' press_stage{stage_num}.xvg)
            echo "  Average pressure: $avg_press bar"
            rm -f press_stage{stage_num}.xvg
        fi
    fi
fi

echo "Stage {stage_num} equilibration completed successfully"
echo "Output: {output_prefix}.gro, {output_prefix}.cpt, {output_prefix}.edr"
"""
        
        script_path = output_path / script_name
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        print(f"Generated {script_name}")
    
    def _analyze_mdp_stage(self, mdp_file: str) -> Dict[str, str]:
        """Analyze MDP file to extract stage information"""
        try:
            with open(self.mdp_directory / mdp_file, 'r') as f:
                content = f.read()
            
            # Extract key parameters
            duration = "unknown"
            ensemble = "unknown"
            
            # Get nsteps and dt
            nsteps_match = re.search(r'nsteps\s*=\s*(\d+)', content)
            dt_match = re.search(r'dt\s*=\s*([\d.]+)', content)
            
            if nsteps_match and dt_match:
                nsteps = int(nsteps_match.group(1))
                dt = float(dt_match.group(1))
                total_ps = nsteps * dt
                duration = f"{total_ps:.0f} ps"
            
            # Determine ensemble
            if re.search(r'pcoupl.*=.*\w+', content) and not re.search(r'pcoupl.*=.*no', content, re.IGNORECASE):
                ensemble = "NPT"
            else:
                ensemble = "NVT"
            
            # Stage-specific descriptions based on your files
            descriptions = {
                "step6.1_equilibration.mdp": "Strong restraints, NVT",
                "step6.2_equilibration.mdp": "Reduced restraints, NVT", 
                "step6.3_equilibration.mdp": "NPT introduction",
                "step6.4_equilibration.mdp": "dt=2fs, moderate restraints",
                "step6.5_equilibration.mdp": "Light restraints",
                "step6.6_equilibration.mdp": "Minimal restraints"
            }
            
            description = descriptions.get(mdp_file, f"{ensemble} equilibration")
            
            return {
                "duration": duration,
                "ensemble": ensemble,
                "description": description
            }
        
        except Exception:
            return {
                "duration": "unknown",
                "ensemble": "unknown", 
                "description": "equilibration stage"
            }
    
    def show_discovered_files(self):
        """Show summary of discovered MDP files in modelbound structure"""
        print(f"\n=== MDP Files in {self.mdp_directory} ===")
        
        total_files = sum(len(files) for files in self.discovered_mdps.values())
        
        if total_files == 0:
            print("No MDP files found!")
            return
        
        # Minimization
        if self.discovered_mdps["minimization"]:
            print(f"\nMinimization ({len(self.discovered_mdps['minimization'])} files):")
            for i, mdp_file in enumerate(self.discovered_mdps["minimization"], 1):
                print(f"  {i}. {mdp_file}")
        
        # Equilibration
        if self.discovered_mdps["equilibration"]:
            print(f"\nEquilibration ({len(self.discovered_mdps['equilibration'])} files):")
            for i, mdp_file in enumerate(self.discovered_mdps["equilibration"], 1):
                stage_info = self._analyze_mdp_stage(mdp_file)
                print(f"  {i}. {mdp_file}")
                print(f"     → {stage_info['description']} ({stage_info['duration']}, {stage_info['ensemble']})")
        
        # Production
        if self.discovered_mdps["production"]:
            print(f"\nProduction ({len(self.discovered_mdps['production'])} files):")
            for i, mdp_file in enumerate(self.discovered_mdps["production"], 1):
                print(f"  {i}. {mdp_file}")
        
        print(f"\nTotal: {total_files} MDP files discovered")
        print("=" * 35)