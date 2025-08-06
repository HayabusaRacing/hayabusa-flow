#!/usr/bin/env python3
"""
OpenFOAM Manual Simulation Runner
=================================
A script to manually set up and run OpenFOAM simulations with custom STL files.

Features:
- STL folder selection with automatic file detection
- BaseCase copying with customizable destination
- Automatic OpenFOAM simulation execution
- C_D coefficient extraction from results

Usage:
    python main.py [OPTIONS]
    
Options:
    --case-dir PATH        Destination case directory (default: ./case)
    --base-dir PATH        Base case directory (default: ./baseCase)
    --stl-dir PATH         Directory containing STL files (optional, will prompt if not provided)
    --n-proc N            Number of processors for parallel run (default: 6)
    --auto-run            Skip confirmations and run automatically
    --cli-mode            Use command line interface for folder selection (no GUI)
"""

import shutil
import os
import sys
import argparse
import time
import numpy as np
import trimesh
import re
from pathlib import Path
from tkinter import filedialog
import tkinter as tk
from typing import Dict, Optional

# Import OpenFOAM runners from your existing code
from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.Execution.UtilityRunner import UtilityRunner
from PyFoam.Execution.BasicRunner import BasicRunner


class STLFileSelector:
    """Handle STL folder selection and automatic file detection"""
    
    def __init__(self):
        self.stl_components = ["FL", "FR", "RL", "RR", "mainBody"]
        self.selected_files = {}
    
    def _find_stl_files_in_folder(self, folder_path: str) -> Dict[str, str]:
        """Find STL files for each component in the given folder"""
        folder = Path(folder_path)
        found_files = {}
        
        # Get all STL files in the folder
        stl_files = list(folder.glob("*.stl"))
        
        print(f"\nFound {len(stl_files)} STL files in folder:")
        for stl_file in stl_files:
            print(f"  {stl_file.name}")
        
        # Try to match each component
        for component in self.stl_components:
            matching_files = []
            
            # Look for files that contain the component name (case-insensitive)
            for stl_file in stl_files:
                filename = stl_file.name.lower()
                component_lower = component.lower()
                
                # Check various naming patterns
                if (component_lower in filename or 
                    filename.startswith(component_lower) or 
                    filename.endswith(f"{component_lower}.stl")):
                    matching_files.append(stl_file)
            
            if len(matching_files) == 1:
                found_files[component] = str(matching_files[0])
                print(f"✓ {component}: {matching_files[0].name}")
            elif len(matching_files) > 1:
                print(f"⚠ Multiple files found for {component}:")
                for i, file in enumerate(matching_files):
                    print(f"  {i+1}. {file.name}")
                
                while True:
                    try:
                        choice = input(f"Select file for {component} (1-{len(matching_files)}): ").strip()
                        idx = int(choice) - 1
                        if 0 <= idx < len(matching_files):
                            found_files[component] = str(matching_files[idx])
                            print(f"✓ {component}: {matching_files[idx].name}")
                            break
                        else:
                            print("Invalid choice. Please try again.")
                    except ValueError:
                        print("Please enter a valid number.")
            else:
                print(f"✗ No file found for {component}")
                return {}
        
        return found_files
    
    def select_files_gui(self) -> Dict[str, str]:
        """Select STL folder using GUI dialog"""
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        
        print("Please select the folder containing your STL files...")
        
        folder_path = filedialog.askdirectory(
            title="Select folder containing STL files"
        )
        
        if not folder_path:
            print("No folder selected. Exiting...")
            sys.exit(1)
        
        print(f"Selected folder: {folder_path}")
        
        root.destroy()
        
        # Find STL files in the selected folder
        self.selected_files = self._find_stl_files_in_folder(folder_path)
        
        if not self.selected_files:
            print("Could not find all required STL files in the selected folder.")
            sys.exit(1)
        
        return self.selected_files
    
    def select_files_cli(self) -> Dict[str, str]:
        """Select STL folder using command line interface"""
        while True:
            folder_path = input("\nEnter path to folder containing STL files: ").strip()
            
            if not folder_path:
                print("Path cannot be empty. Please try again.")
                continue
            
            if not os.path.exists(folder_path):
                print(f"Folder does not exist: {folder_path}. Please try again.")
                continue
            
            if not os.path.isdir(folder_path):
                print(f"Path is not a directory: {folder_path}. Please try again.")
                continue
            
            print(f"Selected folder: {folder_path}")
            
            # Find STL files in the selected folder
            self.selected_files = self._find_stl_files_in_folder(folder_path)
            
            if not self.selected_files:
                print("Could not find all required STL files in the selected folder.")
                continue
            
            break
        
        return self.selected_files


