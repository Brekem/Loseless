# Loseless

App personal para bajar **solo el audio** de videos y **playlists completas** de YouTube,
en formatos listos para DJ (FLAC, WAV, AIFF, ALAC, MP3 320). Usa [yt-dlp](https://github.com/yt-dlp/yt-dlp) + ffmpeg.

## Windows: Loseless.exe (recomendado)

Baja **Loseless.exe** de https://github.com/Brekem/Loseless/releases/latest y ábrelo con doble clic.
Trae todo incluido (Python, yt-dlp y ffmpeg): no hay que instalar nada. La música se guarda en `Música\Loseless`.
El exe se recompila solo cada lunes con la última versión de yt-dlp; si YouTube deja de funcionar, baja el más nuevo.

## Windows: doble clic con Python

1. Instala Python desde https://www.python.org/downloads/ (marca **"Add python.exe to PATH"**).
2. Baja el ZIP del repo, descomprímelo y haz **doble clic en `Loseless.bat`**.
   - La primera vez instala ffmpeg si hace falta (te pedirá volver a abrirlo) y prepara todo.
   - Cada vez que lo abras actualiza yt-dlp y abre la app en tu navegador.
3. La música queda en la carpeta `downloads` dentro de la carpeta de la app.

## Instalación manual

1. Python 3.10+
2. ffmpeg:
   - macOS: `brew install ffmpeg`
   - Windows: `winget install ffmpeg`
   - Linux: `sudo apt install ffmpeg`
3. Dependencias:
   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Uso

### Interfaz web (la más cómoda)
```bash
python -m loseless --web
```
Se abre `http://127.0.0.1:5055`: pegas URLs (videos o playlists, una por línea), eliges formato y listo.
Tiene cola de descargas y muestra el progreso.

### Línea de comandos
```bash
# Una playlist completa en FLAC
python -m loseless "https://www.youtube.com/playlist?list=XXXX"

# AIFF para Rekordbox/Serato, a 44.1 kHz, en otra carpeta
python -m loseless -f aiff --sample-rate 44100 -o ~/Music/DJ "URL"

# Solo los temas 1 a 10 de una playlist
python -m loseless --items 1-10 "URL_PLAYLIST"

# Muchas URLs desde un archivo (una por línea, # para comentarios)
python -m loseless -i lista.txt
```

| Formato | Qué es |
|---|---|
| `best` | El stream original de YouTube sin recodificar (Opus/M4A). Máxima calidad real, archivo pequeño. |
| `flac` | Sin pérdida comprimido, con tags y portada. **Default.** |
| `wav` | PCM sin comprimir (sin portada). |
| `aiff` | PCM sin comprimir, preferido por Rekordbox/Serato en Mac. |
| `alac` | Apple Lossless (.m4a), con portada. |
| `mp3` | MP3 320 kbps, con portada. |

Otras opciones: `--normalize` (iguala volumen a -14 LUFS), `--no-thumbnail`, `--no-archive`,
`--cookies-from-browser chrome` (para videos con restricción de edad o playlists privadas tuyas).

### Características
- Playlists → se guardan en una subcarpeta con el nombre de la playlist y numeradas (`001 - Artista - Tema.flac`).
- Archivo `.archive.txt` en la carpeta destino: si vuelves a correr la misma playlist, **solo baja los temas nuevos**.
- Videos borrados/privados se saltan sin detener la playlist.
- Metadatos (título, artista) y portada incrustados cuando el formato lo permite.

## ⚠ Importante sobre la calidad "lossless"

YouTube **no guarda audio sin pérdida**: el mejor stream es Opus ~160 kbps (o AAC 256 kbps con Premium).
Convertir a FLAC/WAV/AIFF **no recupera calidad**; solo guarda ese audio en un contenedor sin pérdida
adicional, cómodo para software de DJ y para que no se degrade más si lo editas.
Para sets en club con sistemas grandes, lo ideal es comprar los temas en Bandcamp, Beatport, Traxsource, etc.
en WAV/AIFF originales.

## Aviso legal
Para uso personal. Descargar contenido de YouTube puede ir contra sus Términos de Servicio y los derechos
de autor de cada tema; eres responsable de tener permiso para lo que descargas y de las licencias para
reproducirlo en público.
