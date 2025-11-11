import inspect
from . import tools
import pathlib as pl
import subprocess as sp
import xarray as xr
from . import fileio

class Lblrtm():
    def __init__(self, verbose = False):
        self.configuration = LblrtmConfig()
        self._verbose = verbose

    @property
    def tape5(self):
        tg = tape5parser.Tape5Generator(self)
        return tg 

    # # def tape3
    # def create_filesystem(self):
    def _create_filesystem(self):
        if self._verbose:
            print(f"Creating LBLRTM filesystem at {self.configuration.environment.base_dir}")
        # level 0
        self.configuration.environment.base_dir.mkdir(parents=True, exist_ok=True)

        # level 1
        p2fld_run = self.configuration.environment.base_dir.joinpath('run')
        p2fld_run.mkdir(parents=True, exist_ok=True)

        # level 2
        p2fld_run_lblrtm = p2fld_run.joinpath('lblrtm')
        p2fld_run_lblrtm.mkdir(parents=True, exist_ok=True) 
        p2fld_run_lnfl = p2fld_run.joinpath('lnfl')
        p2fld_run_lnfl.mkdir(parents=True, exist_ok=True)

        # level 3.lblrtm
        ## create TAPE5
        p2f_lblrtm_tape5 = p2fld_run_lblrtm.joinpath('TAPE5')

        ##  check/create TAPE3
        self.p2f_lblrtm_tape3_link = p2fld_run_lblrtm.joinpath('TAPE3') # this is the link to the actual file within lblrtm folder
        self.p2f_lblrtm_tape3_orig = p2fld_run_lnfl.joinpath('TAPE3') # this is the actual file within lnfl folder
        
        ## check continuum file exists # TODO make dynamic
        p2f_continuum_orig = pl.Path('/home/hagen/prog/LBLRTM/data/absco-ref_wv-mt-ckd.nc')
        p2f_continuum_link = p2fld_run_lblrtm.joinpath('absco-ref_wv-mt-ckd.nc')
        if not p2f_continuum_link.exists():
            p2f_continuum_link.symlink_to(p2f_continuum_orig)

        assert self.p2f_lblrtm_tape3_orig.exists(), f"TAPE3 file not found at expected location: {self.p2f_lblrtm_tape3_orig}"
        if not self.p2f_lblrtm_tape3_link.exists():
            self.p2f_lblrtm_tape3_link.symlink_to(self.p2f_lblrtm_tape3_orig)
        self._filesystem = dict(
            base_dir = self.configuration.environment.base_dir,
            p2fld_run_lblrtm = p2fld_run_lblrtm,
            p2f_lblrtm_tape5 = p2f_lblrtm_tape5,)
        
    def _execute_lblrtm(self):
        if self._verbose:
            print("Executing LBLRTM") 
        result = sp.run(
            ["lblrtm"],
            cwd=self._filesystem['p2fld_run_lblrtm'],
            check=True,
            capture_output=True,
            text=True,            # str instead of bytes
        )
        print(result.stdout+result.stderr)
        self.tp_result = result
        if result.stderr.strip() == "STOP  LBLRTM EXIT":
            out = 0
        else:
            out = 1
        return out
        
    def _write_tape5(self):
        if self._verbose:
            print("Writing TAPE5 file")
        p2f_lblrtm_tape5 = self._filesystem['p2f_lblrtm_tape5']
        with open(p2f_lblrtm_tape5, 'w') as f:
            f.write(self.tape5.tape5)

    def run(self):
        self._create_filesystem()
        self._write_tape5()
        out = self._execute_lblrtm()
        if self._verbose:
            if out == 0:
                print("LBLRTM run completed successfully")
            else:
                print("LBLRTM run failed, i think")
        result = Results(self._filesystem['p2fld_run_lblrtm'])
        return result
    
class Results():
    def __init__(self, path2result_dir : str | pl.Path):
        self.path2result_dir = pl.Path(path2result_dir)
        self._data = None
        pass
    
    @property
    def data(self) -> xr.Dataset:
        if isinstance(self._data, type(None)):
            p2f_tape12 = pl.Path(self.path2result_dir).joinpath('TAPE12')
            self._data = fileio.read_tape12(p2f_tape12)
        return self._data

