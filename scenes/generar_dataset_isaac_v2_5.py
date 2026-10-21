import os
import csv
import random
import traceback

import cv2
import numpy as np

import omni.usd
import omni.replicator.core as rep

from pxr import Usd, UsdGeom, Gf

from isaacsim.core.utils.semantics import add_update_semantics


# ============================================================
# CONFIGURACIÓN
# ============================================================

NUM_IMAGENES = 5

WIDTH = 640
HEIGHT = 480

CAMERA_PATH = "/World/Camera_RGB_Astra"
BANDEJA_PATH = "/World/bandeja_v2"

OUTPUT_DIR = "/home/cristian/Desktop/dataset_isaac_v2_test_5"

IMAGES_DIR = os.path.join(
    OUTPUT_DIR,
    "images"
)

MASKS_DIR = os.path.join(
    OUTPUT_DIR,
    "masks"
)

LABELS_DIR = os.path.join(
    OUTPUT_DIR,
    "labels"
)

METADATA_PATH = os.path.join(
    OUTPUT_DIR,
    "metadata.csv"
)

os.makedirs(
    IMAGES_DIR,
    exist_ok=True
)

os.makedirs(
    MASKS_DIR,
    exist_ok=True
)

os.makedirs(
    LABELS_DIR,
    exist_ok=True
)


# ============================================================
# DISTRIBUCIÓN DE LAS 5 IMÁGENES
# ============================================================

TIPOS = [
    "normal",
    "normal",
    "normal",
    "occluded",
    "negative",
]

random.shuffle(TIPOS)


# ============================================================
# RANGO DE MOVIMIENTO BANDEJA
# ============================================================

# Son rangos deliberadamente amplios para V2.
# Si alguna posición queda fuera del robot/cámara,
# después los ajustamos viendo estas primeras 5.

X_MIN = 0.15
X_MAX = 0.75

Y_MIN = -1.20
Y_MAX = -0.60

YAW_MIN = -90.0
YAW_MAX = 90.0


# ============================================================
# VARIACIÓN DE CÁMARA
# ============================================================

CAMERA_TRANSLATION_JITTER = 0.025
CAMERA_ROTATION_JITTER = 2.0


# ============================================================
# ESCENA
# ============================================================

stage = omni.usd.get_context().get_stage()

if stage is None:
    raise RuntimeError(
        "No hay una escena USD abierta."
    )


camera_prim = stage.GetPrimAtPath(
    CAMERA_PATH
)

tray_prim = stage.GetPrimAtPath(
    BANDEJA_PATH
)

if not camera_prim.IsValid():
    raise RuntimeError(
        f"No existe la cámara: {CAMERA_PATH}"
    )

if not tray_prim.IsValid():
    raise RuntimeError(
        f"No existe la bandeja: {BANDEJA_PATH}"
    )


print("=" * 70)
print("ISAAC SIM - DATASET V2 - PRUEBA 5 IMÁGENES")
print("=" * 70)

print("\nCámara:")
print(CAMERA_PATH)

print("\nBandeja:")
print(BANDEJA_PATH)

print("\nSalida:")
print(OUTPUT_DIR)


# ============================================================
# SEMÁNTICA BANDEJA
# ============================================================

# Etiqueta en el root
add_update_semantics(
    tray_prim,
    "bandeja",
    "class"
)

# También la ponemos en los Mesh descendientes.
# Esto hace la máscara más robusta.
num_meshes_semanticos = 0

for prim in Usd.PrimRange(tray_prim):

    if prim.IsA(UsdGeom.Mesh):

        add_update_semantics(
            prim,
            "bandeja",
            "class"
        )

        num_meshes_semanticos += 1

print(
    "\nMeshes de bandeja etiquetados:",
    num_meshes_semanticos
)


# ============================================================
# FUNCIONES DE TRANSFORMACIÓN
# ============================================================

def get_local_transform(prim):

    xformable = UsdGeom.Xformable(
        prim
    )

    matrix, resets = (
        xformable.GetLocalTransformation()
    )

    return matrix


def extract_translation(matrix):

    t = matrix.ExtractTranslation()

    return np.array(
        [
            float(t[0]),
            float(t[1]),
            float(t[2]),
        ],
        dtype=np.float64
    )


