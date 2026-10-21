import os
import csv
import asyncio
import numpy as np
import cv2

from PIL import Image

import omni.usd
import omni.replicator.core as rep

from pxr import Usd, UsdGeom, Gf

from isaacsim.sensors.camera import Camera
from isaacsim.core.utils.semantics import add_update_semantics


# ============================================================
# CONFIGURACION GENERAL
# ============================================================

WIDTH = 640
HEIGHT = 480

CAMERA_RGB_PATH = "/World/Camera_RGB_Astra"

PIVOTE_PATH = "/World/bandeja_v2"

ROBOT_ROOT_PATH = "/World/robot_ensamble"

ROBOT_JOINT_NAMES = (
    "x_link",
    "y_link",
    "z_link",
    "r_joint",
)

# Los cubos/objetos NO se crean dentro de bandeja_v2
# para que no hereden la semantica "bandeja".
OBJECTS_ROOT_PATH = "/World/DatasetObjects"


# ============================================================
# SALIDA
# ============================================================

OUTPUT_DIR = (
    "/home/cristian/Desktop/"
    "dataset_robot_ensamble_500_v2"
)

IMAGES_DIR = os.path.join(
    OUTPUT_DIR,
    "images"
)

LABELS_DIR = os.path.join(
    OUTPUT_DIR,
    "labels"
)

MASKS_DIR = os.path.join(
    OUTPUT_DIR,
    "masks"
)

META_CSV = os.path.join(
    OUTPUT_DIR,
    "metadata.csv"
)

os.makedirs(
    IMAGES_DIR,
    exist_ok=True
)

os.makedirs(
    LABELS_DIR,
    exist_ok=True
)

os.makedirs(
    MASKS_DIR,
    exist_ok=True
)


# ============================================================
# RANGO DE GENERACION
# ============================================================
#
# Para generar todo:
# SCENE_START = 1
# SCENE_END   = 500
#
# Para probar SOLO los objetos primero:
# SCENE_START = 451
# SCENE_END   = 455
#
# ============================================================

SCENE_START = 1
SCENE_END = 500

TOTAL_IMGS = 500

RANDOM_SEED = 20261015


# ============================================================
# BANDEJA
# ============================================================

DX_RANGE_M = (
    -0.10,
    0.10
)

DY_RANGE_M = (
    -0.10,
    0.10
)

YAW_RANGE_DEG = (
    0.0,
    180.0
)


# ============================================================
# ROBOT
# ============================================================

ROBOT_LIMIT_MARGIN = 0.15


# ============================================================
# ILUMINACION
# ============================================================

# Cambio moderado de intensidad
LIGHT_FACTOR_RANGE = (
    0.75,
    1.25
)

# Para SphereLight, RectLight, DiskLight, etc.
LIGHT_DX_RANGE_M = (
    -0.25,
    0.25
)

LIGHT_DY_RANGE_M = (
    -0.25,
    0.25
)

LIGHT_DZ_RANGE_M = (
    -0.10,
    0.20
)

# Para DistantLight:
# mover XYZ prácticamente no cambia la iluminación.
# Ahí rotamos la dirección.
LIGHT_YAW_RANGE_DEG = (
    -25.0,
    25.0
)

LIGHT_PITCH_RANGE_DEG = (
    -15.0,
    15.0
)


# ============================================================
# OBJETOS DENTRO DE BANDEJA
# ============================================================
#
# Bandeja aproximadamente:
# 0.50 x 0.30 m
#
# Dejamos margen respecto de los bordes.
# ============================================================

OBJECT_LOCAL_X_RANGE = (
    -0.20,
    0.20
)

OBJECT_LOCAL_Y_RANGE = (
    -0.10,
    0.10
)

# Altura aproximada interior de la bandeja.
#
# Si los objetos quedan flotando o enterrados,
# ESTE es el parámetro que ajustamos.
TRAY_OBJECT_BASE_Z = 0.060

OBJECT_COUNT_MIN = 2
OBJECT_COUNT_MAX = 4

OBJECT_SIZE_X_RANGE = (
    0.03,
    0.07
)

OBJECT_SIZE_Y_RANGE = (
    0.03,
    0.07
)

OBJECT_SIZE_Z_RANGE = (
    0.02,
    0.05
)

