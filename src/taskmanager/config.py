import re
from pathlib import Path
from .utils import ConfigurationError

class SlurmConfig:
    DEFAULT_CONFIG = {
        'PARTITION': 'altair',
        'TIME': '1-00:00:00',
        'JOB_NAME': 'modelbound',
        'OUTPUT_DIR': 'logs',
        'OUTPUT_PATTERN': 'TASKMANAGER.%A_%a.%N.out',
        'ERROR_PATTERN': 'TASKMANAGER.%A_%a.%N.err'
    }

    def __init__(self, config_file):
        """Initialize SLURM configuration"""
        self.config_file = Path(config_file)
        self.global_params = {}
        self.job_configs = {}
        
        if not self.config_file.exists():
            print(f"Created default configuration: {self.config_file}")
            self._create_default_config()
        
        self._load_config()

    def _create_default_config(self):
        """Create default configuration file"""
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            for key, value in self.DEFAULT_CONFIG.items():
                f.write(f"{key}={value}\n")
        self.global_params = self.DEFAULT_CONFIG.copy()

    def _load_config(self):
        """Load configuration from file"""
        current_section = None
        
        with open(self.config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                    
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1].lower()
                    self.job_configs[current_section] = {}
                    continue
                    
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if current_section:
                        self.job_configs[current_section][key] = value
                    else:
                        self.global_params[key] = value

    def _validate_time_format(self, time_str):
        """Validate SLURM time format"""
        patterns = [
            r'^\d+-\d{1,2}:\d{2}:\d{2}$',  # days-hours:mins:secs
            r'^\d{1,2}:\d{2}:\d{2}$',      # hours:mins:secs
            r'^\d{1,2}:\d{2}$',            # mins:secs
            r'^\d+$'                        # mins
        ]
        
        for pattern in patterns:
            if re.match(pattern, time_str):
                # Additional validation for hours/minutes/seconds ranges
                if ':' in time_str:
                    parts = time_str.replace('-', ':').split(':')
                    if len(parts) > 1 and int(parts[-2]) >= 60:  # minutes
                        return False
                    if len(parts) > 2 and int(parts[-3]) >= 24:  # hours
                        return False
                    if len(parts) > 0 and int(parts[-1]) >= 60:  # seconds
                        return False
                return True
        return False

    def get_job_params(self, job_type, nodes=None):
        """Get parameters for specific job type"""
        params = self.global_params.copy()
        
        if job_type.lower() in self.job_configs:
            params.update(self.job_configs[job_type.lower()])
            
        if nodes is not None:
            params['NODES'] = str(nodes)
            
        return params

    def format_sbatch_options(self, job_type, nodes=None):
        """Format parameters as SBATCH options"""
        params = self.get_job_params(job_type, nodes)
        options = []
        
        for key, value in params.items():
            if key == 'OUTPUT_DIR':
                continue
            elif key == 'OUTPUT_PATTERN':
                options.append(f"--output={params.get('OUTPUT_DIR', 'logs')}/{value}")
            elif key == 'ERROR_PATTERN':
                options.append(f"--error={params.get('OUTPUT_DIR', 'logs')}/{value}")
            elif key == 'JOB_NAME':
                options.append(f"--job-name={value}")
            elif key == 'MEM_PER_CPU':
                options.append(f"--mem-per-cpu={value}")
            elif key == 'NTASKS_PER_NODE':
                options.append(f"--ntasks-per-node={value}")
            elif key == 'NTASKS_PER_CORE':
                options.append(f"--ntasks-per-core={value}")
            elif key == 'CPUS_PER_TASK':
                options.append(f"--cpus-per-task={value}")
            elif key == 'GRES':
                options.append(f"--gres={value}")
            else:
                # Convert underscore to hyphen for SLURM compatibility
                slurm_key = key.lower().replace('_', '-')
                options.append(f"--{slurm_key}={value}")
                
        return options

    def format_sbatch_headers(self, job_type, nodes=None):
        """Format complete SBATCH headers as strings"""
        options = self.format_sbatch_options(job_type, nodes)
        headers = ["#!/bin/bash", "", "# SLURM job parameters"]
        
        for option in options:
            headers.append(f"#SBATCH {option}")
        
        headers.append("")
        return "\n".join(headers)

    def validate_config(self):
        """Validate configuration parameters"""
        issues = []
        required_params = ['PARTITION', 'TIME', 'JOB_NAME']
        
        for param in required_params:
            if param not in self.global_params:
                issues.append(f"Missing required parameter: {param}")
                
        if 'TIME' in self.global_params and not self._validate_time_format(self.global_params['TIME']):
            issues.append("Invalid time format in global parameters")
            
        for job_type, params in self.job_configs.items():
            if 'TIME' in params and not self._validate_time_format(params['TIME']):
                issues.append(f"Invalid time format in {job_type} configuration")
                
        return issues

    def get_global_params(self):
        """Get global configuration parameters"""
        return self.global_params.copy() 