def extract_rotation_xyz(matrix):

    transform = Gf.Transform(
        matrix
    )

    rotation = transform.GetRotation()

    euler = rotation.Decompose(
        Gf.Vec3d.XAxis(),
        Gf.Vec3d.YAxis(),
        Gf.Vec3d.ZAxis()
    )

    return np.array(
        [
            float(euler[0]),
            float(euler[1]),
            float(euler[2]),
        ],
        dtype=np.float64
    )


def set_translate_rotate(
    prim,
    translation,
    rotation_xyz
):

    xform = UsdGeom.Xformable(
        prim
    )

    # Limpiamos SOLO los xformOps de este prim.
    # No toca geometría ni materiales.
    xform.ClearXformOpOrder()

    translate_op = xform.AddTranslateOp()

    rotate_op = xform.AddRotateXYZOp()

    translate_op.Set(
        Gf.Vec3d(
            float(translation[0]),
            float(translation[1]),
            float(translation[2])
        )
    )

    rotate_op.Set(
        Gf.Vec3f(
            float(rotation_xyz[0]),
            float(rotation_xyz[1]),
            float(rotation_xyz[2])
        )
    )


# ============================================================
# GUARDAR TRANSFORMACIONES ORIGINALES
# ============================================================

CAMERA_MATRIX_ORIGINAL = (
    get_local_transform(
        camera_prim
    )
)

TRAY_MATRIX_ORIGINAL = (
    get_local_transform(
        tray_prim
    )
)

CAMERA_POS_ORIGINAL = (
    extract_translation(
        CAMERA_MATRIX_ORIGINAL
    )
)

CAMERA_ROT_ORIGINAL = (
    extract_rotation_xyz(
        CAMERA_MATRIX_ORIGINAL
    )
)

TRAY_POS_ORIGINAL = (
    extract_translation(
        TRAY_MATRIX_ORIGINAL
    )
)

TRAY_ROT_ORIGINAL = (
    extract_rotation_xyz(
        TRAY_MATRIX_ORIGINAL
    )
)

print(
    "\nCámara original pos:",
    CAMERA_POS_ORIGINAL
)

print(
    "Cámara original rot:",
    CAMERA_ROT_ORIGINAL
)

print(
    "\nBandeja original pos:",
    TRAY_POS_ORIGINAL
)

print(
    "Bandeja original rot:",
    TRAY_ROT_ORIGINAL
)


# ============================================================
# RANDOMIZAR BANDEJA
# ============================================================

def randomize_tray():

    x = random.uniform(
        X_MIN,
        X_MAX
    )

    y = random.uniform(
        Y_MIN,
        Y_MAX
    )

    z = float(
        TRAY_POS_ORIGINAL[2]
    )

    yaw = random.uniform(
        YAW_MIN,
        YAW_MAX
    )

    rotation = np.array(
        [
            TRAY_ROT_ORIGINAL[0],
            TRAY_ROT_ORIGINAL[1],
            yaw
        ]
    )

    set_translate_rotate(
        tray_prim,
        [x, y, z],
        rotation
    )

    return x, y, z, yaw


# ============================================================
# RANDOMIZAR CÁMARA
# ============================================================

def randomize_camera():

    dx = random.uniform(
        -CAMERA_TRANSLATION_JITTER,
        CAMERA_TRANSLATION_JITTER
    )

    dy = random.uniform(
        -CAMERA_TRANSLATION_JITTER,
        CAMERA_TRANSLATION_JITTER
    )

    dz = random.uniform(
        -CAMERA_TRANSLATION_JITTER,
        CAMERA_TRANSLATION_JITTER
    )

    drx = random.uniform(
        -CAMERA_ROTATION_JITTER,
        CAMERA_ROTATION_JITTER
    )

    dry = random.uniform(
        -CAMERA_ROTATION_JITTER,
        CAMERA_ROTATION_JITTER
    )

    drz = random.uniform(
        -CAMERA_ROTATION_JITTER,
        CAMERA_ROTATION_JITTER
    )

    new_pos = (
        CAMERA_POS_ORIGINAL
        + np.array(
            [
                dx,
                dy,
                dz
            ]
        )
    )

    new_rot = (
        CAMERA_ROT_ORIGINAL
        + np.array(
            [
                drx,
                dry,
                drz
            ]
        )
    )

    set_translate_rotate(
        camera_prim,
        new_pos,
        new_rot
    )

    return (
        dx,
        dy,
        dz,
        drx,
        dry,
        drz
    )


