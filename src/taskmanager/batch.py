"""
Enhanced batch job management for simple .slurmparams format
"""

from typing import List, Dict, Any
from .config import SlurmConfig


class BatchManager:
    """Batch job manager for simple SLURM parameter format"""
    
    def __init__(self, config: SlurmConfig):
        self.config = config
    
    def generate_script(self, jobs, execution_mode="sequential"):
        """Generate batch script with job-specific resources"""
        script_parts = []
        
        # Add SLURM headers for the batch script itself
        batch_params = self.config.get_global_params()
        
        script_parts.append("#!/bin/bash")
        script_parts.append("")
        script_parts.append("# SLURM job parameters")
        
        for key, value in batch_params.items():
            if key not in ['OUTPUT_DIR', 'OUTPUT_PATTERN', 'ERROR_PATTERN']:
                script_parts.append(f"#SBATCH --{key.lower()}={value}")
        
        # Add job steps
        script_parts.append("\n# Job steps")
        
        if execution_mode == "sequential":
            script_parts.append("prev_job_id=''")
            
            for job in jobs:
                job_type = job['job_type']
                job_path = job['path']
                
                for script in job['scripts']:
                    script_path = f"{job_path}/{script}"
                    script_parts.append(f"\n# Submit {script}")
                    script_parts.append(f"job_id=$(submit_job_step {script_path} $prev_job_id)")
                    script_parts.append("prev_job_id=$job_id")
                
        elif execution_mode == "parallel":
            for job in jobs:
                job_type = job['job_type']
                job_path = job['path']
                
                script_parts.append(f"\n# Submit {job['name']} (parallel)")
                for script in job['scripts']:
                    script_path = f"{job_path}/{script}"
                    script_parts.append(f"submit_job_step {script_path}")
        
        return "\n".join(script_parts)