import os
import shutil
import random
from pathlib import Path

# ============================================================
# CONFIGURACION
# ============================================================

DATASET_ORIGINAL = Path(
    "/home/cristian/Desktop/dataset_astra_blanca_200"
)

DATASET_SPLIT = Path(
    "/home/cristian/Desktop/dataset_astra_blanca_200_split"
)

IMAGES_ORIG = DATASET_ORIGINAL / "images"
LABELS_ORIG = DATASET_ORIGINAL / "labels"

TRAIN_IMAGES = DATASET_SPLIT / "images" / "train"
VAL_IMAGES = DATASET_SPLIT / "images" / "val"

TRAIN_LABELS = DATASET_SPLIT / "labels" / "train"
VAL_LABELS = DATASET_SPLIT / "labels" / "val"

SEED = 20261009

# 50 imagenes por bloque
IMAGENES_POR_BLOQUE = 50

# De cada bloque:
TRAIN_POR_BLOQUE = 40
VAL_POR_BLOQUE = 10


# ============================================================
# CREAR CARPETAS
# ============================================================

for folder in [
    TRAIN_IMAGES,
    VAL_IMAGES,
    TRAIN_LABELS,
    VAL_LABELS,
]:
    folder.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================
# LIMPIAR SPLIT ANTERIOR
# ============================================================

for folder in [
    TRAIN_IMAGES,
    VAL_IMAGES,
    TRAIN_LABELS,
    VAL_LABELS,
]:
    for f in folder.iterdir():
        if f.is_file():
            f.unlink()


# ============================================================
# SPLIT ESTRATIFICADO POR BLOQUES
# ============================================================

rng = random.Random(SEED)

total_train = 0
total_val = 0

for bloque in range(4):

    inicio = bloque * IMAGENES_POR_BLOQUE + 1
    fin = inicio + IMAGENES_POR_BLOQUE

    ids = list(
        range(
            inicio,
            fin,
        )
    )

    rng.shuffle(ids)

    ids_train = ids[:TRAIN_POR_BLOQUE]
    ids_val = ids[
        TRAIN_POR_BLOQUE:
        TRAIN_POR_BLOQUE + VAL_POR_BLOQUE
    ]

    print()
    print(
        f"BLOQUE {bloque + 1}"
    )
    print(
        "Train:",
        len(ids_train)
    )
    print(
        "Val:",
        len(ids_val)
    )

    # --------------------------------------------------------
    # TRAIN
    # --------------------------------------------------------

    for idx in ids_train:

        nombre = f"img_{idx:04d}"

        img_src = (
            IMAGES_ORIG
            / f"{nombre}.png"
        )

        lbl_src = (
            LABELS_ORIG
            / f"{nombre}.txt"
        )

        if not img_src.exists():
            raise FileNotFoundError(
                img_src
            )

        if not lbl_src.exists():
            raise FileNotFoundError(
                lbl_src
            )

        shutil.copy2(
            img_src,
            TRAIN_IMAGES
            / img_src.name,
        )

        shutil.copy2(
            lbl_src,
            TRAIN_LABELS
            / lbl_src.name,
        )

        total_train += 1

    # --------------------------------------------------------
    # VAL
    # --------------------------------------------------------

    for idx in ids_val:

        nombre = f"img_{idx:04d}"

        img_src = (
            IMAGES_ORIG
            / f"{nombre}.png"
        )

        lbl_src = (
            LABELS_ORIG
            / f"{nombre}.txt"
        )

        if not img_src.exists():
            raise FileNotFoundError(
                img_src
            )

        if not lbl_src.exists():
            raise FileNotFoundError(
                lbl_src
            )

        shutil.copy2(
            img_src,
            VAL_IMAGES
            / img_src.name,
        )

        shutil.copy2(
            lbl_src,
            VAL_LABELS
            / lbl_src.name,
        )

        total_val += 1


# ============================================================
# CREAR data.yaml
# ============================================================

yaml_path = (
    DATASET_SPLIT
    / "data.yaml"
)

yaml_text = f"""path: {DATASET_SPLIT}
train: images/train
val: images/val

names:
  0: bandeja
"""

with open(
    yaml_path,
    "w",
    encoding="utf-8",
) as f:

    f.write(
        yaml_text
    )


# ============================================================
# RESULTADO
# ============================================================

print()
print("=" * 70)
print("DATASET PREPARADO")
print("=" * 70)

print(
    "Train:",
    total_train
)

print(
    "Val:",
    total_val
)

print(
    "YAML:",
    yaml_path
)

print("=" * 70)