class CaseSetup:
    """Handle OpenFOAM case setup and STL file copying"""
    
    def __init__(self, base_dir: str, case_dir: str, n_proc: int = 6):
        self.base_dir = Path(base_dir)
        self.case_dir = Path(case_dir)
        self.n_proc = n_proc
    
    def setup_case(self, stl_files: Dict[str, str]) -> bool:
        """Set up the OpenFOAM case with selected STL files"""
        try:
            # Remove existing case directory if it exists
            if self.case_dir.exists():
                print(f"Removing existing case directory: {self.case_dir}")
                shutil.rmtree(self.case_dir)
            
            # Copy base case
            print(f"Copying base case from {self.base_dir} to {self.case_dir}")
            shutil.copytree(self.base_dir, self.case_dir)
            
            # Copy STL files to triSurface directory
            tri_surface_dir = self.case_dir / "constant" / "triSurface"
            tri_surface_dir.mkdir(parents=True, exist_ok=True)
            
            wheel_centers = {}
            
            for component, file_path in stl_files.items():
                dest_name = f"{component}.stl"
                dest_path = tri_surface_dir / dest_name
                
                print(f"Copying {component}: {file_path} → {dest_path}")
                shutil.copy2(file_path, dest_path)
                
                # Calculate centroid for wheel components
                if component in ["FL", "FR", "RL", "RR"]:
                    try:
                        mesh = trimesh.load(file_path)
                        centroid = mesh.centroid
                        wheel_centers[component] = centroid
                        print(f"  Calculated {component} center: ({centroid[0]:.8f} {centroid[1]:.6f} {centroid[2]:.6f})")
                    except Exception as e:
                        print(f"  Warning: Could not calculate centroid for {component}: {e}")
            
            # Update wheel centers in U file
            if wheel_centers:
                self._update_wheel_centers(wheel_centers)
            
            # Update decomposeParDict with processor count
            self._update_decompose_par_dict()
            
            print(f"✓ Case setup completed successfully!")
            return True
            
        except Exception as e:
            print(f"Error setting up case: {e}")
            return False
    
    def _update_decompose_par_dict(self):
        """Update decomposeParDict with the correct number of processors"""
        decompose_file = self.case_dir / "system" / "decomposeParDict"
        
        if decompose_file.exists():
            # Read the file
            with open(decompose_file, 'r') as f:
                content = f.read()
            
            # Replace numberOfSubdomains
            import re
            content = re.sub(r'numberOfSubdomains\s+\d+;', f'numberOfSubdomains {self.n_proc};', content)
            
            # Write back
            with open(decompose_file, 'w') as f:
                f.write(content)
            
            print(f"Updated decomposeParDict to use {self.n_proc} processors")
    
    def _update_wheel_centers(self, wheel_centers: Dict[str, np.ndarray]):
        """Update wheel center coordinates in the U file based on STL centroids"""
        u_file = self.case_dir / "0" / "U"
        
        if not u_file.exists():
            print(f"Warning: U file not found at {u_file}")
            return
        
        # Read the U file
        with open(u_file, 'r') as f:
            content = f.read()
        
        print("Updating wheel centers in U file...")
        
        # Update each wheel's origin
        for component, centroid in wheel_centers.items():
            # Format centroid coordinates with appropriate precision
            origin_str = f"({centroid[0]:.8f} {centroid[1]:.6f} {centroid[2]:.6f})"
            
            # Create regex pattern to find and replace the origin line for this component
            # Pattern matches: component name, then rotatingWallVelocity block, then origin line
            pattern = rf'(\s+{component}\s*\{{\s*[\s\S]*?type\s+rotatingWallVelocity;\s*origin\s+)\([^)]+\)(;[\s\S]*?\}})'
            
            replacement = rf'\g<1>{origin_str}\g<2>'
            
            old_content = content
            content = re.sub(pattern, replacement, content)
            
            if content != old_content:
                print(f"  Updated {component} origin to: {origin_str}")
            else:
                print(f"  Warning: Could not find/update {component} origin in U file")
        
        # Write back the updated content
        with open(u_file, 'w') as f:
            f.write(content)
        
        print("✓ Wheel centers updated in U file")