# Colores discretos, parecidos a cosas reales.
OBJECT_COLORS = [
    (0.72, 0.55, 0.33),   # carton
    (0.20, 0.20, 0.20),   # negro
    (0.65, 0.65, 0.65),   # gris
    (0.85, 0.78, 0.60),   # beige
    (0.45, 0.28, 0.16),   # marron
]


# ============================================================
# ESTABILIZACION
# ============================================================

FRAMES_INICIALES = 10

FRAMES_BANDEJA = 5

FRAMES_ROBOT = 30

FRAMES_POST_ROBOT = 15

FRAMES_LUZ = 8

FRAMES_OBJETOS = 4

FRAMES_CAPTURA = 3


# ============================================================
# YOLO SEG
# ============================================================

CLASS_ID = 0

SEMANTIC_LABEL = "bandeja"

MIN_MASK_PIXELS = 1200

MAX_INTENTOS = 2500

POLY_EPSILON_FACTOR = 0.0025


# ============================================================
# TRANSFORMS
# ============================================================

def obtener_translate_op(path):

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    prim = stage.GetPrimAtPath(
        path
    )

    if not prim.IsValid():

        raise RuntimeError(
            "No existe: "
            +
            path
        )

    xf = UsdGeom.Xformable(
        prim
    )

    for op in xf.GetOrderedXformOps():

        if (
            op.GetOpType()
            ==
            UsdGeom.XformOp.TypeTranslate
        ):

            return op

    return xf.AddTranslateOp()


def leer_translate(path):

    op = obtener_translate_op(
        path
    )

    value = op.Get()

    if value is None:

        return np.zeros(
            3,
            dtype=np.float64
        )

    return np.array(
        [
            float(value[0]),
            float(value[1]),
            float(value[2])
        ],
        dtype=np.float64
    )


def escribir_translate(
    path,
    xyz
):

    op = obtener_translate_op(
        path
    )

    if (
        op.GetPrecision()
        ==
        UsdGeom.XformOp.PrecisionDouble
    ):

        value = Gf.Vec3d(
            float(xyz[0]),
            float(xyz[1]),
            float(xyz[2])
        )

    else:

        value = Gf.Vec3f(
            float(xyz[0]),
            float(xyz[1]),
            float(xyz[2])
        )

    op.Set(
        value
    )


def obtener_rotate_xyz_op(path):

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    prim = stage.GetPrimAtPath(
        path
    )

    if not prim.IsValid():

        raise RuntimeError(
            "No existe: "
            +
            path
        )

    xf = UsdGeom.Xformable(
        prim
    )

    for op in xf.GetOrderedXformOps():

        if (
            op.GetOpType()
            ==
            UsdGeom.XformOp.TypeRotateXYZ
        ):

            return op

    return xf.AddRotateXYZOp()


def leer_rotate_xyz(path):

    op = obtener_rotate_xyz_op(
        path
    )

    value = op.Get()

    if value is None:

        return np.zeros(
            3,
            dtype=np.float64
        )

    return np.array(
        [
            float(value[0]),
            float(value[1]),
            float(value[2])
        ],
        dtype=np.float64
    )


def escribir_rotate_xyz(
    path,
    xyz
):

    op = obtener_rotate_xyz_op(
        path
    )

    op.Set(
        Gf.Vec3f(
            float(xyz[0]),
            float(xyz[1]),
            float(xyz[2])
        )
    )


# ============================================================
# ROTACION BANDEJA
# ============================================================

def establecer_angulo_bandeja(
    angle_deg
):

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    prim = stage.GetPrimAtPath(
        PIVOTE_PATH
    )

    if not prim.IsValid():

        raise RuntimeError(
            "No existe: "
            +
            PIVOTE_PATH
        )

    xf = UsdGeom.Xformable(
        prim
    )

    rotate_op = None

    for op in xf.GetOrderedXformOps():

        if op.GetOpType() in (

            UsdGeom.XformOp.TypeRotateXYZ,

            UsdGeom.XformOp.TypeRotateZYX,

            UsdGeom.XformOp.TypeRotateZ

        ):

            rotate_op = op

            break

    if rotate_op is None:

        rotate_op = (
            xf.AddRotateXYZOp()
        )

    if (
        rotate_op.GetOpType()
        ==
        UsdGeom.XformOp.TypeRotateZ
    ):

        rotate_op.Set(
            float(angle_deg)
        )

    else:

        actual = rotate_op.Get()

        if actual is None:

            x = 0.0
            y = 0.0

        else:

            x = float(
                actual[0]
            )

            y = float(
                actual[1]
            )

        rotate_op.Set(

            Gf.Vec3f(

                x,

                y,

                float(
                    angle_deg
                )
            )
        )


