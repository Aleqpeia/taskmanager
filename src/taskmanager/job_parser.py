"""
Enhanced job parser with dynamic production chunk handling
"""

import yaml
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from .utils import ValidationError, TaskManagerError


class JobParser:
    """Enhanced job parser with automatic chunk script generation"""
    
    def __init__(self, job_file: str, profile: Optional[str] = None):
        self.job_file = job_file
        self.profile = profile
        self.workflow_data = self.load_workflow()
    
    def load_workflow(self) -> Dict[str, Any]:
        """Load workflow configuration with better error handling"""
        job_path = Path(self.job_file)
        
        if not job_path.exists():
            raise ValidationError(f"Job file not found: {self.job_file}")
        
        try:
            with open(job_path, 'r') as f:
                if job_path.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            # Validate required structure
            if not isinstance(data, dict):
                raise ValidationError("Job file must contain a dictionary")
            
            if 'jobs' not in data:
                raise ValidationError("Job file must contain 'jobs' section")
            
            return data
            
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML in {self.job_file}: {e}")
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in {self.job_file}: {e}")
        except Exception as e:
            raise ValidationError(f"Error loading {self.job_file}: {e}")
    
    def get_jobs(self) -> List[Dict[str, Any]]:
        """Get processed jobs with dynamic chunk generation"""
        jobs = self.workflow_data.get('jobs', [])
        processed_jobs = []
        
        for job in jobs:
            processed_job = self.process_job(job)
            processed_jobs.append(processed_job)
        
        return processed_jobs
    
    def process_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Process individual job with chunk handling and profile overrides"""
        processed_job = job.copy()
        
        # Apply profile overrides if specified
        if self.profile:
            processed_job = self.apply_profile(processed_job)
        
        # Handle chunked production jobs
        if self.is_chunked_job(processed_job):
            processed_job = self.expand_chunked_job(processed_job)
        
        return processed_job
    
    def is_chunked_job(self, job: Dict[str, Any]) -> bool:
        """Check if job uses chunking"""
        chunk_config = job.get('chunk_config', {})
        return chunk_config.get('enabled', False)
    
    def expand_chunked_job(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Expand chunked job into individual scripts"""
        chunk_config = job.get('chunk_config', {})
        
        total_chunks = chunk_config.get('total_chunks', 5)
        script_prefix = chunk_config.get('script_prefix', 'prod_chunk')
        
        # Generate script list dynamically
        scripts = []
        outputs = []
        
        for chunk_num in range(1, total_chunks + 1):
            script_name = f"{script_prefix}{chunk_num}.sh"
            scripts.append(script_name)
            
            # Generate expected outputs
            output_prefix = f"{script_prefix}{chunk_num}"
            outputs.extend([
                f"{output_prefix}.xtc",
                f"{output_prefix}.edr",
                f"{output_prefix}.gro"
            ])
        
        # Update job with generated scripts
        job['scripts'] = scripts
        job['outputs'] = outputs
        job['total_scripts'] = len(scripts)
        
        # Add chunk metadata for batch script generation
        job['is_chunked'] = True
        job['chunk_metadata'] = {
            'total_chunks': total_chunks,
            'chunk_length_ns': chunk_config.get('chunk_length_ns', 10),
            'template_mdp': chunk_config.get('template_mdp', 'step7_production.mdp')
        }
        
        return job
    
    def apply_profile(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Apply execution profile settings"""
        profiles = self.workflow_data.get('execution_profiles', {})
        
        if self.profile not in profiles:
            return job
        
        profile_config = profiles[self.profile]
        job_name = job['name']
        
        if job_name in profile_config:
            job_overrides = profile_config[job_name]
            
            # Apply direct parameter overrides (like nodes)
            for key, value in job_overrides.items():
                if key != 'chunk_config':
                    job[key] = value
            
            # Apply chunk_config overrides
            if 'chunk_config' in job_overrides:
                current_chunk_config = job.get('chunk_config', {})
                chunk_overrides = job_overrides['chunk_config']
                current_chunk_config.update(chunk_overrides)
                job['chunk_config'] = current_chunk_config
        
        return job
    
    def show_workflow_summary(self):
        """Display workflow summary with chunk information"""
        workflow = self.workflow_data.get('workflow', {})
        jobs = self.get_jobs()
        
        print(f"\n=== Workflow: {workflow.get('name', 'Unknown')} ===")
        if self.profile:
            print(f"Profile: {self.profile}")
        print(f"Description: {workflow.get('description', 'No description')}")
        print(f"Base path: {workflow.get('base_path', '.')}")
        print()
        
        for i, job in enumerate(jobs, 1):
            print(f"{i}. {job['name']} ({job.get('job_type', 'default')})")
            print(f"   Path: {job['path']}")
            print(f"   Nodes: {job.get('nodes', 1)}")
            
            if job.get('is_chunked', False):
                chunk_meta = job['chunk_metadata']
                total_time = chunk_meta['total_chunks'] * chunk_meta['chunk_length_ns']
                print(f"   Chunked: {chunk_meta['total_chunks']} chunks × {chunk_meta['chunk_length_ns']} ns = {total_time} ns total")
                print(f"   Scripts: {job['scripts'][0]} ... {job['scripts'][-1]} ({len(job['scripts'])} total)")
            else:
                scripts = job.get('scripts', [])
                if len(scripts) <= 3:
                    print(f"   Scripts: {', '.join(scripts)}")
                else:
                    print(f"   Scripts: {scripts[0]}, {scripts[1]}, ... ({len(scripts)} total)")
            
            if job.get('depends_on'):
                print(f"   Depends on: {', '.join(job['depends_on'])}")
            print()
        
        print("=" * 50)

    def parse_jobs(self, job_file: str) -> Dict[str, Any]:
        """Parse job configuration from YAML file"""
        job_path = Path(job_file)
        
        if not job_path.exists():
            raise ValidationError(f"Job file not found: {job_file}")
        
        try:
            with open(job_path, 'r') as f:
                workflow = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValidationError(f"Invalid YAML in {job_file}: {e}")
        
        # Validate workflow structure
        self._validate_workflow(workflow)
        
        return workflow
    
    def _validate_workflow(self, workflow: Dict[str, Any]):
        """Validate workflow structure"""
        if 'workflow' not in workflow:
            raise ValidationError("Missing 'workflow' section")
        
        if 'jobs' not in workflow:
            raise ValidationError("Missing 'jobs' section")
        
        workflow_info = workflow['workflow']
        required_fields = ['name', 'description']
        
        for field in required_fields:
            if field not in workflow_info:
                raise ValidationError(f"Missing required workflow field: {field}")
        
        # Validate jobs
        jobs = workflow['jobs']
        if not isinstance(jobs, list):
            raise ValidationError("'jobs' must be a list")
        
        for i, job in enumerate(jobs):
            self._validate_job(job, i)
    
    def _validate_job(self, job: Dict[str, Any], index: int):
        """Validate individual job configuration"""
        required_fields = ['name', 'path', 'job_type', 'scripts']
        
        for field in required_fields:
            if field not in job:
                raise ValidationError(f"Job {index}: Missing required field '{field}'")
        
        # Validate scripts list
        scripts = job['scripts']
        if not isinstance(scripts, list) or not scripts:
            raise ValidationError(f"Job {index}: 'scripts' must be a non-empty list")
        
        # Validate job_type
        valid_types = ['minimization', 'equilibration', 'production']
        if job['job_type'] not in valid_types:
            raise ValidationError(
                f"Job {index}: Invalid job_type '{job['job_type']}'. "
                f"Must be one of: {', '.join(valid_types)}"
            )
        
        # Validate nodes if present
        if 'nodes' in job:
            try:
                nodes = int(job['nodes'])
                if nodes < 1:
                    raise ValidationError(f"Job {index}: 'nodes' must be >= 1")
            except ValueError:
                raise ValidationError(f"Job {index}: 'nodes' must be an integer")