class LblrtmConfig():
    # __slots__ = ("_fmin", "_fmax", "_df")

    def __init__(self):
        self.spectral_grid = SpectralGrid()
        self.aerosols = Aerosols()
        self.molecular_spectral_lines = MolecularSpectralLines()
        self.molecular_continuum = MolecularContinuum()
        self.rayleigh = RayleighScattering()
        self.surface = Surface()
        self.atmospheric_layers = AtmosphericLayers()
        self.environment = Environment()

class Environment():
    __slots__ = ('_base_dir',)

    def __init__(self):
        self.base_dir = None
        pass

    @property
    def base_dir(self) -> str:
        """Base directory for LBLRTM temporary files."""
        return self._base_dir
    
    @base_dir.setter
    def base_dir(self, v: str | pl.Path | None = None) -> None:
        if isinstance(v, type(None)):
            v = '~/tmp/tapefive_lblrtm'
        self._base_dir = pl.Path(v).expanduser()

class SpectralGrid():
    __slots__ = ("_fmin", "_fmax", "_df")

    def __init__(self, fmin=10280.0, fmax=11010.0, df=0.01):
        self.fmin = fmin
        self.fmax = fmax
        self.df = df

    @property
    def fmin(self) -> float:
        """Start wavenumber [cm^-1]. Must be > 0 and < fmax."""
        return self._fmin
    
    @fmin.setter
    def fmin(self, v: float) -> None:
        # TODO make sure I take care and mention of the +25 cm-1 buffer in LBLRTM docs
        if v <= 0: raise ValueError("fmin must be > 0")
        self._fmin = v

    @property
    def fmax(self) -> float:
        """End wavenumber [cm^-1]. Must be > fmin."""
        return self._fmax
    
    @fmax.setter
    def fmax(self, v: float) -> None:
        if v <= self.fmin: raise ValueError("fmax must be > fmin")
        self._fmax = v

    @property
    def df(self) -> float:
        """Wavenumber increment [cm^-1]. Must be > 0."""
        return self._df
    
    @df.setter
    def df(self, v: float) -> None:
        # TODO It is not clear to me how this is actually implemented in LBLRTM
        if v <= 0: raise ValueError("df must be > 0")
        self._df = v

    def help(self, name: str | None = None) -> None:
        """Show docs/constraints for one field or all fields."""
        props = {k: v for k, v in type(self).__dict__.items() if isinstance(v, property)}
        if name:
            p = props[name]; print(f"{name}: {inspect.getdoc(p.fget)}  (value={getattr(self,name)!r})")
        else:
            for k, p in props.items():
                print(f"{k:5}  {inspect.getdoc(p.fget)}  (value={getattr(self,k)!r})")

    def __dir__(self):
        # cleaner tab-complete: only your fields + common dunders/helpers
        base = [k for k,v in type(self).__dict__.items() if isinstance(v, property)]
        return sorted(base + ["help", "__class__"])

class Aerosols():
    __slots__ = ()

    def __init__(self):
        pass

class MolecularSpectralLines():
    __slots__ = ('_lineshape', '_lineshape_no')
    _lineshape_options = {'None':0, 'Voigt':1}

    def __init__(self):
        self.lineshape = 'Voigt'
        pass

    @property
    def lineshape(self) -> str:
        """Lineshape model. Options: 'None', 'Voigt'.
        In LBLRTM documentation
        ------------------------
                 IHIRAC   (0,1,2,3,4,9) selects desired version of HIRAC
                     = 0  HIRAC   HIRAC not activated; line-by-line calculation is bypassed
                                                       (skips to selected function)
                     = 1  HIRAC1  (Voigt profile)
                     = 2  HIRACL  (Lorentz profile, not available in LBLRTM)
                     = 3  HIRACD  (Doppler profile, not available in LBLRTM)
                     = 4  NLTE Option (Non Local Thermodynamic Equilibrium)
                               -state populations as a function of altitude required on TAPE4
                     = 9  central line contribution omitted (functions 1-3)
        """
        return self._lineshape
    
    @lineshape.setter
    def lineshape(self, v: str) -> None:
        v = v.capitalize()
        if v not in self._lineshape_options.keys():
            raise ValueError(f"lineshape must be one of {list(self._lineshape_options.keys())}")
        self._lineshape_no = self._lineshape_options[v]
        self._lineshape = v
    

class MolecularContinuum():
    __slots__ = ()

    def __init__(self):
        pass

class RayleighScattering():
    __slots__ = ()

    def __init__(self):
        pass
    
class Surface():
    __slots__ = ()

    def __init__(self):
        pass


class AtmosphericLayers():
    __slots__ = ()

    def __init__(self):
        pass