# ============================================================
# LUCES
# ============================================================

def descubrir_luces():

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    luces = []

    for prim in stage.Traverse():

        intensity_attr = (
            prim.GetAttribute(
                "inputs:intensity"
            )
        )

        if not intensity_attr:

            continue

        try:

            value = (
                intensity_attr
                .Get()
            )

        except Exception:

            value = None

        if value is None:

            continue

        try:

            base_intensity = float(
                value
            )

        except Exception:

            continue

        path = str(
            prim.GetPath()
        )

        tipo = (
            prim.GetTypeName()
        )

        try:

            base_translate = (
                leer_translate(
                    path
                )
            )

        except Exception:

            base_translate = (
                np.zeros(
                    3,
                    dtype=np.float64
                )
            )

        try:

            base_rotate = (
                leer_rotate_xyz(
                    path
                )
            )

        except Exception:

            base_rotate = (
                np.zeros(
                    3,
                    dtype=np.float64
                )
            )

        luces.append(
            {
                "path":
                    path,

                "type":
                    tipo,

                "intensity_attr":
                    intensity_attr,

                "base_intensity":
                    base_intensity,

                "base_translate":
                    base_translate.copy(),

                "base_rotate":
                    base_rotate.copy()
            }
        )

    return luces


def restaurar_luces(
    luces
):

    for luz in luces:

        try:

            luz[
                "intensity_attr"
            ].Set(

                float(
                    luz[
                        "base_intensity"
                    ]
                )
            )

        except Exception:

            pass

        try:

            escribir_translate(

                luz[
                    "path"
                ],

                luz[
                    "base_translate"
                ]
            )

        except Exception:

            pass

        try:

            escribir_rotate_xyz(

                luz[
                    "path"
                ],

                luz[
                    "base_rotate"
                ]
            )

        except Exception:

            pass


def randomizar_luces(
    luces,
    rng
):

    factores = []

    for luz in luces:

        factor = float(

            rng.uniform(
                *LIGHT_FACTOR_RANGE
            )
        )

        factores.append(
            factor
        )

        try:

            luz[
                "intensity_attr"
            ].Set(

                float(

                    luz[
                        "base_intensity"
                    ]

                    *

                    factor
                )
            )

        except Exception:

            pass

        tipo = str(
            luz[
                "type"
            ]
        ).lower()


        # ----------------------------------------------------
        # DISTANT LIGHT
        # ----------------------------------------------------

        if "distant" in tipo:

            rot = (
                luz[
                    "base_rotate"
                ]
                .copy()
            )

            rot[0] += float(

                rng.uniform(
                    *LIGHT_PITCH_RANGE_DEG
                )
            )

            rot[2] += float(

                rng.uniform(
                    *LIGHT_YAW_RANGE_DEG
                )
            )

            try:

                escribir_rotate_xyz(

                    luz[
                        "path"
                    ],

                    rot
                )

            except Exception:

                pass


        # ----------------------------------------------------
        # LUZ FISICA
        # ----------------------------------------------------

        else:

            pos = (
                luz[
                    "base_translate"
                ]
                .copy()
            )

            pos[0] += float(

                rng.uniform(
                    *LIGHT_DX_RANGE_M
                )
            )

            pos[1] += float(

                rng.uniform(
                    *LIGHT_DY_RANGE_M
                )
            )

            pos[2] += float(

                rng.uniform(
                    *LIGHT_DZ_RANGE_M
                )
            )

            try:

                escribir_translate(

                    luz[
                        "path"
                    ],

                    pos
                )

            except Exception:

                pass

    if len(
        factores
    ) == 0:

        return 1.0

    return float(
        np.mean(
            factores
        )
    )


# ============================================================
# ROBOT
# ============================================================

