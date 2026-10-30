# Third-party software

Random New World is distributed under MPL-2.0; see LICENSE.
The separate interpreter, extension modules and libraries retain their own licences.
The runtime libraries remain separate and replaceable files.

| Component | Licence | Source |
| --- | --- | --- |
| CPython | PSF-2.0 and bundled notices | https://www.python.org/downloads/source/ |
| Qt for Python: PySide6 Essentials, Shiboken6 | LGPL-3.0, with the GPL alternatives identified in each wheel | https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| Qt libraries | LGPL-3.0 and the notices of the shipped Qt modules | https://download.qt.io/official_releases/qt/ |
| NumPy and its bundled libraries | BSD-3-Clause and bundled notices | https://github.com/numpy/numpy |
| Pillow and its bundled libraries | MIT-CMU and bundled notices | https://github.com/python-pillow/Pillow |
| Typer, Rich, Shellingham, markdown-it-py, mdurl, annotated-doc | MIT | Their installed distribution metadata and licence files |
| Pygments | BSD-2-Clause | https://github.com/pygments/pygments |
| The Rust dependencies of rnw._native | The licences named in native/Cargo.lock and the crates' metadata | https://crates.io/ |
| PyInstaller (native packages) | GPL-2.0 with the bootloader exception | https://pyinstaller.org/en/stable/license.html |
| The window: Tauri 2, its plugins and the crates linked into it | The licences listed in licenses/window/crates.txt, with their texts | https://crates.io/ |
| The window's interface: Svelte, Tauri's JavaScript API and plugins | MIT, Apache-2.0 OR MIT, listed in licenses/window/npm.txt | https://www.npmjs.com/ |
| Noto Sans and JetBrains Mono fonts | SIL OFL 1.1 | licenses/window/npm.txt |
| WebView2Loader.dll (Windows window) | BSD-3-Clause-style, Microsoft Corporation | licenses/window/WebView2Loader.txt |

The Windows layouts preserve the runtime wheels' distribution metadata, notices and
licence files. Native packages carry copied runtime licence files under licenses/.
The versions and source URLs of Python packages are listed in licenses/packages.txt.
Qt's corresponding source is available from the Qt links above, for the version named
there; the LGPL text is at https://www.gnu.org/licenses/lgpl-3.0.html.

Release packages contain only the generator and its runtime dependencies.
Complete notices travel with the package; the checked source is published with
the matching product version. Windows binaries are currently unsigned.
No EU5 assets or locally generated world files belong in these packages.
