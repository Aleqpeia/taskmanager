"""
Enhanced batch job management for simple .slurmparams format
"""

from typing import List, Dict, Any
from .config import SlurmConfig


class BatchManager:
    """Batch job manager for simple SLURM parameter format"""
    
    def __init__(self, config: SlurmConfig):
        self.config = config
    
    def generate_script(self, jobs: List[Dict[str, Any]], execution_mode: str = "sequential") -> str:
        """Generate batch script with job-specific resources"""
        script_parts = []
        
        script_parts.extend([
            "#!/bin/bash",
            "",
            # "# SLURM directives for workflow manager job",
            # "#SBATCH --job-name=modelmembrane",
            # "#SBATCH --output=logs/modelmembrane.log",
            # "#SBATCH --error=logs/modelmembrane.err",
            # "#SBATCH --time=1-00:00:00",
            # "#SBATCH --nodes=4",
            # "#SBATCH --ntasks-per-node=6",
            # "#SBATCH --ntasks-per-core=1",
            # "#SBATCH --cpus-per-task=4",
            "",
            "# Generated SLURM batch script",
            f"# Configuration: {self.config.config_file}",
            f"# Execution mode: {execution_mode}",
            "",
            "set -euo pipefail",
            "",
            "# Ensure output directory exists",
            "mkdir -p logs",
            "",
            "# Function to submit job with specific resources", 
            "submit_job_step() {",
            "    local job_name=\"$1\"",
            "    local script_path=\"$2\"", 
            "    local dependency=\"$3\"",
            "",
            "    echo \"Submitting $job_name from $script_path\"",
            "",
            "    # Check if script exists",
            "    if [[ ! -f \"$script_path\" ]]; then",
            "        echo \"  ERROR: Script not found: $script_path\"",
            "        return 1",
            "    fi",
            "",
            "    # Build SBATCH command",
            "    local sbatch_cmd=\"sbatch\"",
            "",
            "    # Add dependency if specified", 
            "    if [[ -n \"$dependency\" ]]; then",
            "        sbatch_cmd=\"$sbatch_cmd --dependency=afterok:$dependency\"",
            "    fi",
            "",
            "    # Submit the script (already has SLURM headers)",
            "    local job_output",
            "    job_output=$($sbatch_cmd \"$script_path\" 2>&1)",
            "    local exit_code=$?",
            "",
            "    if [[ $exit_code -eq 0 ]]; then",
            "        local job_id=$(echo \"$job_output\" | grep -o '[0-9]\\+' | head -1)",
            "        echo \"  Submitted: Job ID $job_id\"",
            "        echo \"$job_id\"",
            "    else",
            "        echo \"  ERROR: Job submission failed\"",
            "        echo \"  Output: $job_output\"",
            "        return 1",
            "    fi",
            "}",
            "",
            "# Main execution",
            "echo \"Starting modelbound workflow\"",
            f"echo \"Configuration: {self.config.config_file}\"",
            "echo \"Output logs: logs/\"",
            "",
            "# Job execution chain",
            "prev_job_id=\"\"",
            ""
        ])
        
        # Generate job submissions
        for job in jobs:
            job_name = job['name'] 
            job_type = job.get('job_type', 'default')
            nodes = job.get('nodes', None)  # Use None to get default from config
            scripts = job.get('scripts', [])
            
            # If job has chunk configuration, handle chunks
            if job.get('is_chunked', False):
                chunk_meta = job['chunk_metadata']
                total_chunks = chunk_meta['total_chunks']
                chunk_length_ns = chunk_meta['chunk_length_ns']
                total_time = total_chunks * chunk_length_ns
                
                script_parts.extend([
                    f"echo \"=== Starting {job_name} stage ===\"",
                    f"echo \"Chunked simulation: {total_chunks} chunks × {chunk_length_ns} ns = {total_time} ns total\"",
                    ""
                ])
            else:
                script_parts.append(f"echo \"=== Starting {job_name} stage ===\"")
            
            for i, script in enumerate(scripts):
                script_path = f"{job['path']}/{script}"
                step_name = f"{job_name}_{script.replace('.sh', '')}"
                
                if execution_mode == "sequential":
                    script_parts.extend([
                        f"echo \"Step {i+1}/{len(scripts)}: {script}\"",
                        f"job_id=$(submit_job_step \"{step_name}\" \"{job_type}\"  \"{script_path}\" \"$prev_job_id\")",
                        "prev_job_id=\"$job_id\"",
                        "echo",
                    ])
                else:  # parallel
                    script_parts.extend([
                        f"echo \"Step {i+1}/{len(scripts)}: {script} (parallel)\"",
                        f"submit_job_step \"{step_name}\" \"{job_type}\" \"{nodes}\" \"{script_path}\" \"\"",
                        "echo",
                    ])
            
            script_parts.append("")
        
        script_parts.extend([
            "echo \"All jobs submitted successfully!\"",
            "echo \"Monitor with: squeue -u $USER\"",
            "echo \"Check logs in: logs/\"",
            ""
        ])
        
        return "\n".join(script_parts)