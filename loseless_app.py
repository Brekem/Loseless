"""Punto de entrada del .exe: sin argumentos abre la interfaz web."""

import sys

from loseless.cli import main

if __name__ == "__main__":
    main(sys.argv[1:] or ["--web"])