class OpenFOAMRunner:
    """Handle OpenFOAM simulation execution using PyFoam"""
    
    def __init__(self, case_dir: str, n_proc: int = 6):
        self.case_dir = Path(case_dir)
        self.n_proc = n_proc
        
    def _run_with_log(self, argv, operation):
        """Run OpenFOAM command with verbose terminal output"""
        print(f"Running {operation}...")
        runner = UtilityRunner(argv=argv, silent=False)
        runner.quiet = False
        runner.start()
        runner.run.join()
        success = runner.run.returncode == 0
        if success:
            print(f"✓ {operation} completed successfully")
        else:
            print(f"✗ {operation} failed with return code: {runner.run.returncode}")
        return success
        
    def run_blockMesh(self):
        """Generate background mesh"""
        return self._run_with_log(["blockMesh", "-case", str(self.case_dir)], "blockMesh")
    
    def run_surfaceFeatureExtract(self, dictPath):
        """Extract surface features for a specific dictionary"""
        return self._run_with_log(
            ["surfaceFeatureExtract", "-case", str(self.case_dir), "-dict", str(dictPath)], 
            f"surfaceFeatureExtract ({dictPath})"
        )
    
    def run_snappyHexMesh(self):
        """Generate mesh using snappyHexMesh"""
        return self._run_with_log(
            ["snappyHexMesh", "-overwrite", "-case", str(self.case_dir)], 
            "snappyHexMesh"
        )

    def decompose_case(self):
        """Decompose case for parallel processing"""
        runner = UtilityRunner(argv=["decomposePar", "-force", "-case", str(self.case_dir)], silent=False)
        runner.quiet = False
        runner.start()
        runner.run.join()
        success = runner.run.returncode == 0
        if success:
            print("✓ Case decomposition completed")
        else:
            print("✗ Case decomposition failed")
        return success

    def run_parallel_simpleFoam(self):
        """Run simpleFoam solver in parallel"""
        print(f"Running simpleFoam with {self.n_proc} processors...")
        mpirun_cmd = ["mpirun", "--allow-run-as-root", "-np", str(self.n_proc), 
                     "simpleFoam", "-case", str(self.case_dir), "-parallel"]
        runner = BasicRunner(argv=mpirun_cmd, silent=False)
        runner.start()
        runner.run.join()
        success = runner.run.returncode == 0
        if success:
            print("✓ Parallel simpleFoam completed")
        else:
            print("✗ Parallel simpleFoam failed")
        return success

    def reconstruct_case(self):
        """Reconstruct parallel case results"""
        runner = UtilityRunner(argv=["reconstructPar", "-case", str(self.case_dir)], silent=False)
        runner.quiet = False
        runner.start()
        runner.run.join()
        success = runner.run.returncode == 0
        if success:
            print("✓ Case reconstruction completed")
        else:
            print("✗ Case reconstruction failed")
        return success
    
    def run_all_surfaceFeatureExtract(self):
        """Run surface feature extraction for all components"""
        dicts = [
            "system/surfaceFeatureExtract_mainBodyDict",
            "system/surfaceFeatureExtract_FLDict",
            "system/surfaceFeatureExtract_FRDict",
            "system/surfaceFeatureExtract_RLDict",
            "system/surfaceFeatureExtract_RRDict",
        ]
        for dict_path in dicts:
            if not self.run_surfaceFeatureExtract(dict_path):
                return False
        return True
    
    def run_full_simulation(self):
        """Run the complete OpenFOAM simulation pipeline"""
        print("Starting full OpenFOAM simulation pipeline...")
        start_time = time.time()
        
        steps = [
            ("Background mesh generation", self.run_blockMesh),
            ("Surface feature extraction", self.run_all_surfaceFeatureExtract),
            ("Mesh generation", self.run_snappyHexMesh),
            ("Case decomposition", self.decompose_case),
            ("Parallel solver", self.run_parallel_simpleFoam),
            ("Case reconstruction", self.reconstruct_case),
        ]
        
        for step_name, step_func in steps:
            print(f"\n{'='*60}")
            print(f"Step: {step_name}")
            print(f"{'='*60}")
            
            if not step_func():
                print(f"✗ Simulation failed at step: {step_name}")
                return False
        
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"\n{'='*60}")
        print(f"✓ Full simulation completed successfully!")
        print(f"Total time elapsed: {elapsed:.2f} seconds ({elapsed/60:.1f} minutes)")
        print(f"{'='*60}")
        
        return True


class ResultsExtractor:
    """Extract simulation results, particularly drag coefficient"""
    
    def __init__(self, case_dir: str):
        self.case_dir = Path(case_dir)
    
    def extract_latest_cd(self) -> Optional[Dict]:
        """Extract the latest drag coefficient from simulation results"""
        post_dir = self.case_dir / "postProcessing" / "forceCoeffs1" / "0"
        filepath = post_dir / "coefficient.dat"
        
        if not filepath.exists():
            print(f"Warning: coefficient.dat not found at: {filepath}")
            return None
        
        try:
            data = np.loadtxt(filepath, comments="#")
            if len(data) == 0:
                print("Warning: No data found in coefficient.dat")
                return None
            
            # Handle both 1D and 2D arrays
            if data.ndim == 1:
                latest_row = data
            else:
                latest_row = data[-1]
            
            time, Cd, Cl, Cm = latest_row[0], latest_row[1], latest_row[4], latest_row[6]
            
            result = {
                "time": time,
                "Cd": Cd,
                "Cl": Cl,
                "Cm": Cm
            }
            
            print(f"\n{'='*40}")
            print(f"SIMULATION RESULTS")
            print(f"{'='*40}")
            print(f"Time: {time:.6f}")
            print(f"Drag Coefficient (Cd): {Cd:.6f}")
            print(f"Lift Coefficient (Cl): {Cl:.6f}")
            print(f"Moment Coefficient (Cm): {Cm:.6f}")
            print(f"{'='*40}")
            
            return result
            
        except Exception as e:
            print(f"Error extracting results: {e}")
            return None


