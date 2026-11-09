# Vendored InsightFace Wheel

`insightface-0.7.3-cp312-cp312-win_amd64.whl` is a locally built wheel for
Windows x64 / CPython 3.12.

- Source: official `insightface-0.7.3.tar.gz` from PyPI (MIT license)
- Built with MinGW-w64 `g++` because InsightFace publishes no cp312 wheel
- The unused `mask_renderer`/3D-visualization imports are removed from the
  package `__init__` files to reduce the packaged bundle size
- The MinGW runtime DLLs (`libgcc_s_seh-1.dll`, `libstdc++-6.dll`,
  `libwinpthread-1.dll`) are bundled beside the extension module
- SHA256: `6D001F0AFF6025E432E8C7E0DF0255F36AAE5D6F9F51497E05082E82353829C2`

## Rebuilding

```powershell
# Python 3.12 environment with setuptools, wheel, Cython, and numpy<2
python -m pip download insightface==0.7.3 --no-deps --no-binary :all: -d vendor_src
tar -xzf vendor_src\insightface-0.7.3.tar.gz -C vendor_src
cd vendor_src\insightface-0.7.3

# Add the runtime DLLs to the wheel and include them as package data
copy C:\mingw64\bin\libgcc_s_seh-1.dll insightface\thirdparty\face3d\mesh\cython\
copy C:\mingw64\bin\libstdc++-6.dll insightface\thirdparty\face3d\mesh\cython\
copy C:\mingw64\bin\libwinpthread-1.dll insightface\thirdparty\face3d\mesh\cython\

# Reduce bundle size by removing imports that Imprint never uses:
#   insightface/__init__.py      -> delete "from . import thirdparty"
#   insightface/app/__init__.py  -> delete "from .mask_renderer import *"

# Add package_data for the DLLs in setup.py before building:
#   package_data={'insightface': ['thirdparty/face3d/mesh/cython/*.dll']},
(Get-Content setup.py -Raw) -replace "include_package_data=True,", "include_package_data=True,`n    package_data={'insightface': ['thirdparty/face3d/mesh/cython/*.dll']}," | Set-Content setup.py -Encoding utf8

python setup.py build_py
python setup.py build_ext --compiler=mingw32
python setup.py bdist_wheel --skip-build --dist-dir ..\..\wheelhouse
```

`requirements.txt` includes `--find-links wheelhouse`, so Windows / Python 3.12
installs use this prebuilt wheel instead of invoking a compiler. Other platforms
fall back to the official source distribution.
