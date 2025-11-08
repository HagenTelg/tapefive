import inspect
from . import tools
from . import tape5parser

class Lblrtm():
    def __init__(self):
        self.configuration = LblrtmConfig()

    @property
    def tape5(self):
        tg = tape5parser.Tape5Generator(self)
        return tg


    # def tape3
    
    def run(self):
        pass

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


