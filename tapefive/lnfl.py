from . import tape5parser
import subprocess as sp
import warnings

class Lnfl():
    def __init__(self, lblrtm, verbose = False):
        self.lblrtm_config = lblrtm.configuration
        self._verbose = verbose

    @property
    def tape5(self):
        tg = tape5parser.Tape5GeneratorLnfl(self)
        return tg

    def _create_filesystem(self):
        if self._verbose:
            print(f"Creating lnfl filesystem at {self.lblrtm_config.environment.project_directory}...")
        # level 0
        self.lblrtm_config.environment.project_directory.mkdir(parents=True, exist_ok=True)

        # level 1
        p2fld_run = self.lblrtm_config.environment.project_directory.joinpath(self.lblrtm_config.environment.run_name)
        p2fld_run.mkdir(parents=True, exist_ok=True)

        # level 2 
        p2fld_run_lnfl = p2fld_run.joinpath('lnfl')
        p2fld_run_lnfl.mkdir(parents=True, exist_ok=True)

        ##  check/create TAPE1
        p2f_tape1 = p2fld_run_lnfl.joinpath('TAPE1')
        if not p2f_tape1.exists():
            if self._verbose:
                print(f"TAPE1 at {p2f_tape1} does not exist, create link")
            if not self.lblrtm_config.environment.linefile.exists():
                raise FileNotFoundError(f'No linefile found at {self.lblrtm_config.environment.linefile}. Make sure to set a path to an existing linefile at lblrtm.configuration.environment.linefile')
            else:
                p2f_tape1.symlink_to(self.lblrtm_config.environment.linefile)

        p2f_tape5 = p2fld_run_lnfl.joinpath('TAPE5')
        p2f_tape3 = p2fld_run_lnfl.joinpath('TAPE3')

        return dict(p2fld_run_lnfl = p2fld_run_lnfl,
                    p2f_tape5 = p2f_tape5,
                    p2f_tape3 = p2f_tape3)

    def _execute_lnfl(self, path2fld_run_lnfl):
        if self._verbose:
            print("Executing lnfl...") 
        result = sp.run(
            ["lnfl"],
            cwd=path2fld_run_lnfl,
            check=True,
            capture_output=True,
            text=True,            # str instead of bytes
        )
        print(result.stdout+result.stderr)
        self.tp_result = result
        if result.stderr.strip() == "STOP  LINFIL COMPLETE":
            out = 0
        else:
            out = 1
        return out

    def run(self, force_run: bool = False):
        paths = self._create_filesystem()
        p2f_tape5 = paths['p2f_tape5']
        tape5_content = self.tape5.tape5
        #check if TAPE5 exists and if it did change, if it did change overwirte and run lnfl to get new TAPE3
        if force_run:
            if self._verbose:
                print('lnfl is run by force.')
        elif not paths['p2f_tape3'].exists():
            if self._verbose:
                print(f"TAPE3 at {paths['p2f_tape3']} does not exist, running lnfl.")  
        elif paths['p2f_tape3'].stat().st_size == 0:
            if self._verbose:
                print(f"TAPE3 at {paths['p2f_tape3']} is empty, running lnfl.")
        elif p2f_tape5.exists():
            # read existing TAPE5
            with open(p2f_tape5, 'r') as f:
                existing_tape5 = f.read()
            # compare with current TAPE5    
            if existing_tape5 == tape5_content:
                if self._verbose:
                    print(f"TAPE5 at {p2f_tape5} unchanged, skipping lnfl run.")
                return
            else:
                if self._verbose:
                    print(f"TAPE5 at {p2f_tape5} changed, running lnfl.")
        else:
            if self._verbose:
                print(f"TAPE5 at {p2f_tape5} does not exist, running lnfl.")
        
        # write TAPE5
        with open(p2f_tape5, 'w') as f:
            f.write(tape5_content)
        if self._verbose:
            print(f"Wrote lnfl TAPE5 to {p2f_tape5}")

        # run lnfl
        out = self._execute_lnfl(paths['p2fld_run_lnfl'])
        if out == 1:
            warnings.warn('I am not sure if lnfl ran smoothly?!?')