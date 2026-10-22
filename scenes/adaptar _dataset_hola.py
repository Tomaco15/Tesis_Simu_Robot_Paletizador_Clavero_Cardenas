
import os
import csv
import shutil
from pathlib import Path

import cv2
import yaml
import numpy as np


# ============================================================
# CONFIGURACION
# ============================================================

# Dataset original generado desde Isaac Sim
INPUT_DIR = Path(
    "/home/cristian/Desktop/dataset_bandeja_sola_600"
)

# Dataset de salida para YOLO
OUTPUT_DIR = Path(
    "/home/cristian/Desktop/dataset_bandeja_yolo_seg"
)

# Una sola clase
CLASS_ID = 0
CLASS_NAME = "bandeja"

# Proporciones train / val / test
TRAIN_RATIO = 0.70
VAL_RATIO = 0.20
TEST_RATIO = 0.10

RANDOM_SEED = 20261021

# Simplificacion del poligono
# Menor valor = contorno mas detallado
POLYGON_EPSILON = 0.0015

# Area minima de un contorno, en pixeles
MIN_CONTOUR_AREA = 30

# Guardar ejemplos de visualizacion
SAVE_PREVIEWS = True
MAX_PREVIEWS = 20

# Seguridad: no sobrescribir conversiones anteriores
OVERWRITE_OUTPUT = False


# ============================================================
# DIRECTORIOS DE ENTRADA
# ============================================================

IMAGES_DIR = INPUT_DIR / "images"

MASKS_DIR = INPUT_DIR / "masks_visible"


# ============================================================
# FUNCIONES
# ============================================================

def crear_directorios():

    if OUTPUT_DIR.exists():

        if OVERWRITE_OUTPUT:
            shutil.rmtree(OUTPUT_DIR)

        elif any(OUTPUT_DIR.iterdir()):
            raise RuntimeError(
                "La carpeta de salida ya contiene archivos: "
                f"{OUTPUT_DIR}\n"
                "Utiliza otra carpeta o configura "
                "OVERWRITE_OUTPUT = True."
            )

    for split in ["train", "val", "test"]:

        (OUTPUT_DIR / "images" / split).mkdir(
            parents=True,
            exist_ok=True
        )

        (OUTPUT_DIR / "labels" / split).mkdir(
            parents=True,
            exist_ok=True
        )

    (OUTPUT_DIR / "previews").mkdir(
        parents=True,
        exist_ok=True
    )


def obtener_imagenes():

    if not IMAGES_DIR.exists():
        raise FileNotFoundError(
            f"No existe: {IMAGES_DIR}"
        )

    if not MASKS_DIR.exists():
        raise FileNotFoundError(
            f"No existe: {MASKS_DIR}"
        )

    extensiones = {
        ".png", ".jpg", ".jpeg"
    }

    imagenes = sorted([
        p for p in IMAGES_DIR.iterdir()
        if p.suffix.lower() in extensiones
    ])

    if not imagenes:
        raise RuntimeError(
            "No se encontraron imagenes RGB."
        )

    pares = []

    for imagen in imagenes:

        mascara = MASKS_DIR / (
            imagen.stem + ".png"
        )

        if not mascara.exists():

            print(
                "[AVISO] Sin mascara:",
                imagen.name
            )

            continue

        pares.append(
            (imagen, mascara)
        )

    return pares


# ============================================================
# MASCARA -> POLIGONO YOLO
# ============================================================

