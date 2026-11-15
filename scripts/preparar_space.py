"""Prepara (y, si se pide, sube) la aplicación como un Space de Hugging Face.

Monta en hf/space/ (carpeta que no se versiona) lo que necesita el Space: la aplicación, las dependencias, la
ficha del Space, el paquete oil_price, la foto de los datos (por si no hay conexión) y las cifras del estudio.
Con --subir, crea el Space (si no existe) y lo sube con la sesión de Hugging Face que ya esté iniciada
(`login()` o la variable HF_TOKEN); este script no maneja ninguna clave.

Uso:
    python scripts/preparar_space.py              # solo monta hf/space/
    python scripts/preparar_space.py --subir      # monta y sube
"""
import argparse
import shutil

from oil_price import config

REPO = "PabloJimenezGirardeau/brent-prevision"
DESTINO = config.RAIZ / "hf" / "space"


def montar():
    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    DESTINO.mkdir(parents=True)
    copias = {config.RAIZ / "app" / "app.py": "app.py", config.RAIZ / "app" / "requirements.txt": "requirements.txt",
              config.RAIZ / "app" / "space_README.md": "README.md",
              config.RAIZ / "data" / "petroleo_dataset.csv": "data/petroleo_dataset.csv",
              config.RAIZ / "data" / "dias_brent.csv": "data/dias_brent.csv",
              config.RAIZ / "web" / "data" / "test.json": "estudio/test.json",
              config.RAIZ / "web" / "data" / "validacion.json": "estudio/validacion.json"}
    for origen in sorted((config.RAIZ / "src" / "oil_price").glob("*.py")):
        copias[origen] = f"src/oil_price/{origen.name}"
    for origen, destino in copias.items():
        (DESTINO / destino).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, DESTINO / destino)
    tamaño = sum(f.stat().st_size for f in DESTINO.rglob("*") if f.is_file()) / 1024
    print(f"Montado en {DESTINO}: {len(copias)} archivos, {tamaño:.0f} KB")
    return len(copias)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--subir", action="store_true")
    args = parser.parse_args()
    montar()
    if not args.subir:
        print("Solo montado: no se ha subido nada.")
        return
    from huggingface_hub import HfApi
    api = HfApi()
    print(f"Sesión iniciada como {api.whoami()['name']}. Subiendo a {args.repo} …")
    api.create_repo(args.repo, repo_type="space", space_sdk="gradio", exist_ok=True)
    api.upload_folder(repo_id=args.repo, repo_type="space", folder_path=str(DESTINO), commit_message="Aplicación")
    print(f"Hecho: https://huggingface.co/spaces/{args.repo}")


if __name__ == "__main__":
    main()
