import inspect
from . import tools
import pathlib as pl
import subprocess as sp
import xarray as xr
from . import fileio
from . import tape5parser
import textwrap


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

    def _remove_old_results(self):
        for f in ['TAPE10','TAPE11','TAPE12', 'TAPE13','TAPE27']:
            p2f = self._filesystem['p2fld_run_lblrtm'].joinpath(f)
            if p2f.exists():
                if self._verbose:
                    print(f"Removing old result file {p2f}")
                p2f.unlink()

    def run(self):
        self._create_filesystem()
        self._remove_old_results()
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
        self.data  # this is necessary to trigger data loading, otherwise it might be overwritten by a later run
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
        # self.molecular_continuum = MolecularContinuum()
        self.rayleigh = RayleighScattering()
        self.surface = Surface()
        self.atmospheric_layers = AtmosphericLayers()
        self.environment = Environment()
    
    def __str__(self) -> str:
        txt = 'doit'
        return txt

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
    __slots__ = ("_fmin", "_fmax", "_layering_control",
                 "_df",
                 )
    _layering_control_options = {'adaptive', 'exact'}

    def __str__(self) -> str:
        txt = f"""spectral grid configuration
---------------------------
minimum frequency, fmin: {self.fmin:0.4f} cm^-1 ({tools.nm_to_inv_cm(self.fmin):0.4f} nm)
maximum frequency, fmax: {self.fmax:0.4f} cm^-1 ({tools.nm_to_inv_cm(self.fmax):0.4f} nm)"""
        return txt
    
    def __repr__(self) -> str:
        return self.__str__()

    def __init__(self, fmin=10280.0, fmax=11010.0, df=4, layering_control='adaptive'):
        self.fmin = fmin
        self.fmax = fmax
        self.layering_control = layering_control
        self.df = df

    @property
    def layering_control(self) -> str:
        """Spectral grid layering control. Options: 
        adaptive: (default, also in LBLRTM) LBLRTM automatically adjusts the layer thickness based on the spectral grid resolution (eq. to IOD = 0). This will cause dt to set SAMPLE in RECORD 1.3
        exact: (recommended, but not default) uses exact calculated dv for each layer and interpolates to the spacing set by DVOUT. dt will set DVOUT in RECORD 1.3.
        LBLRTM has more options in for IOD in RECORD 1.2, but these are not implemented here.
        """
        return self._layering_control

    @layering_control.setter
    def layering_control(self, v: str) -> None:
        v = v.lower()
        if v not in self._layering_control_options:
            raise ValueError(f"layering_control must be one of {self._layering_control_options}")
        self._layering_control = v    

    @property
    def fmin(self) -> float:
        """Start wavenumber [cm^-1]. Must be > 0 and < fmax. Note, when the Tape5 is written,
        25 cm^-1 are subtracted as a buffer to this value in accordance with LBLRTM recommondations"""
        return self._fmin
    
    @fmin.setter
    def fmin(self, v: float) -> None:
        # TODO make sure I take care and mention of the +25 cm-1 buffer in LBLRTM docs
        if v <= 0: raise ValueError("fmin must be > 0")
        self._fmin = v

    @property
    def fmax(self) -> float:
        """End wavenumber [cm^-1]. Must be > fmin. Note, when the Tape5 is written,
        25 cm^-1 are added as a buffer to this value in accordance with LBLRTM recommondations."""
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
        # assert(False), 'not implemented yet'
        # TODO It is not clear to me how this is actually implemented in LBLRTM
        # if v <= 0: raise ValueError("df must be > 0")
        self._df = v

    def help(self, name: str | None = None) -> None:
        """Show docs/constraints for one field or all fields."""
        props = {k: v for k, v in type(self).__dict__.items() if isinstance(v, property)}
        if name:
            p = props[name]; print(f"{name}: {inspect.getdoc(p.fget)}  (value={getattr(self,name)!r})")
        else:
            for k, p in props.items():
                print(f"{k:5}")
                print(textwrap.indent(f"{inspect.getdoc(p.fget)}  (value={getattr(self,k)!r})", '    '))

    def __dir__(self):
        # cleaner tab-complete: only your fields + common dunders/helpers
        base = [k for k,v in type(self).__dict__.items() if isinstance(v, property)]
        return sorted(base + ["help", "__class__"])

class Aerosols():
    __slots__ = ("_enabled",)

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        pass
    
    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self):
        txt = f"""Aerosols
-----------------
enabled: {self.enabled}"""
        return txt

    @property
    def enabled(self) -> bool:
        """Enable/disable Aerosol effects on radiation."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, v: bool) -> None:
        self._enabled = v

class MolecularSpectralLines():
    __slots__ = ('_lineshape', '_lineshape_no', 'molecules',)
    _lineshape_options = {'None':0, 'Voigt':1}

    def __init__(self):
        self.lineshape = 'Voigt'
        self.molecules = Molecules()
        pass
    
    def __str__(self) -> str:
        txt = f"""Molecular spectral lines configuration
-------------------------------------------
lineshape: {self.lineshape} (code {self._lineshape_no})