def descubrir_joints_robot():

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    root = stage.GetPrimAtPath(
        ROBOT_ROOT_PATH
    )

    if not root.IsValid():

        raise RuntimeError(
            "No existe robot: "
            +
            ROBOT_ROOT_PATH
        )

    wanted = set(
        ROBOT_JOINT_NAMES
    )

    encontrados = {}

    for prim in Usd.PrimRange(
        root
    ):

        name = prim.GetName()

        if name not in wanted:

            continue

        drive_attr = None

        drive_kind = None

        for kind in (
            "linear",
            "angular"
        ):

            attr = (
                prim.GetAttribute(
                    f"drive:{kind}:physics:targetPosition"
                )
            )

            if attr:

                try:

                    if (
                        attr.Get()
                        is not None
                    ):

                        drive_attr = attr

                        drive_kind = kind

                        break

                except Exception:

                    pass

        if drive_attr is None:

            print(
                "[WARN] Joint sin drive:",
                name
            )

            continue

        lower_attr = (
            prim.GetAttribute(
                "physics:lowerLimit"
            )
        )

        upper_attr = (
            prim.GetAttribute(
                "physics:upperLimit"
            )
        )

        lower = (
            lower_attr.Get()
            if lower_attr
            else None
        )

        upper = (
            upper_attr.Get()
            if upper_attr
            else None
        )

        try:

            lower = float(
                lower
            )

            upper = float(
                upper
            )

        except Exception:

            continue

        lo = min(
            lower,
            upper
        )

        hi = max(
            lower,
            upper
        )

        try:

            current_target = float(
                drive_attr.Get()
            )

        except Exception:

            current_target = (

                0.5

                *

                (
                    lo
                    +
                    hi
                )
            )

        encontrados[
            name
        ] = {

            "drive_attr":
                drive_attr,

            "drive_kind":
                drive_kind,

            "lower":
                lo,

            "upper":
                hi,

            "fixed_target":
                current_target
        }

    return encontrados


def restaurar_robot_fijo(
    joints
):

    targets = {}

    for name, data in joints.items():

        target = float(
            data[
                "fixed_target"
            ]
        )

        try:

            data[
                "drive_attr"
            ].Set(
                target
            )

            targets[
                name
            ] = target

        except Exception:

            pass

    return targets


def randomizar_robot(
    joints,
    rng
):

    targets = {}

    for name, data in joints.items():

        lo = float(
            data[
                "lower"
            ]
        )

        hi = float(
            data[
                "upper"
            ]
        )

        span = (
            hi
            -
            lo
        )

        safe_lo = (

            lo

            +

            ROBOT_LIMIT_MARGIN

            *

            span
        )

        safe_hi = (

            hi

            -

            ROBOT_LIMIT_MARGIN

            *

            span
        )

        target = float(

            rng.uniform(
                safe_lo,
                safe_hi
            )
        )

        try:

            data[
                "drive_attr"
            ].Set(
                target
            )

            targets[
                name
            ] = target

        except Exception:

            pass

    return targets


# ============================================================
# OBJETOS SINTETICOS
# ============================================================

def limpiar_objetos():

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    root = stage.GetPrimAtPath(
        OBJECTS_ROOT_PATH
    )

    if root.IsValid():

        stage.RemovePrim(
            OBJECTS_ROOT_PATH
        )

    UsdGeom.Xform.Define(
        stage,
        OBJECTS_ROOT_PATH
    )


def punto_bandeja_a_world(
    xyz_local
):

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    prim = stage.GetPrimAtPath(
        PIVOTE_PATH
    )

    M = (

        UsdGeom.Xformable(
            prim
        )

        .ComputeLocalToWorldTransform(
            Usd.TimeCode.Default()
        )
    )

    p = Gf.Vec3d(

        float(
            xyz_local[0]
        ),

        float(
            xyz_local[1]
        ),

        float(
            xyz_local[2]
        )
    )

    pw = M.Transform(
        p
    )

    return np.array(
        [
            float(pw[0]),
            float(pw[1]),
            float(pw[2])
        ],
        dtype=np.float64
    )


