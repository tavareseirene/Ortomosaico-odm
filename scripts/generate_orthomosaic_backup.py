import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime   


# ============================================================
# CONFIGURAÇÕES
# ============================================================

# Pasta onde estão as imagens originais do drone DJI
INPUT_IMAGES_DIR = Path("/home/savefarm/Documents/Estudo Crop/ortomosaico/ortomosaico-80mm-full")

# Pasta onde o projeto ODM será criado
PROJECTS_ROOT = Path("/home/savefarm/HD/ortomosaico/odm_projects")

# Nome do projeto
PROJECT_NAME = "ortomosaico_dji_air3s"

# Pasta final onde o ortomosaico será copiado
FINAL_OUTPUT_DIR = Path("/home/savefarm/Documents/Estudo Crop/ortomosaico/ortomosaico-80mm-full")

# Procurar imagens também em subpastas?
RECURSIVE = False

# Extensões aceitas
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".JPG", ".JPEG",
    ".tif", ".tiff", ".TIF", ".TIFF",
    ".dng", ".DNG"
}

# Imagem Docker do OpenDroneMap
ODM_DOCKER_IMAGE = "opendronemap/odm"

# Resolução do ortomosaico em cm/pixel.
# Quanto menor, maior resolução e mais pesado.
# Default ODM costuma ser 5 cm/px.
ORTHOPHOTO_RESOLUTION_CM = 1.0

# Qualidade dos pontos/características.
# Opções comuns: lowest, low, medium, high, ultra
FEATURE_QUALITY = "high"
POINT_CLOUD_QUALITY = "high"

# Para ortomosaico agrícola, normalmente não precisa do modelo 3D texturizado final.
SKIP_3D_MODEL = True

# Mais rápido, mas pode perder qualidade porque pula reconstrução densa.
# Para resultado bom, deixe False.
FAST_ORTHOPHOTO = False

# Cria Cloud Optimized GeoTIFF e overviews, útil para abrir mais fácil em QGIS/GIS.
CREATE_COG = True
BUILD_OVERVIEWS = True

# Tenta cortar melhor as bordas do ortomosaico.
AUTO_BOUNDARY = True

# Se quiser gerar DSM/DTM também, coloque True.
CREATE_DSM = False
CREATE_DTM = False

# Limite de concorrência. None deixa o ODM decidir.
# Em máquina com muita RAM/CPU pode usar 8, 12, 16...
MAX_CONCURRENCY = 64

# Usar hardlink quando possível para não duplicar 33 MB por imagem.
# Se não der, copia normalmente.
USE_HARDLINK_OR_COPY = True

# Limpar pasta images do projeto antes de preparar?
CLEAN_PROJECT_IMAGES = True

# Limpar processamento antigo do ODM antes de rodar de novo?
# Se True, apaga saídas antigas do projeto, mantendo images.
CLEAN_OLD_PROCESSING = True


# ============================================================
# FUNÇÕES
# ============================================================

def find_images(input_dir: Path, recursive: bool = False):
    if not input_dir.exists():
        raise FileNotFoundError(f"Pasta de entrada não existe: {input_dir}")

    if recursive:
        files = [p for p in input_dir.rglob("*") if p.suffix in IMAGE_EXTENSIONS]
    else:
        files = [p for p in input_dir.iterdir() if p.is_file() and p.suffix in IMAGE_EXTENSIONS]

    files = sorted(files)

    if not files:
        raise RuntimeError(f"Nenhuma imagem encontrada em: {input_dir}")

    return files


def safe_remove_dir(path: Path):
    if path.exists() and path.is_dir():
        shutil.rmtree(path)


def prepare_odm_project(images):
    project_dir = PROJECTS_ROOT / PROJECT_NAME
    images_dir = project_dir / "images"

    PROJECTS_ROOT.mkdir(parents=True, exist_ok=True)
    project_dir.mkdir(parents=True, exist_ok=True)

    if CLEAN_PROJECT_IMAGES:
        safe_remove_dir(images_dir)

    images_dir.mkdir(parents=True, exist_ok=True)

    if CLEAN_OLD_PROCESSING:
        for item in project_dir.iterdir():
            if item.name == "images":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

    copied = 0

    for src in images:
        dst = images_dir / src.name

        if dst.exists():
            continue

        if USE_HARDLINK_OR_COPY:
            try:
                os.link(src, dst)
            except OSError:
                shutil.copy2(src, dst)
        else:
            shutil.copy2(src, dst)

        copied += 1

    return project_dir, images_dir, copied


def check_docker():
    if shutil.which("docker") is None:
        raise RuntimeError(
            "Docker não encontrado. Instale o Docker antes de rodar o ODM."
        )

    subprocess.run(
        ["docker", "--version"],
        check=True
    )


def pull_odm_image():
    print(f"\n[INFO] Baixando/atualizando imagem Docker: {ODM_DOCKER_IMAGE}")
    subprocess.run(
        ["docker", "pull", ODM_DOCKER_IMAGE],
        check=True
    )