# ============================================================
# LUCES
# ============================================================

def find_lights():

    lights = []

    for prim in stage.Traverse():

        intensity_attr = (
            prim.GetAttribute(
                "inputs:intensity"
            )
        )

        if not intensity_attr.IsValid():

            intensity_attr = (
                prim.GetAttribute(
                    "intensity"
                )
            )

        if intensity_attr.IsValid():

            value = intensity_attr.Get()

            if value is not None:

                lights.append(
                    (
                        prim,
                        intensity_attr,
                        float(value)
                    )
                )

    return lights


LIGHTS = find_lights()

print(
    "\nLuces encontradas:",
    len(LIGHTS)
)

for prim, attr, value in LIGHTS:

    print(
        "  ",
        prim.GetPath(),
        "intensidad:",
        value
    )


def randomize_lights():

    if len(LIGHTS) == 0:

        return 1.0

    global_factor = random.uniform(
        0.60,
        1.35
    )

    for (
        prim,
        intensity_attr,
        original_intensity
    ) in LIGHTS:

        individual_factor = random.uniform(
            0.75,
            1.25
        )

        new_value = (
            original_intensity
            * global_factor
            * individual_factor
        )

        intensity_attr.Set(
            new_value
        )

    return global_factor


def restore_lights():

    for (
        prim,
        intensity_attr,
        original_intensity
    ) in LIGHTS:

        intensity_attr.Set(
            original_intensity
        )


# ============================================================
# CREAR OCLUSOR
# ============================================================

OCCLUDER_PATH = (
    "/World/SimToRealV2_Occluder"
)


def remove_occluder():

    prim = stage.GetPrimAtPath(
        OCCLUDER_PATH
    )

    if prim.IsValid():

        stage.RemovePrim(
            OCCLUDER_PATH
        )


def create_occluder(
    tray_x,
    tray_y,
    tray_z
):

    remove_occluder()

    cube = UsdGeom.Cube.Define(
        stage,
        OCCLUDER_PATH
    )

    cube.CreateSizeAttr(
        1.0
    )

    prim = cube.GetPrim()

    xform = UsdGeom.Xformable(
        prim
    )

    translate = (
        xform.AddTranslateOp()
    )

    scale = (
        xform.AddScaleOp()
    )

    offset_x = random.uniform(
        -0.10,
        0.10
    )

    offset_y = random.uniform(
        -0.06,
        0.06
    )

    sx = random.uniform(
        0.05,
        0.12
    )

    sy = random.uniform(
        0.04,
        0.10
    )

    sz = random.uniform(
        0.04,
        0.08
    )

    translate.Set(
        Gf.Vec3d(
            tray_x + offset_x,
            tray_y + offset_y,
            tray_z + (
                sz / 2.0
            ) + 0.025
        )
    )

    scale.Set(
        Gf.Vec3f(
            sx,
            sy,
            sz
        )
    )

    # Color visible aleatorio
    color = Gf.Vec3f(
        random.uniform(
            0.05,
            0.9
        ),
        random.uniform(
            0.05,
            0.9
        ),
        random.uniform(
            0.05,
            0.9
        )
    )

    cube.CreateDisplayColorAttr(
        [color]
    )


# ============================================================
# POSTPROCESADO SIM -> REAL
# ============================================================

