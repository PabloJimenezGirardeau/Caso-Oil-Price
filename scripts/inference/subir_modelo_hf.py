"""Sube los modelos finales a Hugging Face (repositorio de modelo).

Sube modelos/final/ (una carpeta por plazo: pesos, escalado y ficha) y la ficha del modelo
(modelos/README.md). No maneja ninguna clave: usa la sesión que se inicia antes con
`hf auth login` (token de tipo «write», de Settings → Access Tokens en Hugging Face).

Uso:
    python scripts/inference/subir_modelo_hf.py --solo-mostrar     # qué se subiría, sin subir nada
    python scripts/inference/subir_modelo_hf.py                    # sube
"""
import argparse

from oil_price.utils import config

REPO = "PabloJimenezGirardeau/brent-rnn-lstm-gru"
ORIGEN = config.RAIZ / "modelos" / "final"
FICHA = config.RAIZ / "modelos" / "README.md"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default=REPO)
    parser.add_argument("--solo-mostrar", action="store_true")
    args = parser.parse_args()

    archivos = sorted(p for p in ORIGEN.rglob("*") if p.is_file())
    print(f"Repositorio: {args.repo}")
    for p in [FICHA, *archivos]:
        destino = "README.md" if p == FICHA else p.relative_to(ORIGEN).as_posix()
        print(f"  {destino:<28} {p.stat().st_size / 1024:6.1f} KB")
    if args.solo_mostrar:
        print("\nSolo el plan: no se ha subido nada.")
        return

    from huggingface_hub import HfApi
    api = HfApi()
    quien = api.whoami()["name"]
    print(f"\nSesión iniciada como {quien}. Subiendo…")
    api.upload_folder(repo_id=args.repo, repo_type="model", folder_path=str(ORIGEN),
                      commit_message="Modelos finales (entrenados hasta el 3/11/2026)")
    api.upload_file(repo_id=args.repo, repo_type="model", path_or_fileobj=str(FICHA), path_in_repo="README.md",
                    commit_message="Ficha del modelo")
    print(f"Hecho: https://huggingface.co/{args.repo}")


if __name__ == "__main__":
    main()