{self.molecules}
"""
        return txt

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
    
    def __repr__(self) -> str:
        return self.__str__()
    
    @lineshape.setter
    def lineshape(self, v: str) -> None:
        v = v.capitalize()
        if v not in self._lineshape_options.keys():
            raise ValueError(f"lineshape must be one of {list(self._lineshape_options.keys())}")
        self._lineshape_no = self._lineshape_options[v]
        self._lineshape = v


class RayleighScattering():
    __slots__ = ("_enabled",)

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        pass
    
    def __repr__(self) -> str:
        return self.__str__()

    def __str__(self):
        txt = f"""Rayleigh scattering
---------------------------
enabled: {self.enabled}"""
        return txt

    @property
    def enabled(self) -> bool:
        """Enable/disable Rayleigh scattering calculations."""
        return self._enabled
    
    @enabled.setter
    def enabled(self, v: bool) -> None:
        self._enabled = v

    
class Surface():
    __slots__ = ()

    def __init__(self):
        pass


class AtmosphericLayers():
    __slots__ = ()

    def __init__(self):
        pass

from dataclasses import dataclass, field

# all molecules available in LBLRTM
MOLECULE_NAMES = ('H2O', 'CO2', 'O3', 'N2O', 'CO', 'CH4', 'O2', 'NO', 'SO2', 'NO2', 'NH3', 'HNO3', 'OH', 'HF', 'HCL', 'HBR', 'HI', 'CLO', 'OCS', 'H2CO', 'HOCL', 'N2', 'HCN', 'CH3CL', 'H2O2', 'C2H2', 'C2H6', 'PH3', 'COF2', 'SF6', 'H2S', 'HCOOH', 'HO2', 'O', 'NO+', 'HOBR', 'C2H4', 'CH3OH')

@dataclass(slots=True)
class Molecule:
    name: str
    _enable: bool = field(default=False, init=False, repr=False)
    _enable_continuum: bool = field(default=True, init=False, repr=False)
    _scale: float = field(default=1.0, init=False, repr=False)
    _scale_unit: str = field(default="direct", init=False, repr=False)
    _scale_unit_options = {'direct', 'column', 'column_dobson', 'column_volmix'} 

    @property
    def enable(self) -> bool: return self._enable

    @enable.setter
    def enable(self, v: bool) -> None: self._enable = bool(v)

    @property
    def enable_continuum(self) -> bool: return self._enable_continuum

    @enable_continuum.setter
    def enable_continuum(self, v: bool) -> None: self._enable_continuum = bool(v)

    @property
    def scale(self) -> float: return self._scale

    @scale.setter
    def scale(self, v: float) -> None: self._scale = float(v)

    @property
    def scale_unit(self) -> str: 
        """Scale unit. Options: 
        'direct': scaling factor used directly to scale profile
        'column': column amount to which the profile is to be scaled (molec/cm^2)
        'column_dobson': amount in Dobson units to which the profile is to be scaled
        'column_volmix: volume mixing ratio (ppv) wrt dry air for the total column to which the profile will be scaled
        'pwv": (H20 only) value of Precipitable Water Vapor (cm) to which the profile will be scaled (water vapor only). USE WITH CAUTION! This is NOT along the vertical column, but the path!"""
        return self._scale_unit

    @scale_unit.setter
    def scale_unit(self, v: str) -> None:
        v = v.lower()
        if v not in self._scale_unit_options:
            raise ValueError(f"scale_unit must be one of {self._scale_unit_options}")
        self._scale_unit = v

    def help(self, name: str | None = None) -> None:
        props = dict(inspect.getmembers(type(self), lambda o: isinstance(o, property)))
        def show(k: str) -> None:
            p = props[k]
            doc = inspect.getdoc(p) or "(no docs)"
            print(f"{k}")
            print(textwrap.indent(f"{doc}  (value={getattr(self, k)!r})", "    "))
        if name:
            if name not in props: raise AttributeError(f"No property named {name!r}")
            show(name)
        else:
            for k in props:
                show(k)

    def __str__(self) -> str:
        cls = type(self).__name__
        props = dict(inspect.getmembers(type(self), lambda o: isinstance(o, property)))
        parts = [f"{k}={getattr(self, k)!r}" for k in sorted(props)]
        return f"{cls}({', '.join(parts)})"

    def __repr__(self):
        return self.__str__()

class Molecules:
    # __slots__ = ("_by_name",)

    def __init__(self, names=MOLECULE_NAMES):
        self._by_name = {}
        for name in names:
            cls = type(name, (Molecule,), {})  # subclass per molecule
            # cls = type(name, (Molecule,), {"__slots__": ()})  # subclass per molecule
            obj = cls(name=name)
            self._by_name[name] = obj
            if name == 'H2O':
                obj._scale_unit_options = obj._scale_unit_options.union({'pwv'})
            setattr(self, name, obj)  # e.g., molecules.H2O

    def __getitem__(self, key: str) -> Molecule: return self._by_name[key]
    def __iter__(self): return iter(self._by_name.values())
    def keys(self): return self._by_name.keys()

    def __str__(self) -> str:
        txt = "Molecules:\n"
        for name, mol in self._by_name.items():
            if mol.enable:
                txt += '\t' + mol.__str__() + "\n"
        txt += "\tOther molecules are disabled\n"
        return txt

    def __repr__(self) -> str:
        return self.__str__()