def crear_objetos(
    rng
):

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    limpiar_objetos()

    cantidad = int(

        rng.integers(

            OBJECT_COUNT_MIN,

            OBJECT_COUNT_MAX
            +
            1
        )
    )

    for i in range(
        cantidad
    ):

        sx = float(
            rng.uniform(
                *OBJECT_SIZE_X_RANGE
            )
        )

        sy = float(
            rng.uniform(
                *OBJECT_SIZE_Y_RANGE
            )
        )

        sz = float(
            rng.uniform(
                *OBJECT_SIZE_Z_RANGE
            )
        )

        lx = float(
            rng.uniform(
                *OBJECT_LOCAL_X_RANGE
            )
        )

        ly = float(
            rng.uniform(
                *OBJECT_LOCAL_Y_RANGE
            )
        )

        lz = (

            TRAY_OBJECT_BASE_Z

            +

            sz
            /
            2.0
        )

        world_pos = punto_bandeja_a_world(
            (
                lx,
                ly,
                lz
            )
        )

        path = (

            OBJECTS_ROOT_PATH

            +

            f"/obj_{i:02d}"
        )

        cube = UsdGeom.Cube.Define(
            stage,
            path
        )

        cube.CreateSizeAttr(
            1.0
        )

        xf = UsdGeom.Xformable(
            cube.GetPrim()
        )

        translate = (
            xf.AddTranslateOp()
        )

        rotate = (
            xf.AddRotateZOp()
        )

        scale = (
            xf.AddScaleOp()
        )

        translate.Set(

            Gf.Vec3d(

                float(
                    world_pos[0]
                ),

                float(
                    world_pos[1]
                ),

                float(
                    world_pos[2]
                )
            )
        )

        rotate.Set(

            float(

                rng.uniform(
                    0.0,
                    180.0
                )
            )
        )

        scale.Set(

            Gf.Vec3f(
                sx,
                sy,
                sz
            )
        )

        color = (

            OBJECT_COLORS[
                int(
                    rng.integers(
                        0,
                        len(
                            OBJECT_COLORS
                        )
                    )
                )
            ]
        )

        try:

            UsdGeom.Gprim(
                cube.GetPrim()
            ).CreateDisplayColorAttr(
                [
                    Gf.Vec3f(
                        *color
                    )
                ]
            )

        except Exception:

            pass

        # Muy importante:
        # estos objetos NO son bandeja.
        try:

            add_update_semantics(
                cube.GetPrim(),
                "objeto",
                "class"
            )

        except Exception:

            pass

    return cantidad


# ============================================================
# SEMANTICA BANDEJA
# ============================================================

def aplicar_semantica_bandeja():

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    root = stage.GetPrimAtPath(
        PIVOTE_PATH
    )

    if not root.IsValid():

        raise RuntimeError(
            "No existe bandeja"
        )

    add_update_semantics(
        root,
        SEMANTIC_LABEL,
        "class"
    )

    print(
        "[OK] Semantica bandeja:",
        PIVOTE_PATH
    )


# ============================================================
# CAPTURA
# ============================================================

def extraer_rgb(data):

    if isinstance(
        data,
        dict
    ):

        rgb = np.asarray(
            data[
                "data"
            ]
        )

    else:

        rgb = np.asarray(
            data
        )

    if rgb.ndim != 3:

        return None

    if rgb.shape[2] == 4:

        rgb = rgb[
            :,
            :,
            :3
        ]

    return np.ascontiguousarray(

        rgb.astype(
            np.uint8
        )
    )


def extraer_mask_bandeja(
    semantic_data
):

    if not isinstance(
        semantic_data,
        dict
    ):

        return None

    seg = np.squeeze(

        np.asarray(
            semantic_data[
                "data"
            ]
        )
    )

    if seg.ndim != 2:

        return None

    info = semantic_data.get(
        "info",
        {}
    )

    labels = info.get(
        "idToLabels",
        {}
    )

    ids = []

    for key, value in labels.items():

        if (
            "bandeja"
            in
            str(
                value
            ).lower()
        ):

            ids.append(
                int(
                    key
                )
            )

    if len(
        ids
    ) == 0:

        print(
            "[WARN] Bandeja no aparece en idToLabels"
        )

        print(
            labels
        )

        return None

    return np.isin(
        seg,
        np.asarray(
            ids,
            dtype=seg.dtype
        )
    )


# ============================================================
# MASCARA -> YOLO
# ============================================================

def mask_a_poligono(
    mask
):

    mask_u8 = (

        mask.astype(
            np.uint8
        )

        *

        255
    )

    contours, _ = (
        cv2.findContours(

            mask_u8,

            cv2.RETR_EXTERNAL,

            cv2.CHAIN_APPROX_SIMPLE
        )
    )

    if len(
        contours
    ) == 0:

        return None

    contour = max(

        contours,

        key=cv2.contourArea
    )

    perimeter = (
        cv2.arcLength(
            contour,
            True
        )
    )

    approx = (
        cv2.approxPolyDP(

            contour,

            max(
                1.0,
                POLY_EPSILON_FACTOR
                *
                perimeter
            ),

            True
        )
    )

    pts = approx.reshape(
        -1,
        2
    )

    if len(
        pts
    ) < 3:

        return None

    h, w = mask.shape

    salida = []

    for x, y in pts:

        salida.extend(
            [
                np.clip(
                    x / w,
                    0,
                    1
                ),

                np.clip(
                    y / h,
                    0,
                    1
                )
            ]
        )

    return salida