def sim_to_real_augmentation(
    image
):

    img = image.astype(
        np.float32
    )

    # --------------------------------------------------------
    # BRILLO
    # --------------------------------------------------------

    brightness = random.uniform(
        0.70,
        1.30
    )

    img *= brightness

    # --------------------------------------------------------
    # CONTRASTE
    # --------------------------------------------------------

    contrast = random.uniform(
        0.75,
        1.30
    )

    mean = np.mean(
        img,
        axis=(0, 1),
        keepdims=True
    )

    img = (
        mean
        + contrast
        * (
            img
            - mean
        )
    )

    # --------------------------------------------------------
    # GANANCIA RGB
    # --------------------------------------------------------

    gains = np.array(
        [
            random.uniform(
                0.88,
                1.12
            ),
            random.uniform(
                0.88,
                1.12
            ),
            random.uniform(
                0.88,
                1.12
            ),
        ],
        dtype=np.float32
    )

    img *= gains

    # --------------------------------------------------------
    # RUIDO
    # --------------------------------------------------------

    if random.random() < 0.80:

        sigma = random.uniform(
            1.0,
            7.0
        )

        noise = np.random.normal(
            0,
            sigma,
            img.shape
        )

        img += noise

    img = np.clip(
        img,
        0,
        255
    )

    img = img.astype(
        np.uint8
    )

    # --------------------------------------------------------
    # BLUR
    # --------------------------------------------------------

    if random.random() < 0.45:

        kernel = random.choice(
            [3, 5]
        )

        img = cv2.GaussianBlur(
            img,
            (
                kernel,
                kernel
            ),
            0
        )

    # --------------------------------------------------------
    # JPEG
    # --------------------------------------------------------

    if random.random() < 0.40:

        quality = random.randint(
            70,
            95
        )

        success, encoded = (
            cv2.imencode(
                ".jpg",
                img,
                [
                    cv2.IMWRITE_JPEG_QUALITY,
                    quality
                ]
            )
        )

        if success:

            decoded = cv2.imdecode(
                encoded,
                cv2.IMREAD_COLOR
            )

            if decoded is not None:

                img = decoded

    return img


# ============================================================
# MÁSCARA -> POLÍGONO YOLO-SEG
# ============================================================

