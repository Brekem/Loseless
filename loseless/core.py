"""Lógica de descarga sobre yt-dlp + ffmpeg."""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import yt_dlp

# Formatos de salida. "best" guarda el stream original (opus/m4a) sin recodificar:
# es la máxima calidad real que ofrece YouTube. FLAC/WAV/AIFF son contenedores sin
# pérdida *a partir de* ese stream (no añaden calidad, pero son cómodos para
# software de DJ como Rekordbox, Serato o Traktor).
FORMATS = {
    "best": {"codec": "best", "ext": None, "desc": "Stream original sin recodificar (opus/m4a)"},
    "flac": {"codec": "flac", "ext": "flac", "desc": "FLAC sin pérdida (comprimido)"},
    "wav": {"codec": "wav", "ext": "wav", "desc": "WAV PCM sin comprimir"},
    "aiff": {"codec": "wav", "ext": "aiff", "desc": "AIFF (ideal para Rekordbox/Serato, con tags)"},
    "alac": {"codec": "alac", "ext": "m4a", "desc": "Apple Lossless"},
    "mp3": {"codec": "mp3", "ext": "mp3", "desc": "MP3 320 kbps"},
}

THUMBNAIL_FORMATS = {"best", "flac", "alac", "mp3"}

ProgressCallback = Callable[[dict], None]


@dataclass
class DownloadOptions:
    urls: list[str]
    output_dir: Path = Path("downloads")
    audio_format: str = "flac"
    sample_rate: int | None = None  # p.ej. 44100 o 48000; None = mantener
    embed_thumbnail: bool = True
    embed_metadata: bool = True
    use_archive: bool = True  # no volver a bajar lo que ya tienes
    playlist_items: str | None = None  # p.ej. "1-10,15"
    normalize: bool = False  # loudnorm EBU R128 (recodifica)
    cookies_from_browser: str | None = None  # "chrome", "firefox"...
    extra_postprocessor_args: list[str] = field(default_factory=list)


# Los "Mix" de YouTube (listas que empiezan con RD) son infinitas: se generan solas.
MIX_MAX_ITEMS = 50


def normalize_url(url: str) -> str:
    """Un link de un video siempre baja SOLO ese video.

    Al abrir un tema desde un Mix o una playlist, YouTube agrega `&list=...` al link
    del video (p.ej. watch?v=abc&list=RDabc&start_radio=1). Quitamos esos parámetros
    para no bajar la lista entera (o infinita, en el caso de los Mix).
    Para bajar una playlist completa, usa el link /playlist?list=...
    """
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    if "youtube.com" not in host and "youtu.be" not in host:
        return url.strip()
    query = parse_qs(parsed.query)
    is_video = "youtu.be" in host or parsed.path.startswith(("/watch", "/shorts/", "/live/"))
    if is_video and "list" in query:
        for key in ("list", "index", "start_radio", "pp"):
            query.pop(key, None)
        parsed = parsed._replace(query=urlencode(query, doseq=True))
    return urlunparse(parsed)


def is_mix(url: str) -> bool:
    lists = parse_qs(urlparse(url).query).get("list", [])
    return any(x.startswith("RD") for x in lists)


def _has_mutagen() -> bool:
    try:
        import mutagen  # noqa: F401
    except ImportError:
        return False
    return True


def bundled_ffmpeg_dir() -> Path | None:
    """Carpeta con ffmpeg incluido dentro del .exe (PyInstaller), si existe."""
    base = getattr(sys, "_MEIPASS", None)
    if base and (Path(base) / "ffmpeg.exe").exists():
        return Path(base)
    return None


def check_ffmpeg() -> bool:
    if bundled_ffmpeg_dir():
        return True
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def default_output_dir() -> Path:
    """En el .exe: Música\\Loseless. Desde el código: ./downloads."""
    if getattr(sys, "frozen", False):
        return Path.home() / "Music" / "Loseless"
    return Path("downloads")


