from pathlib import Path
from dataclasses import dataclass
try:
    import tomllib as toml
except ImportError:
    import toml
from typing import Optional
import string

@dataclass(frozen=True)
class ProjectConfig:
    project_name: str
    base: Path
    _build_target: Optional[str] = None
    _test_target: Optional[str] = None
    _ifndef_name: Optional[str] = None
    _namespace_name: Optional[str] = None
    _testsuite_macro: Optional[str] = None

    @property
    def build_dir(self) -> Path:
        return self.base / 'build'

    @property
    def build_target(self) -> str:
        if self._build_target is None:
            return self.project_name
        else:
            return self._build_target

    @property
    def test_target(self) -> str:
        if self._test_target is None:
            return f'{self.project_name}-tests'
        else:
            return self._test_target

    @property
    def ifndef_name(self) -> str:
        if self._ifndef_name is None:
            result = self.project_name.upper()
        else:
            result = self._ifndef_name
        allowed = set(string.ascii_uppercase + '_')
        assert all(c in allowed for c in result)
        return result

    @property
    def namespace_name(self) -> str:
        if self._namespace_name is None:
            result = self.project_name
        else:
            result = self._namespace_name
        allowed = set(string.ascii_uppercase + string.ascii_lowercase + '_')
        assert all(c in set(allowed) for c in result)
        return result

    @property
    def testsuite_macro(self) -> str:
        if self._testsuite_macro is None:
            return f'{self.ifndef_name}_TEST_SUITE'
        else:
            return self._testsuite_macro

def find_config_root(d: Path) -> Optional[Path]:
    d = Path(d).resolve()
    assert d.is_absolute()

    while True:
        config_path = d / '.lockshaw.toml'

        if config_path.is_file():
            return d

        if d == d.parent:
            return None
        else:
            d = d.parent

def _load_config(d: Path) -> Optional[ProjectConfig]:
    config_root = find_config_root(d)
    if config_root is None:
        return None

    with (config_root / '.lockshaw.toml').open('r') as f:
        raw = toml.loads(f.read())
    return ProjectConfig(
        project_name=raw['project_name'],
        base=config_root,
        _build_target=raw.get('build_target'),
        _test_target=raw.get('test_target'),
        _ifndef_name=raw.get('ifndef_name'),
        _namespace_name=raw.get('namespace_name'),
    )

def gen_ifndef_uid(p):
    p = Path(p).absolute()
    relpath = p.relative_to(get_lib_root(p))
    config = _load_config(p)
    return f'_{config.ifndef_name}_' + str(relpath).upper().replace('/', '_').replace('.', '_')

def get_config(p) -> Optional[ProjectConfig]:
    p = Path(p).absolute()
    config = _load_config(p)
    return config

def get_lib_root(p: Path) -> Path:
    config_root = find_config_root(p)
    assert config_root is not None
    return config_root / 'lib'


def with_suffixes(p, suffs):
    name = p.name
    while '.' in name:
        name = name[:name.rfind('.')]
    return p.with_name(name + suffs)

def get_include_path(p: Path):
    p = Path(p).absolute()
    lib_root = get_lib_root(p)
    relpath = p.relative_to(lib_root / 'src')
    include_dir = lib_root / 'include'
    assert include_dir.is_dir()
    src_dir = lib_root / 'src'
    assert src_dir.is_dir()
    public_include = include_dir / with_suffixes(relpath, '.hh')
    private_include = src_dir / with_suffixes(relpath, '.hh')
    if public_include.exists():
        return str(public_include.relative_to(include_dir))
    if private_include.exists():
        return str(private_include.relative_to(src_dir))
    raise ValueError