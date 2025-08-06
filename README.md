# OpenFOAM Manual Simulation Runner

A comprehensive Python script for manually setting up and running OpenFOAM simulations with custom STL files.

## Features

- **STL Folder Selection**: Select a folder containing FL, FR, RL, RR, and mainBody STL files with automatic detection
- **Flexible Case Setup**: Copy baseCase to customizable destination with automatic configuration
- **Complete Simulation Pipeline**: Automated OpenFOAM workflow using PyFoam
- **Results Extraction**: Automatic C_D coefficient extraction from simulation results
- **Parallel Processing**: Configurable multi-processor simulation support

## Prerequisites

- OpenFOAM installation
- Python 3.x
- PyFoam library
- Required Python packages (see requirements.txt)

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure OpenFOAM and PyFoam are properly installed and configured.

## Usage

### Basic Usage (with GUI folder selection)
```bash
python main.py
```

### Command Line Options
```bash
python main.py [OPTIONS]

Options:
  --case-dir PATH     Destination case directory (default: ./case)
  --base-dir PATH     Base case directory (default: ./baseCase)
  --stl-dir PATH      Directory containing STL files (optional, will prompt if not provided)
  --n-proc N         Number of processors for parallel run (default: 6)
  --auto-run         Skip confirmations and run automatically
  --cli-mode         Use command line interface for folder selection (no GUI)
```

### Examples

1. **Basic run with GUI folder selection:**
```bash
python main.py
```

2. **Specify STL directory directly (no GUI needed):**
```bash
python main.py --stl-dir ./my_stl_files
```

3. **Specify custom directories and processor count:**
```bash
python main.py --stl-dir ./stl_files --case-dir ./my_simulation --n-proc 8
```

4. **Fully automated run (no prompts):**
```bash
python main.py --stl-dir ./stl_files --auto-run --n-proc 12
```

5. **CLI mode for server environments:**
```bash
python main.py --cli-mode --case-dir ./simulation_001
```

## Workflow

The script follows this automated workflow:

1. **STL Folder Selection**: Select a folder containing all required STL files (FL, FR, RL, RR, mainBody) with automatic detection
2. **Case Setup**: Copy baseCase to destination and update with detected STL files
3. **Mesh Generation**: 
   - Generate background mesh (blockMesh)
   - Extract surface features for all components
   - Generate final mesh (snappyHexMesh)
4. **Parallel Simulation**:
   - Decompose case for parallel processing
   - Run simpleFoam solver
   - Reconstruct results
5. **Results Extraction**: Extract drag coefficient (C_D) and other coefficients

## Output

The script generates:
- Complete OpenFOAM case in specified directory
- Simulation results with force coefficients
- `simulation_results.txt` file with extracted coefficients
- Console output with progress and timing information

## File Structure

After running, your case directory will contain:
```
case/
├── 0/                    # Initial conditions
├── constant/
│   ├── triSurface/      # Your detected STL files (FL.stl, FR.stl, etc.)
│   └── ...
├── system/              # Solver configuration
├── postProcessing/      # Results data
└── simulation_results.txt
```

## Troubleshooting

1. **PyFoam import errors**: Ensure PyFoam is properly installed and OpenFOAM environment is sourced
2. **STL file issues**: Verify STL files are valid and properly formatted
3. **Parallel processing**: Adjust `--n-proc` based on your system capabilities
4. **Memory issues**: Reduce mesh resolution in baseCase if experiencing memory problems

## Integration Notes

This script is designed to work alongside your existing genetic algorithm workflow, providing a manual interface for:
- Testing individual configurations
- Validating STL files before batch processing
- Manual verification of simulation parameters
- One-off simulations for design validation

## License

This script is part of the Hayabusa Racing CFD workflow.
