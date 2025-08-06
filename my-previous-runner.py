from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile
from PyFoam.Execution.UtilityRunner import UtilityRunner
from PyFoam.Execution.BasicRunner import BasicRunner
import time
import os
import sys
from pathlib import Path

class OpenFOAMParallelRunner:
    def __init__(self, case_dir, n_proc=6, case_id=None):
        self.case_dir = case_dir
        self.n_proc = n_proc
        self.case_id = case_id
        
    def _run_with_log(self, argv, operation):
        """Run OpenFOAM command normally (verbose terminal output)"""
        runner = UtilityRunner(argv=argv, silent=False)
        runner.quiet = False
        runner.start()
        runner.run.join()
        return runner.run.returncode == 0
        
    def run_blockMesh(self):
        return self._run_with_log(["blockMesh", "-case", str(self.case_dir)], "blockMesh")
    
    def run_surfaceFeatureExtract(self, dictPath):
        return self._run_with_log(["surfaceFeatureExtract", "-case", str(self.case_dir), "-dict", str(dictPath)], "surfaceFeatureExtract")
    
    def run_snappyHexMesh(self):
        return self._run_with_log(["snappyHexMesh", "-overwrite", "-case", str(self.case_dir)], "snappyHexMesh")
        runner.start()
        runner.run.join()
        return runner.run.returncode == 0

    def decompose_case(self):
        runner = UtilityRunner(argv=["decomposePar", "-force", "-case", str(self.case_dir)], silent=False)
        runner.quiet = False
        runner.start()
        runner.run.join()
        return runner.run.returncode == 0

    def run_parallel_simpleFoam(self):
        mpirun_cmd = ["mpirun", "--allow-run-as-root", "-np", str(self.n_proc), "simpleFoam", "-case", str(self.case_dir), "-parallel"]
        runner = BasicRunner(argv=mpirun_cmd, silent=False)
        runner.start()
        runner.run.join()
        return runner.run.returncode == 0

    def reconstruct_case(self):
        runner = UtilityRunner(argv=["reconstructPar", "-case", str(self.case_dir)], silent=False)
        runner.quiet = False
        runner.start()
        runner.run.join()
        return runner.run.returncode == 0
    
    def run_all_surfaceFeatureExtract(self):
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
    
    def run_all(self):
        start_time = time.time()
        
        if not self.run_blockMesh():
            return False
        if not self.run_all_surfaceFeatureExtract():
            return False
        if not self.run_snappyHexMesh():
            return False
        if not self.decompose_case():
            return False
        if not self.run_parallel_simpleFoam():
            return False
        if not self.reconstruct_case():
            return False
        
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"Total time elapsed: {elapsed:.2f} s")
    
        return True

if __name__ == "__main__":
    case = "../case"
    runner = OpenFOAMParallelRunner(case_dir=case, n_proc=6)
    runner.run_all()
    print("Parallel run completed successfully")