def guardar(
    scene_id,
    rgb,
    mask
):

    name = (
        f"img_{scene_id:04d}"
    )

    img_path = os.path.join(
        IMAGES_DIR,
        name + ".png"
    )

    label_path = os.path.join(
        LABELS_DIR,
        name + ".txt"
    )

    mask_path = os.path.join(
        MASKS_DIR,
        name + ".png"
    )

    polygon = mask_a_poligono(
        mask
    )

    if polygon is None:

        return None

    Image.fromarray(
        rgb
    ).save(
        img_path
    )

    Image.fromarray(

        mask.astype(
            np.uint8
        )
        *
        255

    ).save(
        mask_path
    )

    with open(
        label_path,
        "w"
    ) as f:

        valores = " ".join(

            f"{x:.6f}"

            for x in polygon
        )

        f.write(
            f"0 {valores}\n"
        )

    return (
        img_path,
        label_path,
        mask_path
    )


# ============================================================
# CONFIGURACION POR ESCENA
# ============================================================

def configuracion_escena(
    scene_id
):

    if scene_id <= 150:

        return (
            False,
            False,
            False,
            "B1"
        )

    elif scene_id <= 250:

        return (
            True,
            False,
            False,
            "B2"
        )

    elif scene_id <= 350:

        return (
            False,
            True,
            False,
            "B3"
        )

    elif scene_id <= 450:

        return (
            True,
            True,
            False,
            "B4"
        )

    else:

        return (
            True,
            True,
            True,
            "B5"
        )


# ============================================================
# FRAMES
# ============================================================

async def avanzar_frames(
    n
):

    for _ in range(
        int(
            n
        )
    ):

        await (
            rep
            .orchestrator
            .step_async()
        )


# ============================================================
# MAIN
# ============================================================