def build_ydl_opts(opts: DownloadOptions, hooks: list[ProgressCallback] | None = None) -> dict:
    if opts.audio_format not in FORMATS:
        raise ValueError(f"Formato no soportado: {opts.audio_format}. Usa uno de {list(FORMATS)}")
    fmt = FORMATS[opts.audio_format]
    out = Path(opts.output_dir).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    postprocessors: list[dict] = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": fmt["codec"],
            "preferredquality": "0" if opts.audio_format != "mp3" else "320",
        }
    ]
    # AIFF: yt-dlp no lo trae como codec nativo; extraemos a WAV y convertimos
    # (ffmpeg usa PCM big-endian para .aiff).
    if opts.audio_format == "aiff":
        postprocessors = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "wav"},
            {"key": "FFmpegVideoConvertor", "preferedformat": "aiff"},
        ]

    if opts.audio_format == "best" and (opts.sample_rate or opts.normalize):
        raise ValueError("--sample-rate/--normalize requieren recodificar: usa flac, wav, aiff, alac o mp3")

    pp_args: list[str] = list(opts.extra_postprocessor_args)
    if opts.sample_rate:
        pp_args += ["-ar", str(opts.sample_rate)]
    if opts.normalize:
        pp_args += ["-af", "loudnorm=I=-14:TP=-1:LRA=11"]

    if opts.embed_metadata:
        postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
    # WAV/AIFF no admiten portada embebida vía yt-dlp.
    thumb = opts.embed_thumbnail and opts.audio_format in THUMBNAIL_FORMATS and _has_mutagen()
    if thumb:
        # YouTube da portadas en .webp, que Rekordbox/Serato no muestran: pasar a JPG.
        postprocessors.insert(0, {"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"})
        postprocessors.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})

    ydl_opts: dict = {
        # Mejor stream de solo audio disponible (normalmente Opus ~160k o AAC 128/256k).
        "format": "bestaudio/best",
        "outtmpl": {
            # Videos sueltos -> carpeta raíz; playlists -> subcarpeta con su nombre.
            "default": str(out / "%(playlist_title&{}/|)s%(playlist_index&{:03d} - |)s%(artist,uploader)s - %(track,title)s.%(ext)s"),
            "thumbnail": str(out / "%(playlist_title&{}/|)s%(playlist_index&{:03d} - |)s%(artist,uploader)s - %(track,title)s.%(ext)s"),
        },
        "restrictfilenames": False,
        "windowsfilenames": True,
        "writethumbnail": thumb,
        "postprocessors": postprocessors,
        "postprocessor_args": {"extractaudio": pp_args} if pp_args else {},
        "ignoreerrors": True,  # un video caído no detiene la playlist
        # Si un link es ambiguo (video + lista), bajar solo el video.
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 10,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
        "progress_hooks": hooks or [],
        "postprocessor_hooks": hooks or [],
    }
    if opts.use_archive:
        ydl_opts["download_archive"] = str(out / ".archive.txt")
    if opts.playlist_items:
        ydl_opts["playlist_items"] = opts.playlist_items
    if ffmpeg_dir := bundled_ffmpeg_dir():
        ydl_opts["ffmpeg_location"] = str(ffmpeg_dir)
    if opts.cookies_from_browser:
        ydl_opts["cookiesfrombrowser"] = (opts.cookies_from_browser,)
    return ydl_opts


def download(opts: DownloadOptions, on_progress: ProgressCallback | None = None) -> int:
    """Descarga todas las URLs. Devuelve el código de retorno de yt-dlp (0 = ok)."""
    if not check_ffmpeg():
        raise RuntimeError(
            "No se encontró ffmpeg/ffprobe en el PATH. Instálalo: "
            "macOS `brew install ffmpeg`, Windows `winget install ffmpeg`, Linux `apt install ffmpeg`."
        )
    hooks = [on_progress] if on_progress else []
    ydl_opts = build_ydl_opts(opts, hooks)
    code = 0
    for url in (normalize_url(u) for u in opts.urls if u.strip()):
        per_url = dict(ydl_opts)
        if is_mix(url) and not opts.playlist_items:
            per_url["playlistend"] = MIX_MAX_ITEMS
        with yt_dlp.YoutubeDL(per_url) as ydl:
            code = ydl.download([url]) or code
    return code