def build_odm_command():
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{PROJECTS_ROOT.resolve()}:/datasets",
        ODM_DOCKER_IMAGE,
        "--project-path", "/datasets",
        PROJECT_NAME,
        "--orthophoto-resolution", str(ORTHOPHOTO_RESOLUTION_CM),
        "--feature-quality", FEATURE_QUALITY,
        "--pc-quality", POINT_CLOUD_QUALITY,
        "--orthophoto-compression", "DEFLATE",
    ]

    if SKIP_3D_MODEL:
        cmd.append("--skip-3dmodel")

    if FAST_ORTHOPHOTO:
        cmd.append("--fast-orthophoto")

    if CREATE_COG:
        cmd.append("--cog")

    if BUILD_OVERVIEWS:
        cmd.append("--build-overviews")

    if AUTO_BOUNDARY:
        cmd.append("--auto-boundary")

    if CREATE_DSM:
        cmd.append("--dsm")

    if CREATE_DTM:
        cmd.append("--dtm")

    if MAX_CONCURRENCY is not None:
        cmd.extend(["--max-concurrency", str(MAX_CONCURRENCY)])

    return cmd


def run_odm():
    cmd = build_odm_command()

    print("\n[INFO] Comando ODM:")
    print(" ".join(cmd))
    print("\n[INFO] Iniciando processamento...\n")

    subprocess.run(cmd, check=True)


def find_orthomosaic(project_dir: Path):
    ortho_dir = project_dir / "odm_orthophoto"

    candidates = [
        ortho_dir / "odm_orthophoto.tif",
        ortho_dir / "odm_orthphoto.tif",
        ortho_dir / "odm_orthophoto.original.tif",
        ortho_dir / "odm_orthphoto.original.tif",
    ]

    for c in candidates:
        if c.exists():
            return c

    tif_files = sorted(ortho_dir.glob("*.tif")) if ortho_dir.exists() else []

    if tif_files:
        return tif_files[0]

    raise FileNotFoundError(
        f"Não encontrei o ortomosaico final em: {ortho_dir}"
    )


def copy_final_outputs(project_dir: Path):
    FINAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ortho_tif = find_orthomosaic(project_dir)

    final_tif = FINAL_OUTPUT_DIR / f"{PROJECT_NAME}_orthomosaic.tif"
    shutil.copy2(ortho_tif, final_tif)

    print("\n[OK] Ortomosaico final salvo em:")
    print(final_tif)

    # Copia PNG/KMZ se existirem
    ortho_dir = project_dir / "odm_orthophoto"

    for ext in ["*.png", "*.kmz", "*.tfw"]:
        for file in ortho_dir.glob(ext):
            dst = FINAL_OUTPUT_DIR / file.name
            shutil.copy2(file, dst)
            print(f"[OK] Arquivo extra copiado: {dst}")

    return final_tif


def print_exif_check_hint(images):
    first = images[0]
    print("\n[INFO] Primeira imagem encontrada:")
    print(first)

    if shutil.which("exiftool") is not None:
        print("\n[INFO] Checando metadados básicos com exiftool:")
        cmd = [
            "exiftool",
            "-GPSLatitude",
            "-GPSLongitude",
            "-GPSAltitude",
            "-RelativeAltitude",
            "-GimbalYawDegree",
            "-GimbalPitchDegree",
            "-FlightYawDegree",
            "-FocalLength",
            "-ImageWidth",
            "-ImageHeight",
            "-n",
            str(first)
        ]
        subprocess.run(cmd, check=False)
    else:
        print(
            "[AVISO] exiftool não encontrado. O ODM ainda pode ler os metadados, "
            "mas não vou imprimir o resumo EXIF aqui."
        )


# ============================================================
# MAIN
# ============================================================

def main():
    start = datetime.now()

    print("============================================================")
    print("GERADOR DE ORTOMOSAICO DJI COM OPENDRONEMAP")
    print("============================================================")

    images = find_images(INPUT_IMAGES_DIR, recursive=RECURSIVE)

    print(f"\n[INFO] Imagens encontradas: {len(images)}")
    print_exif_check_hint(images)

    check_docker()
    pull_odm_image()

    project_dir, images_dir, copied = prepare_odm_project(images)

    print("\n[INFO] Projeto ODM preparado:")
    print(f"Projeto: {project_dir}")
    print(f"Imagens: {images_dir}")
    print(f"Novas imagens adicionadas: {copied}")

    run_odm()

    final_tif = copy_final_outputs(project_dir)

    end = datetime.now()
    elapsed = end - start

    print("\n============================================================")
    print("[FINALIZADO]")
    print(f"Tempo total: {elapsed}")
    print(f"Ortomosaico: {final_tif}")
    print("============================================================")


if __name__ == "__main__":
    main()