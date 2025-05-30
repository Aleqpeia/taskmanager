"""
SLURM Task Manager - Main entry point
Enhanced with job-specific resource management and dynamic chunking
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from .config import SlurmConfig
from .job_parser import JobParser
from .batch import BatchManager
from .equilibration_generator import EquilibrationGenerator
from .production_chunker import ProductionChunker
from .script_generator import ScriptGenerator


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser with all subcommands"""
    parser = argparse.ArgumentParser(
        description="SLURM Task Manager for Multi-stage MD Simulations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m taskmanager generate-script batch --job-file jobs.yaml
  python -m taskmanager show-config --config .slurmparams
  python -m taskmanager generate-chunks --chunks 50 --length-ns 20
  python -m taskmanager validate-workflow --job-file jobs.yaml
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Batch script generation
    batch_parser = subparsers.add_parser('generate-script', help='Generate batch scripts')
    batch_subparsers = batch_parser.add_subparsers(dest='script_type', help='Script type')
    
    # Batch script
    batch_script_parser = batch_subparsers.add_parser('batch', help='Generate batch submission script')
    batch_script_parser.add_argument('--job-file', default='jobs.yaml', help='YAML job definition file')
    batch_script_parser.add_argument('--execution', choices=['sequential', 'parallel'], 
                                    default='sequential', help='Execution mode')
    batch_script_parser.add_argument('--profile', help='Execution profile')
    batch_script_parser.add_argument('--output', default='batch_job.sh', help='Output script file')
    batch_script_parser.add_argument('--dry-run', action='store_true', help='Show script without writing')
    
    # Configuration management
    config_parser = subparsers.add_parser('show-config', help='Show SLURM configuration')
    config_parser.add_argument('--config', default='.slurmparams', help='Configuration file')
    
    job_types_parser = subparsers.add_parser('show-job-types', help='Show available job types')
    job_types_parser.add_argument('--config', default='.slurmparams', help='Configuration file')
    
    # Script generation
    scripts_parser = subparsers.add_parser('generate-scripts', help='Generate scripts from configuration')
    scripts_parser.add_argument('--config', default='script_configs.yaml', help='Script configuration file')
    scripts_parser.add_argument('--output-dir', default='.', help='Output directory')
    scripts_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing files')
    
    script_config_parser = subparsers.add_parser('show-script-config', help='Show script configuration')
    script_config_parser.add_argument('--config', default='script_configs.yaml', help='Script configuration file')
    
    # Custom script generation
    custom_script_parser = subparsers.add_parser('generate-custom-script', help='Generate custom script')
    custom_script_parser.add_argument('--type', required=True, help='Script type')
    custom_script_parser.add_argument('--output', required=True, help='Output file')
    custom_script_parser.add_argument('--set', action='append', metavar='KEY=VALUE', 
                                     help='Set custom parameter (can be used multiple times)')
    
    # Equilibration script generation
    equil_parser = subparsers.add_parser('generate-equilibration', help='Generate equilibration scripts')
    equil_parser.add_argument('--mdp-dir', default='.', help='Directory containing MDP files')
    equil_parser.add_argument('--output-dir', default='.', help='Output directory for scripts')
    equil_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing scripts')
    equil_parser.add_argument('--backup', action='store_true', help='Backup existing scripts')
    
    equil_show_parser = subparsers.add_parser('show-equilibration', help='Show discovered MDP files')
    equil_show_parser.add_argument('--mdp-dir', default='.', help='Directory containing MDP files')
    
    # Production chunk generation
    chunks_parser = subparsers.add_parser('generate-chunks', help='Generate production chunk scripts')
    chunks_parser.add_argument('--chunks', type=int, required=True, help='Number of chunks')
    chunks_parser.add_argument('--length-ns', type=float, required=True, help='Length per chunk (ns)')
    chunks_parser.add_argument('--path', default='.', help='Output directory')
    chunks_parser.add_argument('--template', default='step7_production.mdp', help='Template MDP file')
    chunks_parser.add_argument('--script-prefix', default='prod_chunk', help='Script name prefix')
    chunks_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing scripts')
    
    # Job parsing and validation
    parse_parser = subparsers.add_parser('parse-jobs', help='Parse and show job configuration')
    parse_parser.add_argument('--job-file', default='jobs.yaml', help='YAML job definition file')
    parse_parser.add_argument('--profile', help='Execution profile')
    parse_parser.add_argument('--format', choices=['summary', 'detailed', 'json'], 
                             default='summary', help='Output format')
    
    validate_parser = subparsers.add_parser('validate-workflow', help='Validate workflow configuration')
    validate_parser.add_argument('--job-file', default='jobs.yaml', help='YAML job definition file')
    validate_parser.add_argument('--check-files', action='store_true', help='Check if required files exist')
    
    return parser


def handle_generate_batch_script(args):
    """Handle batch script generation"""
    try:
        # Load configuration
        config = SlurmConfig(args.config if hasattr(args, 'config') else '.slurmparams')
        
        # Parse jobs
        job_parser = JobParser(args.job_file, args.profile)
        jobs = job_parser.get_jobs()
        
        # Generate batch script
        batch_manager = BatchManager(config)
        script_content = batch_manager.generate_script(jobs, args.execution)
        
        if args.dry_run:
            print("=== Generated Batch Script ===")
            print(script_content)
        else:
            with open(args.output, 'w') as f:
                f.write(script_content)
            # Make script executable
            import os
            os.chmod(args.output, 0o755)
            print(f"Generated batch script: {args.output}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_show_config(args):
    """Handle configuration display"""
    try:
        config = SlurmConfig(args.config)
        config.show_summary()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_show_job_types(args):
    """Handle job types display"""
    try:
        config = SlurmConfig(args.config)
        job_types = config.get_available_job_types()
        
        print(f"\n=== Available Job Types ({args.config}) ===")
        if job_types:
            for job_type in job_types:
                print(f"  - {job_type}")
                # Show sample configuration
                params = config.get_job_params(job_type)
                key_params = ['NODES', 'TIME', 'CPUS_PER_TASK', 'NTASKS_PER_NODE']
                param_str = ", ".join([f"{k}={params.get(k, 'N/A')}" for k in key_params if k in params])
                print(f"    ({param_str})")
        else:
            print("  No job-specific types configured.")
            print("  All jobs will use global parameters.")
        print("=" * 40)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_generate_scripts(args):
    """Handle script generation from configuration"""
    try:
        import yaml
        
        # Load script configuration
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        
        with open(config_path, 'r') as f:
            script_config = yaml.safe_load(f)
        
        generator = ScriptGenerator()
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        generated_count = 0
        
        # Generate scripts for each stage
        for stage_name, stage_scripts in script_config.items():
            if stage_name == 'global':
                continue
                
            print(f"\n=== Generating {stage_name} scripts ===")
            
            for script_name, script_info in stage_scripts.items():
                script_type = script_info.get('type', script_name)
                custom_config = script_info.get('config', {})
                
                output_file = output_dir / f"{script_name}.sh"
                
                # Check for existing file
                if output_file.exists() and not args.overwrite:
                    print(f"  Skipping {script_name}.sh (exists, use --overwrite)")
                    continue
                
                try:
                    generated_path = generator.generate_script(script_type, output_file, custom_config)
                    print(f"  Generated: {script_name}.sh")
                    generated_count += 1
                except Exception as e:
                    print(f"  Error generating {script_name}.sh: {e}")
        
        print(f"\nGenerated {generated_count} scripts in {output_dir}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_show_script_config(args):
    """Handle script configuration display"""
    try:
        import yaml
        
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
            sys.exit(1)
        
        with open(config_path, 'r') as f:
            script_config = yaml.safe_load(f)
        
        print(f"\n=== Script Configuration ({args.config}) ===")
        
        for stage_name, stage_scripts in script_config.items():
            if stage_name == 'global':
                continue
                
            print(f"\n{stage_name.upper()}:")
            for script_name, script_info in stage_scripts.items():
                script_type = script_info.get('type', script_name)
                custom_config = script_info.get('config', {})
                
                print(f"  {script_name}.sh ({script_type})")
                if custom_config:
                    for key, value in custom_config.items():
                        print(f"    {key}: {value}")
        
        print("=" * 45)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_generate_equilibration(args):
    """Handle equilibration script generation"""
    try:
        generator = EquilibrationGenerator(args.mdp_dir)
        
        if hasattr(args, 'show') and args.show:
            generator.show_discovered_mdps()
        else:
            scripts = generator.generate_scripts(
                output_dir=args.output_dir,
                overwrite=args.overwrite,
                backup=getattr(args, 'backup', False)
            )
            print(f"Generated {len(scripts)} equilibration scripts in {args.output_dir}")
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_show_equilibration(args):
    """Handle equilibration MDP discovery"""
    try:
        generator = EquilibrationGenerator(args.mdp_dir)
        generator.show_discovered_mdps()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_generate_chunks(args):
    """Handle production chunk generation"""
    try:
        chunker = ProductionChunker(
            chunk_length_ns=args.length_ns,
            total_chunks=args.chunks
        )
        
        output_path = Path(args.path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        scripts = chunker.generate_chunk_scripts(
            base_path=str(output_path),
            template_mdp=args.template,
            script_prefix=args.script_prefix,
            overwrite=args.overwrite
        )
        
        total_time = args.chunks * args.length_ns
        print(f"Generated {len(scripts)} production chunk scripts")
        print(f"Total simulation time: {total_time} ns ({args.chunks} × {args.length_ns} ns)")
        print(f"Output directory: {output_path}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_parse_jobs(args):
    """Handle job parsing and display"""
    try:
        job_parser = JobParser(args.job_file, args.profile)
        
        if args.format == 'summary':
            job_parser.show_workflow_summary()
        elif args.format == 'detailed':
            jobs = job_parser.get_jobs()
            for i, job in enumerate(jobs, 1):
                print(f"\n=== Job {i}: {job['name']} ===")
                for key, value in job.items():
                    if key == 'scripts' and len(value) > 5:
                        print(f"  {key}: {value[:3]} ... ({len(value)} total)")
                    else:
                        print(f"  {key}: {value}")
        elif args.format == 'json':
            jobs = job_parser.get_jobs()
            print(json.dumps(jobs, indent=2))
            
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_validate_workflow(args):
    """Handle workflow validation"""
    try:
        job_parser = JobParser(args.job_file)
        jobs = job_parser.get_jobs()
        
        print("=== Workflow Validation ===")
        print(f"Job file: {args.job_file}")
        print(f"Jobs found: {len(jobs)}")
        
        errors = []
        warnings = []
        
        for job in jobs:
            job_name = job['name']
            job_path = Path(job['path'])
            
            # Check if path exists
            if not job_path.exists():
                warnings.append(f"Job '{job_name}': Path does not exist: {job_path}")
            
            # Check scripts exist if file checking is enabled
            if args.check_files:
                scripts = job.get('scripts', [])
                for script in scripts:
                    script_path = job_path / script
                    if not script_path.exists():
                        errors.append(f"Job '{job_name}': Script not found: {script_path}")
            
            # Check dependencies
            depends_on = job.get('depends_on', [])
            for dep in depends_on:
                dep_path = Path(dep)
                if args.check_files and not dep_path.exists():
                    warnings.append(f"Job '{job_name}': Dependency not found: {dep_path}")
        
        # Report results
        if errors:
            print(f"\nERRORS ({len(errors)}):")
            for error in errors:
                print(f"  ❌ {error}")
        
        if warnings:
            print(f"\nWARNINGS ({len(warnings)}):")
            for warning in warnings:
                print(f"  ⚠️  {warning}")
        
        if not errors and not warnings:
            print("\n✅ Workflow validation passed!")
        elif errors:
            print(f"\n❌ Workflow validation failed with {len(errors)} errors")
            sys.exit(1)
        else:
            print(f"\n⚠️  Workflow validation passed with {len(warnings)} warnings")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def handle_generate_custom_script(args):
    """Handle custom script generation"""
    try:
        generator = ScriptGenerator()
        
        # Parse custom parameters
        custom_config = {}
        if args.set:
            for param in args.set:
                if '=' not in param:
                    print(f"Error: Invalid parameter format: {param} (expected KEY=VALUE)", file=sys.stderr)
                    sys.exit(1)
                key, value = param.split('=', 1)
                custom_config[key] = value
        
        generated_path = generator.generate_script(args.type, args.output, custom_config)
        print(f"Generated custom {args.type} script: {generated_path}")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Handle different commands
    if args.command == 'generate-script':
        if args.script_type == 'batch':
            handle_generate_batch_script(args)
        else:
            print(f"Unknown script type: {args.script_type}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == 'show-config':
        handle_show_config(args)
    
    elif args.command == 'show-job-types':
        handle_show_job_types(args)
    
    elif args.command == 'generate-scripts':
        handle_generate_scripts(args)
    
    elif args.command == 'show-script-config':
        handle_show_script_config(args)
    
    elif args.command == 'generate-custom-script':
        handle_generate_custom_script(args)
    
    elif args.command == 'generate-equilibration':
        handle_generate_equilibration(args)
    
    elif args.command == 'show-equilibration':
        handle_show_equilibration(args)
    
    elif args.command == 'generate-chunks':
        handle_generate_chunks(args)
    
    elif args.command == 'parse-jobs':
        handle_parse_jobs(args)
    
    elif args.command == 'validate-workflow':
        handle_validate_workflow(args)
    
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()