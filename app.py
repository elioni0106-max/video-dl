import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from starlette.background import BackgroundTask
import yt_dlp

app = FastAPI(title="Video Downloader")

PAGE = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Скачать видео</title>
<style>
 body{font-family:system-ui,sans-serif;max-width:560px;margin:10vh auto;padding:0 16px}
 input{width:100%;padding:12px;font-size:16px;box-sizing:border-box}
 select,button{margin-top:10px;padding:12px;font-size:16px}
 button{cursor:pointer}
 #s{margin-top:12px;color:#666}
</style></head><body>
<h2>Скачать видео по ссылке</h2>
<form method="post" action="/download" onsubmit="document.getElementById('s').textContent='Качаю… подождите'">
 <input name="url" type="url" placeholder="https://..." required autofocus>
 <select name="quality">
  <option value="best">Лучшее качество</option>
  <option value="720">До 720p</option>
  <option value="480">До 480p</option>
  <option value="audio">Только аудио</option>
 </select>
 <button type="submit">Скачать</button>
</form>
<div id="s"></div>
</body></html>"""

FORMATS = {
    "best": "bv*+ba/b",
    "720": "bv*[height<=720]+ba/b[height<=720]/b",
    "480": "bv*[height<=480]+ba/b[height<=480]/b",
    "audio": "ba/b",
}


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


@app.post("/download")
def download(url: str = Form(...), quality: str = Form("best")):
    if not url.startswith(("http://", "https://")):
        raise HTTPException(400, "Нужна ссылка http(s)")

    tmp = tempfile.mkdtemp(prefix="vdl_")
    opts = {
        "format": FORMATS.get(quality, FORMATS["best"]),
        "outtmpl": str(Path(tmp) / "%(title).80s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "max_filesize": 2 * 1024**3,  # 2 ГБ
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:
        shutil.rmtree(tmp, ignore_errors=True)
        raise HTTPException(400, f"Не удалось скачать: {e}")

    files = list(Path(tmp).iterdir())
    if not files:
        shutil.rmtree(tmp, ignore_errors=True)
        raise HTTPException(500, "Файл не найден после загрузки")

    f = max(files, key=lambda p: p.stat().st_size)
    return FileResponse(
        f,
        filename=f.name,
        media_type="application/octet-stream",
        background=BackgroundTask(shutil.rmtree, tmp, ignore_errors=True),
    )