def mask_to_yolo_polygon(
    mask
):

    binary = (
        mask > 0
    ).astype(
        np.uint8
    )

    contours, _ = (
        cv2.findContours(
            binary,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
    )

    if len(contours) == 0:

        return None

    all_points = np.vstack(
        contours
    )

    hull = cv2.convexHull(
        all_points
    )

    perimeter = cv2.arcLength(
        hull,
        True
    )

    approx = cv2.approxPolyDP(
        hull,
        0.003 * perimeter,
        True
    )

    if len(approx) < 3:

        return None

    h, w = mask.shape[:2]

    values = []

    for point in approx:

        px = float(
            point[0][0]
        )

        py = float(
            point[0][1]
        )

        x = np.clip(
            px / w,
            0.0,
            1.0
        )

        y = np.clip(
            py / h,
            0.0,
            1.0
        )

        values.extend(
            [
                x,
                y
            ]
        )

    return values


# ============================================================
# SEMANTIC ID -> BANDEJA
# ============================================================

def label_contains_bandeja(
    label_info
):

    if label_info is None:

        return False

    if isinstance(
        label_info,
        str
    ):

        return (
            "bandeja"
            in label_info.lower()
        )

    if isinstance(
        label_info,
        dict
    ):

        for key, value in (
            label_info.items()
        ):

            if (
                str(key).lower()
                == "class"
                and
                "bandeja"
                in str(value).lower()
            ):

                return True

            if (
                "bandeja"
                in str(value).lower()
            ):

                return True

    if isinstance(
        label_info,
        (
            list,
            tuple
        )
    ):

        for value in label_info:

            if label_contains_bandeja(
                value
            ):

                return True

    return False


def semantic_to_tray_mask(
    semantic_output
):

    if not isinstance(
        semantic_output,
        dict
    ):

        raise RuntimeError(
            "El annotator semantic_segmentation "
            "no devolvió un diccionario."
        )

    semantic_data = (
        semantic_output.get(
            "data"
        )
    )

    info = (
        semantic_output.get(
            "info",
            {}
        )
    )

    id_to_labels = (
        info.get(
            "idToLabels",
            {}
        )
    )

    if semantic_data is None:

        raise RuntimeError(
            "semantic_segmentation devolvió "
            "data=None."
        )

    sem = np.asarray(
        semantic_data
    )

    if sem.ndim == 3:

        sem = sem[:, :, 0]

    sem = sem.astype(
        np.uint32
    )

    tray_ids = []

    for raw_id, label_info in (
        id_to_labels.items()
    ):

        if label_contains_bandeja(
            label_info
        ):

            try:

                tray_ids.append(
                    int(raw_id)
                )

            except Exception:

                pass

    if len(tray_ids) == 0:

        print(
            "\nADVERTENCIA:"
        )

        print(
            "No encontré el ID semántico "
            "'bandeja'."
        )

        print(
            "idToLabels:"
        )

        print(
            id_to_labels
        )

        return np.zeros(
            (
                HEIGHT,
                WIDTH
            ),
            dtype=np.uint8
        ), []

    mask = np.isin(
        sem,
        tray_ids
    ).astype(
        np.uint8
    ) * 255

    return mask, tray_ids


# ============================================================
# RENDER PRODUCT
# ============================================================

rep.orchestrator.set_capture_on_play(
    False
)

render_product = (
    rep.create.render_product(
        CAMERA_PATH,
        (
            WIDTH,
            HEIGHT
        )
    )
)


# ============================================================
# RGB ANNOTATOR
# ============================================================

rgb_annotator = (
    rep.AnnotatorRegistry
    .get_annotator(
        "rgb"
    )
)

rgb_annotator.attach(
    [
        render_product
    ]
)


# ============================================================
# SEMANTIC SEGMENTATION
# ============================================================

semantic_annotator = (
    rep.AnnotatorRegistry
    .get_annotator(
        "semantic_segmentation",
        init_params={
            "colorize": False,
            "semanticTypes": [
                "class"
            ]
        }
    )
)

semantic_annotator.attach(
    [
        render_product
    ]
)


# ============================================================
# CSV
# ============================================================

csv_file = open(
    METADATA_PATH,
    "w",
    newline="",
    encoding="utf-8"
)

csv_writer = csv.writer(
    csv_file
)

csv_writer.writerow(
    [
        "imagen",
        "tipo",
        "tray_x",
        "tray_y",
        "tray_z",
        "tray_yaw",
        "cam_dx",
        "cam_dy",
        "cam_dz",
        "cam_drx",
        "cam_dry",
        "cam_drz",
        "light_factor",
        "mask_pixels",
        "tray_semantic_ids",
        "label_valid"
    ]
)


# ============================================================
# GENERACIÓN
# ============================================================

try:

    print("\n")
    print("=" * 70)
    print("GENERANDO 5 IMÁGENES")
    print("=" * 70)

    for index in range(
        1,
        NUM_IMAGENES + 1
    ):

        tipo = TIPOS[
            index - 1
        ]

        print("\n")
        print("-" * 70)

        print(
            f"[{index}/{NUM_IMAGENES}] "
            f"Tipo: {tipo}"
        )

        # ----------------------------------------------------
        # LIMPIAR OCLUSOR ANTERIOR
        # ----------------------------------------------------

        remove_occluder()

        # ----------------------------------------------------
        # POSE BANDEJA
        # ----------------------------------------------------

        (
            tray_x,
            tray_y,
            tray_z,
            tray_yaw
        ) = randomize_tray()

        # ----------------------------------------------------
        # CÁMARA
        # ----------------------------------------------------

        (
            cam_dx,
            cam_dy,
            cam_dz,
            cam_drx,
            cam_dry,
            cam_drz
        ) = randomize_camera()

        # ----------------------------------------------------
        # LUZ
        # ----------------------------------------------------

        light_factor = (
            randomize_lights()
        )

        # ----------------------------------------------------
        # OCLUSIÓN
        # ----------------------------------------------------

        if tipo == "occluded":

            create_occluder(
                tray_x,
                tray_y,
                tray_z
            )

        # ----------------------------------------------------
        # NEGATIVA
        # ----------------------------------------------------

        if tipo == "negative":

            # Dejamos la bandeja completamente
            # fuera del campo de visión.
            set_translate_rotate(
                tray_prim,
                [
                    10.0,
                    10.0,
                    10.0
                ],
                TRAY_ROT_ORIGINAL
            )

        # ----------------------------------------------------
        # RENDER
        # ----------------------------------------------------

        rep.orchestrator.step(
            rt_subframes=8
        )

        # ----------------------------------------------------
        # RGB
        # ----------------------------------------------------

        rgb_output = (
            rgb_annotator.get_data()
        )

        if isinstance(
            rgb_output,
            dict
        ):

            rgb = rgb_output.get(
                "data"
            )

        else:

            rgb = rgb_output

        if rgb is None:

            print(
                "ERROR: RGB vacío."
            )

            continue

        rgb = np.asarray(
            rgb
        )

        if rgb.ndim != 3:

            print(
                "ERROR: formato RGB inesperado:",
                rgb.shape
            )

            continue

        if rgb.shape[2] == 4:

            rgb = rgb[
                :,
                :,
                :3
            ]

        rgb_bgr = cv2.cvtColor(
            rgb.astype(
                np.uint8
            ),
            cv2.COLOR_RGB2BGR
        )

        rgb_aug = (
            sim_to_real_augmentation(
                rgb_bgr
            )
        )

        # ----------------------------------------------------
        # SEMANTIC MASK
        # ----------------------------------------------------

        semantic_output = (
            semantic_annotator.get_data()
        )

        (
            mask,
            tray_ids
        ) = semantic_to_tray_mask(
            semantic_output
        )

        # ----------------------------------------------------
        # NOMBRES
        # ----------------------------------------------------

        base_name = (
            f"isaac_v2_{index:04d}"
        )

        image_path = os.path.join(
            IMAGES_DIR,
            base_name + ".png"
        )

        mask_path = os.path.join(
            MASKS_DIR,
            base_name + ".png"
        )

        label_path = os.path.join(
            LABELS_DIR,
            base_name + ".txt"
        )

        # ----------------------------------------------------
        # GUARDAR RGB
        # ----------------------------------------------------

        cv2.imwrite(
            image_path,
            rgb_aug
        )

        # ----------------------------------------------------
        # GUARDAR MASK
        # ----------------------------------------------------

        cv2.imwrite(
            mask_path,
            mask
        )

        # ----------------------------------------------------
        # YOLO LABEL
        # ----------------------------------------------------

        mask_pixels = int(
            np.count_nonzero(
                mask
            )
        )

        label_valid = False

        # Negativa correcta:
        # TXT vacío.
        if tipo == "negative":

            open(
                label_path,
                "w"
            ).close()

            label_valid = (
                mask_pixels == 0
            )

        else:

            polygon = (
                mask_to_yolo_polygon(
                    mask
                )
            )

            if polygon is not None:

                values = [
                    "0"
                ]

                values.extend(
                    [
                        f"{value:.6f}"
                        for value
                        in polygon
                    ]
                )

                with open(
                    label_path,
                    "w",
                    encoding="utf-8"
                ) as f:

                    f.write(
                        " ".join(
                            values
                        )
                    )

                    f.write(
                        "\n"
                    )

                label_valid = True

            else:

                open(
                    label_path,
                    "w"
                ).close()

                label_valid = False

        # ----------------------------------------------------
        # CSV
        # ----------------------------------------------------

        csv_writer.writerow(
            [
                base_name + ".png",
                tipo,
                tray_x,
                tray_y,
                tray_z,
                tray_yaw,
                cam_dx,
                cam_dy,
                cam_dz,
                cam_drx,
                cam_dry,
                cam_drz,
                light_factor,
                mask_pixels,
                str(
                    tray_ids
                ),
                int(
                    label_valid
                )
            ]
        )

        csv_file.flush()

        print(
            "RGB:",
            image_path
        )

        print(
            "MASK pixels:",
            mask_pixels
        )

        print(
            "Semantic IDs bandeja:",
            tray_ids
        )

        print(
            "Label válido:",
            label_valid
        )


# ============================================================
# ERROR
# ============================================================

except Exception:

    print("\n")
    print("=" * 70)
    print("ERROR DURANTE GENERACIÓN")
    print("=" * 70)

    traceback.print_exc()


# ============================================================
# RESTAURAR ESCENA
# ============================================================

finally:

    print("\nRestaurando escena...")

    remove_occluder()

    restore_lights()

    set_translate_rotate(
        camera_prim,
        CAMERA_POS_ORIGINAL,
        CAMERA_ROT_ORIGINAL
    )

    set_translate_rotate(
        tray_prim,
        TRAY_POS_ORIGINAL,
        TRAY_ROT_ORIGINAL
    )

    csv_file.close()

    print(
        "Escena restaurada."
    )


# ============================================================
# FIN
# ============================================================

print("\n")
print("=" * 70)
print("PRUEBA V2 TERMINADA")
print("=" * 70)

print(
    "\nDataset guardado en:"
)

print(
    OUTPUT_DIR
)

print("\nDebe contener:")

print(
    "images/ -> 5 RGB"
)

print(
    "masks/  -> 5 máscaras"
)

print(
    "labels/ -> 5 TXT YOLO"
)

print(
    "metadata.csv"
)

print("\nFIN")