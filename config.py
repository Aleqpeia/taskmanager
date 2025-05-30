"""
SLURM configuration parser for simple key=value format with optional job-specific sections
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, List


class SlurmConfig:
    """SLURM configuration with simple key=value format support"""
    
    def __init__(self, config_file: str = '.slurmparams'):
        self.config_file = config_file
        self.global_params = {}
        self.job_configs = {}
        self.load_config()
    
    def load_config(self):
        """Load SLURM configuration from simple key=value format"""
        config_path = Path(self.config_file)
        
        if not config_path.exists():
            self.create_default_config()
            return
        
        current_section = 'global'
        
        with open(config_path, 'r') as f:
            content = f.read().strip()
        
        # Check if file has section headers
        has_sections = re.search(r'^\[([A-Z_]+)\]', content, re.MULTILINE)
        
        if not has_sections:
            # Simple key=value format - treat everything as global
            self._parse_simple_format(content)
        else:
            # INI-style format with sections
            self._parse_sectioned_format(content)
    
    def _parse_simple_format(self, content: str):
        """Parse simple key=value format without sections"""
        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse key=value pairs
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                self.global_params[key] = value
            else:
                print(f"Warning: Invalid line {line_num} in {self.config_file}: {line}")
    
    def _parse_sectioned_format(self, content: str):
        """Parse INI-style format with sections"""
        current_section = 'global'
        
        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Check for section headers [SECTION_NAME]
            section_match = re.match(r'^\[([A-Z_]+)\]$', line)
            if section_match:
                current_section = section_match.group(1).lower()
                if current_section not in self.job_configs:
                    self.job_configs[current_section] = {}
                continue
            
            # Parse key=value pairs
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                if current_section == 'global':
                    self.global_params[key] = value
                else:
                    self.job_configs[current_section][key] = value
            else:
                print(f"Warning: Invalid line {line_num} in {self.config_file}: {line}")
    
    def create_default_config(self):
        """Create default configuration file in your format"""
        config_content = """# Global SLURM parameters
PARTITION=altair
TIME=1-00:00:00
JOB_NAME=modelbound
OUTPUT_DIR=logs
OUTPUT_PATTERN=TASKMANAGER.%A_%a.%N.out
ERROR_PATTERN=TASKMANAGER.%A_%a.%N.err
MEM_PER_CPU=512MB

# Default job parameters
NODES=8
NTASKS_PER_NODE=6
NTASKS_PER_CORE=1
CPUS_PER_TASK=4

# Job-specific configurations (optional)
# Add sections like [MINIMIZATION], [EQUILIBRATION], [PRODUCTION] for job-specific settings
"""
        
        with open(self.config_file, 'w') as f:
            f.write(config_content)
        print(f"Created default configuration: {self.config_file}")
    
    def get_global_params(self) -> Dict[str, str]:
        """Get global SLURM parameters"""
        return self.global_params.copy()
    
    def get_job_params(self, job_type: str, nodes: Optional[int] = None) -> Dict[str, str]:
        """Get job-specific parameters with optional nodes override"""
        # Start with global defaults
        params = self.get_global_params().copy()
        
        # Override with job-specific parameters if they exist
        job_type_lower = job_type.lower()
        if job_type_lower in self.job_configs:
            job_params = self.job_configs[job_type_lower].copy()
            params.update(job_params)
        
        # Override NODES if specified (this is the only tunable parameter)
        if nodes is not None:
            params['NODES'] = str(nodes)
        
        return params
    
    def get_available_job_types(self) -> List[str]:
        """Get list of available job types"""
        return list(self.job_configs.keys())
    
    def format_sbatch_options(self, job_type: str = 'default', nodes: Optional[int] = None) -> List[str]:
        """Format parameters as SBATCH options"""
        params = self.get_job_params(job_type, nodes)
        sbatch_options = []
        
        # Map parameter names to SBATCH options
        param_mapping = {
            'PARTITION': 'partition',
            'TIME': 'time', 
            'JOB_NAME': 'job-name',
            'NODES': 'nodes',
            'NTASKS_PER_NODE': 'ntasks-per-node',
            'NTASKS_PER_CORE': 'ntasks-per-core',
            'CPUS_PER_TASK': 'cpus-per-task',
            'MEM_PER_CPU': 'mem-per-cpu',
            'GRES': 'gres'
        }
        
        for param_key, sbatch_key in param_mapping.items():
            if param_key in params:
                sbatch_options.append(f"--{sbatch_key}={params[param_key]}")
        
        # Handle output patterns
        if 'OUTPUT_DIR' in params and 'OUTPUT_PATTERN' in params:
            output_path = f"{params['OUTPUT_DIR']}/{params['OUTPUT_PATTERN']}"
            sbatch_options.append(f"--output={output_path}")
        
        if 'OUTPUT_DIR' in params and 'ERROR_PATTERN' in params:
            error_path = f"{params['OUTPUT_DIR']}/{params['ERROR_PATTERN']}"
            sbatch_options.append(f"--error={error_path}")
        
        return sbatch_options
    
    def show_summary(self):
        """Display configuration summary"""
        print(f"\n=== SLURM Configuration ({self.config_file}) ===")
        
        # Global parameters
        if self.global_params:
            print("\nGlobal Parameters:")
            for key, value in self.global_params.items():
                tunable = " (tunable)" if key == "NODES" else ""
                print(f"  {key:18}: {value}{tunable}")
        
        # Job-specific parameters
        if self.job_configs:
            print(f"\nJob-Specific Configurations:")
            for job_type, job_params in self.job_configs.items():
                print(f"\n  [{job_type.upper()}]:")
                for key, value in job_params.items():
                    tunable = " (tunable)" if key == "NODES" else ""
                    print(f"    {key:16}: {value}{tunable}")
        else:
            print("\nNo job-specific configurations found.")
            print("All jobs will use global parameters.")
        
        print("\nNote: Only 'NODES' parameter is tunable per job execution")
        print("=" * 47)
    
    def validate_job_type(self, job_type: str) -> bool:
        """Validate if job type is configured"""
        return job_type.lower() in self.job_configs or job_type == 'default'