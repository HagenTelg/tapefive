import inspect


class LblrtmConfig():
    

class Lblrtm():
    def __init__(self):
        self.configuration = LblrtmConfig()

    def tape5(self):
        pass

    # def tape3
    
    def run(self):
        pass
    

class Spectral:
    __slots__ = ("_fmin", "_fmax", "_df")

    def __init__(self, fmin=10280.0, fmax=11010.0, df=0.01):
        self.fmin = fmin
        # self.fmax = fmax
        # self.df = df

    @property
    def fmin(self) -> float:
        """Start wavenumber [cm^-1]. Must be > 0 and < fmax."""
        return self._fmin
    @fmin.setter
    def fmin(self, v: float) -> None:
        if v <= 0: raise ValueError("fmin must be > 0")
        self._fmin = v

    # ... fmax/df similar ...

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
