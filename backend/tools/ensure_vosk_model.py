"""Instala de forma atómica el modelo español pequeño de Vosk en el volumen."""
from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import requests

ENABLED = os.getenv("LIAM_LOCAL_STT_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on", "si", "sí"}
ROOT_NAME = "vosk-model-small-es-0.42"
URL = os.getenv("LIAM_VOSK_MODEL_URL", f"https://alphacephei.com/vosk/models/{ROOT_NAME}.zip")
TARGET = Path(os.getenv("LIAM_VOSK_MODEL_PATH") or Path(os.getenv("DATA_DIR", "/data")) / "models" / ROOT_NAME)


def main() -> None:
    if not ENABLED:
        print("[LIAM-STT] Motor local desactivado.")
        return
    marker = TARGET / "conf" / "model.conf"
    if marker.exists():
        print(f"[LIAM-STT] Modelo disponible en {TARGET}.")
        return
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="liam-vosk-") as temporary:
        archive = Path(temporary) / "model.zip"
        print(f"[LIAM-STT] Descargando modelo español en {TARGET.parent}.")
        with requests.get(URL, stream=True, timeout=(15, 180)) as response:
            response.raise_for_status()
            with archive.open("wb") as output:
                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        output.write(chunk)
        if archive.stat().st_size < 20_000_000:
            raise RuntimeError("La descarga del modelo Vosk quedó incompleta.")
        with zipfile.ZipFile(archive) as bundle:
            names = bundle.namelist()
            if not names or any(".." in Path(name).parts or Path(name).is_absolute() for name in names):
                raise RuntimeError("El archivo del modelo contiene rutas no seguras.")
            bundle.extractall(temporary)
        extracted = Path(temporary) / ROOT_NAME
        if not (extracted / "conf" / "model.conf").exists():
            raise RuntimeError("El modelo descargado no tiene la estructura esperada.")
        staging = TARGET.with_name(f".{TARGET.name}.installing")
        if staging.exists():
            shutil.rmtree(staging)
        shutil.copytree(extracted, staging)
        staging.replace(TARGET)
    print("[LIAM-STT] Modelo español instalado correctamente.")


if __name__ == "__main__":
    main()
