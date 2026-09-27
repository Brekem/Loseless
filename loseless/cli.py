"""Interfaz de línea de comandos."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import FORMATS, DownloadOptions, download


def _progress(d: dict) -> None:
    status = d.get("status")
    info = d.get("info_dict") or {}
    name = info.get("title") or Path(d.get("filename", "")).name
    if status == "downloading":
        pct = d.get("_percent_str", "").strip()
        speed = d.get("_speed_str", "").strip()
        print(f"\r  ↓ {name[:60]:<60} {pct:>7} {speed:>12}", end="", flush=True)
    elif status == "finished" and "postprocessor" not in d:
        print(f"\r  ✓ descargado: {name[:60]:<60}{' ' * 20}")
    elif status == "started" and d.get("postprocessor") == "ExtractAudio":
        print(f"  ⚙ convirtiendo: {name}")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        prog="loseless",
        description="Descarga solo el audio de videos/playlists de YouTube en FLAC, WAV, AIFF, ALAC o MP3.",
    )
    p.add_argument("urls", nargs="*", help="URLs de videos o playlists")
    p.add_argument("-f", "--format", default="flac", choices=list(FORMATS), help="formato de salida (default: flac)")
    p.add_argument("-o", "--output", default="downloads", help="carpeta de destino (default: ./downloads)")
    p.add_argument("-i", "--input-file", help="archivo .txt con una URL por línea")
    p.add_argument("--sample-rate", type=int, choices=[44100, 48000], help="forzar frecuencia de muestreo")
    p.add_argument("--items", help="solo ciertos items de la playlist, p.ej. '1-10,15'")
    p.add_argument("--normalize", action="store_true", help="normalizar volumen (EBU R128, -14 LUFS)")
    p.add_argument("--no-thumbnail", action="store_true", help="no incrustar portada")
    p.add_argument("--no-archive", action="store_true", help="volver a bajar aunque ya exista")
    p.add_argument("--cookies-from-browser", metavar="BROWSER", help="usar cookies de chrome/firefox/edge/brave")
    p.add_argument("--web", action="store_true", help="abrir la interfaz web local")
    p.add_argument("--port", type=int, default=5055)
    args = p.parse_args(argv)

    if args.web:
        from .web import run

        run(port=args.port)
        return

    urls = list(args.urls)
    if args.input_file:
        lines = Path(args.input_file).read_text(encoding="utf-8").splitlines()
        urls += [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    if not urls:
        p.error("pasa al menos una URL, un --input-file o usa --web")

    opts = DownloadOptions(
        urls=urls,
        output_dir=Path(args.output),
        audio_format=args.format,
        sample_rate=args.sample_rate,
        embed_thumbnail=not args.no_thumbnail,
        use_archive=not args.no_archive,
        playlist_items=args.items,
        normalize=args.normalize,
        cookies_from_browser=args.cookies_from_browser,
    )
    print(f"→ {len(urls)} URL(s) · formato {args.format} · destino {opts.output_dir.resolve()}")
    try:
        code = download(opts, _progress)
    except (RuntimeError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)
    print("Listo." if code == 0 else "Terminado con algunos errores (videos privados/borrados se saltan).")
    sys.exit(code)