def main():
    """Main function to orchestrate the entire simulation process"""
    parser = argparse.ArgumentParser(
        description="OpenFOAM Manual Simulation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split('Usage:')[1].split('Options:')[0] + 
               'Options:\n' + __doc__.split('Options:')[1]
    )
    
    parser.add_argument('--case-dir', default='./case', 
                       help='Destination case directory (default: ./case)')
    parser.add_argument('--base-dir', default='./baseCase',
                       help='Base case directory (default: ./baseCase)')
    parser.add_argument('--stl-dir', 
                       help='Directory containing STL files (FL.stl, FR.stl, etc.). If not provided, will prompt for selection.')
    parser.add_argument('--n-proc', type=int, default=6,
                       help='Number of processors for parallel run (default: 6)')
    parser.add_argument('--auto-run', action='store_true',
                       help='Skip confirmations and run automatically')
    parser.add_argument('--cli-mode', action='store_true',
                       help='Use command line interface for file selection (no GUI)')
    
    args = parser.parse_args()
    
    print("="*60)
    print("OpenFOAM Manual Simulation Runner")
    print("="*60)
    
    # Validate base directory
    if not os.path.exists(args.base_dir):
        print(f"Error: Base directory does not exist: {args.base_dir}")
        sys.exit(1)
    
    # Step 1: Select STL folder
    print("\n1. STL Folder Selection")
    print("-" * 30)
    
    selector = STLFileSelector()
    try:
        if args.stl_dir:
            # Use provided STL directory
            if not os.path.exists(args.stl_dir):
                print(f"Error: STL directory does not exist: {args.stl_dir}")
                sys.exit(1)
            if not os.path.isdir(args.stl_dir):
                print(f"Error: STL path is not a directory: {args.stl_dir}")
                sys.exit(1)
            
            print(f"Using provided STL directory: {args.stl_dir}")
            stl_files = selector._find_stl_files_in_folder(args.stl_dir)
            
            if not stl_files:
                print("Could not find all required STL files in the provided directory.")
                sys.exit(1)
        else:
            # Use interactive selection
            if args.cli_mode:
                stl_files = selector.select_files_cli()
            else:
                stl_files = selector.select_files_gui()
    except Exception as e:
        print(f"Error during file selection: {e}")
        sys.exit(1)
    
    # Display selected files
    print(f"\nSelected STL files:")
    for component, file_path in stl_files.items():
        print(f"  {component}: {file_path}")
    
    # Step 2: Confirm settings
    if not args.auto_run:
        print(f"\nSimulation settings:")
        print(f"  Base directory: {args.base_dir}")
        print(f"  Case directory: {args.case_dir}")
        print(f"  Processors: {args.n_proc}")
        
        confirm = input(f"\nProceed with simulation? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Simulation cancelled.")
            sys.exit(0)
    
    # Step 3: Set up case
    print("\n2. Case Setup")
    print("-" * 30)
    
    case_setup = CaseSetup(args.base_dir, args.case_dir, args.n_proc)
    if not case_setup.setup_case(stl_files):
        print("Case setup failed. Exiting...")
        sys.exit(1)
    
    # Step 4: Run simulation
    print("\n3. Running Simulation")
    print("-" * 30)
    
    runner = OpenFOAMRunner(args.case_dir, args.n_proc)
    if not runner.run_full_simulation():
        print("Simulation failed. Exiting...")
        sys.exit(1)
    
    # Step 5: Extract results
    print("\n4. Extracting Results")
    print("-" * 30)
    
    extractor = ResultsExtractor(args.case_dir)
    results = extractor.extract_latest_cd()
    
    if results:
        # Save results to file
        results_file = Path(args.case_dir) / "simulation_results.txt"
        with open(results_file, 'w') as f:
            f.write("OpenFOAM Simulation Results\n")
            f.write("=" * 30 + "\n")
            f.write(f"Time: {results['time']:.6f}\n")
            f.write(f"Drag Coefficient (Cd): {results['Cd']:.6f}\n")
            f.write(f"Lift Coefficient (Cl): {results['Cl']:.6f}\n")
            f.write(f"Moment Coefficient (Cm): {results['Cm']:.6f}\n")
        
        print(f"Results saved to: {results_file}")
    else:
        print("Warning: Could not extract results from simulation.")
    
    print(f"\n{'='*60}")
    print("Simulation completed!")
    print(f"Case directory: {args.case_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
