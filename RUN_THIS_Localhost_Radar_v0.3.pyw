"""Silent launcher. Double click this file on Windows.

.pyw is handled by pythonw.exe, so no console remains open.
Localhost Radar itself is the only long-running application process created by this launcher.
"""
from main import main

if __name__ == "__main__":
    raise SystemExit(main())
