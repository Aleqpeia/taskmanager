#!/usr/bin/env python3
"""
SLURM Task Manager - Production Main Module
For PCSS Eagle Altair HPC Cluster
"""

import sys
import argparse
from pathlib import Path
from .config import SlurmConfig
from .job_parser import JobParser
from .batch import BatchManager
from .script_generator import ScriptGenerator
from .equilibration_generator import EquilibrationGenerator
from .production_chunker import ProductionChunker
from .utils import setup_logging, TaskManagerError

def setup_argument_parser():
    """Setup command line argument parser"""
    parser = argparse.ArgumentParser(
        description="SLURM Task Manager for Multi-stage MD Simulations",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Submit batch job')
    batch_parser.add_argument('--job-file', default='jobs.yaml', help='Job configuration file')
    batch_parser.add_argument('--execution', choices=['sequential', 'parallel'], default='sequential')
    batch_parser.add_argument('--profile', help='Execution profile')
    batch_parser.add_argument('--config', default='.slurmparams', help='SLURM config file')
    batch_parser.add_argument('--output', default='batch_job.sh', help='Output script name')
    batch_parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    
    # Generate scripts command
    gen_parser = subparsers.add_parser('generate-scripts', help='Generate scripts from templates')
    gen_parser.add_argument('--config', required=True, help='Script configuration file')
    gen_parser.add_argument('--output-dir', default='.', help='Output directory')
    gen_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files')
    
    # Generate chunks command
    chunk_parser = subparsers.add_parser('generate-chunks', help='Generate production chunks')
    chunk_parser.add_argument('--chunks', type=int, required=True, help='Number of chunks')
    chunk_parser.add_argument('--length-ns', type=int, required=True, help='Length per chunk (ns)')
    chunk_parser.add_argument('--path', default='.', help='Output path')
    chunk_parser.add_argument('--template', default='step7_production.mdp', help='MDP template')
    
    # Show config command
    config_parser = subparsers.add_parser('show-config', help='Show SLURM configuration')
    config_parser.add_argument('--config', default='.slurmparams', help='Config file')
    
    # Validate workflow command
    validate_parser = subparsers.add_parser('validate-workflow', help='Validate job workflow')
    validate_parser.add_argument('--job-file', default='jobs.yaml', help='Job file to validate')
    
    return parser

def cmd_batch(args):
    """Handle batch command"""
    try:
        config = SlurmConfig(args.config)
        parser = JobParser(config)
        
        # Parse jobs
        workflow = parser.parse_jobs(args.job_file)
        jobs = workflow.get('jobs', [])
        
        if not jobs:
            print("No jobs found in workflow")
            return 1
            
        # Initialize batch manager
        batch_manager = BatchManager(config)
        
        # Generate batch script
        output_file = getattr(args, 'output', 'batch_job.sh')
        execution_mode = getattr(args, 'execution', 'sequential')
        dry_run = getattr(args, 'dry_run', False)
        
        batch_script = batch_manager.generate_batch_script(
            jobs, output_file, execution_mode, dry_run
        )
        
        print(f"Generated batch script: {batch_script}")
        
        if dry_run:
            print("\n=== Generated Script Content ===")
            with open(batch_script, 'r') as f:
                print(f.read())
        else:
            print(f"\nTo submit jobs, run: ./{batch_script}")
            
        return 0
        
    except Exception as e:
        print(f"Error in batch mode: {e}")
        return 1

def cmd_generate_chunks(args):
    """Handle generate-chunks command"""
    try:
        chunker = ProductionChunker(
            total_chunks=args.chunks,
            chunk_length_ns=args.length_ns
        )
        
        scripts = chunker.generate_chunk_scripts(args.path, args.template)
        
        print(f"Generated {len(scripts)} chunk scripts:")
        for script in scripts:
            print(f"  {script}")
        
        chunker.show_chunk_summary()
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

def cmd_show_config(args):
    """Handle show-config command"""
    try:
        config = SlurmConfig(args.config)
        
        print(f"=== SLURM Configuration ({args.config}) ===")
        print("\nGlobal Parameters:")
        for key, value in config.get_global_params().items():
            print(f"  {key}: {value}")
        
        print("\nJob-specific Configurations:")
        for job_type, params in config.job_configs.items():
            print(f"  [{job_type}]")
            for key, value in params.items():
                print(f"    {key}: {value}")
        
        # Validate configuration
        issues = config.validate_config()
        if issues:
            print("\n⚠️  Configuration Issues:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print("\n✅ Configuration is valid")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

def cmd_validate_workflow(args):
    """Handle validate-workflow command"""
    try:
        # Check if job file exists
        job_file = Path(args.job_file)
        if not job_file.exists():
            print(f"Error: Job file not found: {args.job_file}")
            return 1
        
        # Parse and validate jobs
        job_parser = JobParser(args.job_file)
        jobs = job_parser.get_jobs()
        
        print(f"=== Workflow Validation ({args.job_file}) ===")
        print(f"Found {len(jobs)} jobs:")
        
        for i, job in enumerate(jobs, 1):
            print(f"\n{i}. {job['name']} ({job['job_type']})")
            print(f"   Path: {job.get('path', 'N/A')}")
            print(f"   Scripts: {len(job.get('scripts', []))}")
            
            if job.get('is_chunked'):
                chunk_config = job.get('chunk_config', {})
                total_ns = chunk_config.get('total_chunks', 0) * chunk_config.get('chunk_length_ns', 0)
                print(f"   Chunked: {chunk_config.get('total_chunks', 0)} × {chunk_config.get('chunk_length_ns', 0)} ns = {total_ns} ns total")
        
        print("\n✅ Workflow validation completed")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

def main():
    """Main entry point"""
    parser = setup_argument_parser()
    
    if len(sys.argv) == 1:
        parser.print_help()
        return 0
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(verbose=False)
    
    # Route to appropriate command handler
    if args.command == 'batch':
        return cmd_batch(args)
    elif args.command == 'generate-chunks':
        return cmd_generate_chunks(args)
    elif args.command == 'show-config':
        return cmd_show_config(args)
    elif args.command == 'validate-workflow':
        return cmd_validate_workflow(args)
    else:
        print(f"Command not implemented: {args.command}")
        return 1

if __name__ == '__main__':
    sys.exit(main())