async def main():

    print("")

    print(
        "="
        *
        90
    )

    print(
        "DATASET V2 - 500 IMAGENES"
    )

    print(
        "="
        *
        90
    )

    print(
        "1-150   bandeja"
    )

    print(
        "151-250 robot variable"
    )

    print(
        "251-350 luz variable"
    )

    print(
        "351-450 robot + luz"
    )

    print(
        "451-500 robot + luz + objetos"
    )

    rng = np.random.default_rng(
        RANDOM_SEED
    )

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    aplicar_semantica_bandeja()

    limpiar_objetos()


    # ========================================================
    # CAMARA
    # ========================================================

    camera = Camera(

        prim_path=
            CAMERA_RGB_PATH,

        resolution=(
            WIDTH,
            HEIGHT
        )
    )

    camera.initialize()

    rgb_ann = (
        rep
        .AnnotatorRegistry
        .get_annotator(
            "rgb"
        )
    )

    sem_ann = (
        rep
        .AnnotatorRegistry
        .get_annotator(

            "semantic_segmentation",

            init_params={
                "colorize":
                    False
            }
        )
    )

    rgb_ann.attach(
        [
            camera
            ._render_product_path
        ]
    )

    sem_ann.attach(
        [
            camera
            ._render_product_path
        ]
    )


    # ========================================================
    # ESTADOS BASE
    # ========================================================

    bandeja_base = leer_translate(
        PIVOTE_PATH
    )

    luces = descubrir_luces()

    joints = descubrir_joints_robot()

    print(
        "Joints:",
        list(
            joints.keys()
        )
    )

    print(
        "Luces:",
        len(
            luces
        )
    )

    restaurar_robot_fijo(
        joints
    )

    restaurar_luces(
        luces
    )

    await avanzar_frames(
        FRAMES_INICIALES
    )


    # ========================================================
    # CSV
    # ========================================================

    with open(
        META_CSV,
        "w",
        newline=""
    ) as f:

        writer = csv.writer(
            f
        )

        writer.writerow(
            [
                "scene_id",
                "bloque",
                "dx",
                "dy",
                "yaw",
                "robot_random",
                "luz_random",
                "objetos",
                "n_objetos",
                "light_factor",
                "mask_pixels"
            ]
        )


    # ========================================================
    # GENERACION
    # ========================================================

    scene_id = SCENE_START

    intentos = 0

    while (
        scene_id
        <=
        SCENE_END
    ):

        intentos += 1

        if (
            intentos
            >
            MAX_INTENTOS
        ):

            raise RuntimeError(
                "Demasiados intentos"
            )

        (
            mover_robot,
            mover_luz,
            usar_objetos,
            bloque
        ) = configuracion_escena(
            scene_id
        )


        # ====================================================
        # BANDEJA
        # ====================================================

        dx = float(
            rng.uniform(
                *DX_RANGE_M
            )
        )

        dy = float(
            rng.uniform(
                *DY_RANGE_M
            )
        )

        yaw = float(
            rng.uniform(
                *YAW_RANGE_DEG
            )
        )

        p = bandeja_base.copy()

        p[0] += dx

        p[1] += dy

        escribir_translate(
            PIVOTE_PATH,
            p
        )

        establecer_angulo_bandeja(
            yaw
        )

        await avanzar_frames(
            FRAMES_BANDEJA
        )


        # ====================================================
        # ROBOT
        # ====================================================

        if mover_robot:

            randomizar_robot(
                joints,
                rng
            )

            await avanzar_frames(
                FRAMES_ROBOT
            )

            await avanzar_frames(
                FRAMES_POST_ROBOT
            )

        else:

            restaurar_robot_fijo(
                joints
            )


        # ====================================================
        # LUZ
        # ====================================================

        if mover_luz:

            light_factor = (
                randomizar_luces(
                    luces,
                    rng
                )
            )

            await avanzar_frames(
                FRAMES_LUZ
            )

        else:

            light_factor = 1.0

            restaurar_luces(
                luces
            )


        # ====================================================
        # OBJETOS
        # ====================================================

        if usar_objetos:

            n_objetos = (
                crear_objetos(
                    rng
                )
            )

            await avanzar_frames(
                FRAMES_OBJETOS
            )

        else:

            limpiar_objetos()

            n_objetos = 0


        # ====================================================
        # CAPTURA
        # ====================================================

        await avanzar_frames(
            FRAMES_CAPTURA
        )

        rgb = extraer_rgb(
            rgb_ann.get_data()
        )

        mask = extraer_mask_bandeja(
            sem_ann.get_data()
        )

        if (
            rgb is None
            or
            mask is None
        ):

            print(
                "[REINTENTO]"
            )

            continue

        mask_pixels = int(
            np.count_nonzero(
                mask
            )
        )

        if (
            mask_pixels
            <
            MIN_MASK_PIXELS
        ):

            print(
                "[REINTENTO] mask:",
                mask_pixels
            )

            continue

        rutas = guardar(
            scene_id,
            rgb,
            mask
        )

        if rutas is None:

            continue


        # ====================================================
        # METADATA
        # ====================================================

        with open(
            META_CSV,
            "a",
            newline=""
        ) as f:

            writer = csv.writer(
                f
            )

            writer.writerow(
                [
                    scene_id,
                    bloque,
                    dx,
                    dy,
                    yaw,
                    mover_robot,
                    mover_luz,
                    usar_objetos,
                    n_objetos,
                    light_factor,
                    mask_pixels
                ]
            )


        print(

            f"[OK] "

            f"{scene_id:03d}/500"

            f" | {bloque}"

            f" | yaw={yaw:.1f}"

            f" | robot="
            f"{'MOV' if mover_robot else 'FIJO'}"

            f" | luz="
            f"{'MOV' if mover_luz else 'FIJA'}"

            f" | objetos="
            f"{n_objetos}"

            f" | mask="
            f"{mask_pixels}"
        )

        scene_id += 1


    # ========================================================
    # RESTAURAR
    # ========================================================

    limpiar_objetos()

    escribir_translate(
        PIVOTE_PATH,
        bandeja_base
    )

    restaurar_robot_fijo(
        joints
    )

    restaurar_luces(
        luces
    )

    await avanzar_frames(
        10
    )


    print("")

    print(
        "="
        *
        90
    )

    print(
        "DATASET TERMINADO"
    )

    print(
        OUTPUT_DIR
    )

    print(
        "="
        *
        90
    )


# ============================================================
# EJECUTAR
# ============================================================

asyncio.ensure_future(
    main()
)