def mascara_a_yolo(mask):

    # La mascara debe ser de un canal.
    # Cualquier pixel distinto de 0 se considera bandeja.

    binary = (
        (mask > 0).astype(np.uint8) * 255
    )

    height, width = binary.shape

    if np.count_nonzero(binary) == 0:
        return []

    # Buscar contornos externos
    contours, _ = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if not contours:
        return []

    # Hay una sola bandeja en cada imagen.
    # Se conserva el contorno principal.
    contour = max(
        contours,
        key=cv2.contourArea
    )

    area = cv2.contourArea(contour)

    if area < MIN_CONTOUR_AREA:
        return []

    # Reducir cantidad de puntos conservando la forma
    perimeter = cv2.arcLength(
        contour,
        True
    )

    epsilon = (
        POLYGON_EPSILON * perimeter
    )

    polygon = cv2.approxPolyDP(
        contour,
        epsilon,
        True
    )

    polygon = polygon.reshape(-1, 2)

    # YOLO requiere al menos 3 puntos
    if len(polygon) < 3:
        return []

    # Normalizar coordenadas al intervalo [0, 1]
    points = []

    for x, y in polygon:

        xn = float(x) / float(width)
        yn = float(y) / float(height)

        xn = np.clip(xn, 0.0, 1.0)
        yn = np.clip(yn, 0.0, 1.0)

        points.extend([
            float(xn),
            float(yn)
        ])

    # Una sola instancia, clase 0
    linea = (
        str(CLASS_ID)
        + " "
        + " ".join(
            f"{v:.6f}"
            for v in points
        )
    )

    return [linea]


# ============================================================
# VISUALIZACION
# ============================================================

def crear_preview(
    image,
    mask,
    destination
):

    overlay = image.copy()

    binary = (
        (mask > 0).astype(np.uint8) * 255
    )

    contours, _ = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    color_layer = overlay.copy()

    color_layer[binary > 0] = (
        0, 0, 255
    )

    overlay = cv2.addWeighted(
        overlay,
        0.55,
        color_layer,
        0.45,
        0
    )

    cv2.drawContours(
        overlay,
        contours,
        -1,
        (0, 255, 0),
        2
    )

    cv2.imwrite(
        str(destination),
        overlay
    )


# ============================================================
# GENERAR DATA.YAML
# ============================================================

def crear_yaml():

    data = {
        "path": str(OUTPUT_DIR.resolve()),
        "train": "images/train",
        "val": "images/val",
        "test": "images/test",
        "nc": 1,
        "names": {
            0: CLASS_NAME
        }
    }

    yaml_path = OUTPUT_DIR / "data.yaml"

    with open(
        yaml_path,
        "w",
        encoding="utf-8"
    ) as f:

        yaml.safe_dump(
            data,
            f,
            sort_keys=False,
            allow_unicode=True
        )

    print(
        "[OK] Archivo data.yaml creado"
    )


# ============================================================
# CONVERTIR UN PAR RGB / MASCARA
# ============================================================

def convertir_par(
    image_path,
    mask_path,
    split,
    preview=False
):

    image = cv2.imread(
        str(image_path),
        cv2.IMREAD_COLOR
    )

    mask = cv2.imread(
        str(mask_path),
        cv2.IMREAD_GRAYSCALE
    )

    if image is None:
        raise RuntimeError(
            f"No se pudo leer {image_path}"
        )

    if mask is None:
        raise RuntimeError(
            f"No se pudo leer {mask_path}"
        )

    if image.shape[:2] != mask.shape[:2]:
        raise RuntimeError(
            "Dimensiones RGB y mascara distintas: "
            f"{image_path.name}"
        )

    # Convertir mascara a etiqueta YOLO
    labels = mascara_a_yolo(mask)

    # Las mascaras vacias no deben convertirse
    # silenciosamente en imagenes negativas.
    if not labels:
        raise RuntimeError(
            "Mascara vacia o contorno invalido: "
            f"{mask_path.name}"
        )

    # Destinos
    target_image = (
        OUTPUT_DIR
        / "images"
        / split
        / image_path.name
    )

    target_label = (
        OUTPUT_DIR
        / "labels"
        / split
        / (image_path.stem + ".txt")
    )

    # Copiar imagen original, sin modificar calidad
    shutil.copy2(
        image_path,
        target_image
    )

    # Guardar anotacion
    with open(
        target_label,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(labels) + "\n"
        )

    if preview:

        preview_path = (
            OUTPUT_DIR
            / "previews"
            / image_path.name
        )

        crear_preview(
            image,
            mask,
            preview_path
        )

    return {
        "image": image_path.name,
        "split": split,
        "mask_pixels": int(
            np.count_nonzero(mask)
        ),
        "instances": len(labels),
        "polygon_points": (
            len(labels[0].split()) - 1
        ) // 2
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n" + "=" * 60)

    print("CONVERSOR ISAAC SIM -> YOLO SEG")

    print("=" * 60)

    print(
        "Dataset original:",
        INPUT_DIR
    )

    print(
        "Dataset YOLO:",
        OUTPUT_DIR
    )

    # --------------------------------------------------------
    # VERIFICAR ENTRADA
    # --------------------------------------------------------

    pares = obtener_imagenes()

    total = len(pares)

    print(
        "\nPares RGB / mascara encontrados:",
        total
    )

    if total == 0:
        raise RuntimeError(
            "No hay pares validos."
        )

    # --------------------------------------------------------
    # MEZCLAR DATOS
    # --------------------------------------------------------

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    indices = rng.permutation(total)

    pares = [
        pares[int(i)]
        for i in indices
    ]

    # --------------------------------------------------------
    # DIVISION DEL DATASET
    # --------------------------------------------------------

    n_train = int(
        total * TRAIN_RATIO
    )

    n_val = int(
        total * VAL_RATIO
    )

    splits = {
        "train": pares[:n_train],
        "val": pares[n_train:n_train + n_val],
        "test": pares[n_train + n_val:]
    }

    print("\nDistribucion:")

    for split, elementos in splits.items():

        print(
            f"  {split}: {len(elementos)}"
        )

    # --------------------------------------------------------
    # PREPARAR SALIDA
    # --------------------------------------------------------

    crear_directorios()

    report = []

    errores = []

    preview_count = 0

    # --------------------------------------------------------
    # CONVERTIR
    # --------------------------------------------------------

    for split, elementos in splits.items():

        print(
            f"\nProcesando: {split}"
        )

        for i, (image_path, mask_path) in enumerate(
            elementos,
            start=1
        ):

            generar_preview = (
                SAVE_PREVIEWS
                and preview_count < MAX_PREVIEWS
            )

            try:

                result = convertir_par(
                    image_path,
                    mask_path,
                    split,
                    generar_preview
                )

                report.append(result)

                if generar_preview:
                    preview_count += 1

                if (
                    i % 25 == 0
                    or i == len(elementos)
                ):

                    print(
                        f"[OK] {split}: "
                        f"{i}/{len(elementos)}"
                    )

            except Exception as e:

                errores.append({
                    "image": image_path.name,
                    "error": str(e)
                })

                print(
                    "[ERROR]",
                    image_path.name,
                    str(e)
                )

    # --------------------------------------------------------
    # CREAR YAML
    # --------------------------------------------------------

    crear_yaml()

    # --------------------------------------------------------
    # REPORTE
    # --------------------------------------------------------

    report_path = (
        OUTPUT_DIR / "conversion_report.csv"
    )

    with open(
        report_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image",
                "split",
                "mask_pixels",
                "instances",
                "polygon_points"
            ]
        )

        writer.writeheader()
        writer.writerows(report)

    if errores:

        error_path = (
            OUTPUT_DIR / "conversion_errors.csv"
        )

        with open(
            error_path,
            "w",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=["image", "error"]
            )

            writer.writeheader()
            writer.writerows(errores)

    # --------------------------------------------------------
    # RESUMEN
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print("CONVERSION FINALIZADA")

    print(
        "Imagenes convertidas:",
        len(report)
    )

    print(
        "Errores:",
        len(errores)
    )

    print(
        "Carpeta de salida:",
        OUTPUT_DIR
    )

    for split in splits:

        count = sum(
            1 for r in report
            if r["split"] == split
        )

        print(
            f"{split}: {count}"
        )

    print("=" * 60)


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":
    main()
