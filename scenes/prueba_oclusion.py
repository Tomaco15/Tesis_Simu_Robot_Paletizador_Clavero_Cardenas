import os
import csv
import asyncio
import numpy as np

from PIL import Image

import omni.usd
import omni.replicator.core as rep

from pxr import Usd, UsdGeom, Gf

from isaacsim.sensors.camera import Camera
from isaacsim.core.utils.semantics import add_update_semantics


# ============================================================
# CONFIGURACION
# ============================================================

WIDTH = 640
HEIGHT = 480

CAMERA_RGB_PATH = "/World/Camera_RGB_Astra"
BANDEJA_PATH = "/World/bandeja_v2"

OCCLUDER_PATH = "/World/OcclusionTest"

OUTPUT_DIR = "/home/cristian/Desktop/prueba_oclusion_100"

IMAGES_DIR = os.path.join(
    OUTPUT_DIR,
    "images"
)

MASK_BASE_DIR = os.path.join(
    OUTPUT_DIR,
    "masks_base"
)

MASK_VISIBLE_DIR = os.path.join(
    OUTPUT_DIR,
    "masks_visible"
)

CSV_PATH = os.path.join(
    OUTPUT_DIR,
    "resultados_oclusion.csv"
)

os.makedirs(
    IMAGES_DIR,
    exist_ok=True
)

os.makedirs(
    MASK_BASE_DIR,
    exist_ok=True
)

os.makedirs(
    MASK_VISIBLE_DIR,
    exist_ok=True
)


# ============================================================
# PRUEBA
# ============================================================

OCCLUSION_LEVELS = [
    0,
    10,
    20,
    30,
    40
]

SCENES_PER_LEVEL = 20

TOTAL = (
    len(OCCLUSION_LEVELS)
    *
    SCENES_PER_LEVEL
)

RANDOM_SEED = 20261019


# ============================================================
# BANDEJA
# ============================================================

# 50 x 30 cm
TRAY_X = 0.50
TRAY_Y = 0.30

DX_RANGE = (
    -0.08,
    0.08
)

DY_RANGE = (
    -0.08,
    0.08
)

YAW_RANGE = (
    0.0,
    180.0
)


# ============================================================
# OCLUSOR
# ============================================================

# Altura aproximada sobre la bandeja.
# Si aparece flotando demasiado, bajar.
# Si queda enterrado, subir.
OCCLUDER_Z_LOCAL = 0.075

OCCLUDER_HEIGHT = 0.03

OCCLUDER_COLOR = (
    0.15,
    0.15,
    0.15
)


# ============================================================
# FRAMES
# ============================================================

FRAMES_INITIAL = 10
FRAMES_TRAY = 5
FRAMES_OCCLUDER = 5
FRAMES_CAPTURE = 3

MIN_MASK_PIXELS = 1000

SEMANTIC_LABEL = "bandeja"


# ============================================================
# TRANSFORMACIONES
# ============================================================

def get_translate_op(path):

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


def read_translate(path):

    value = (
        get_translate_op(
            path
        ).Get()
    )

    return np.array(
        [
            float(value[0]),
            float(value[1]),
            float(value[2])
        ],
        dtype=np.float64
    )


def write_translate(
    path,
    xyz
):

    op = get_translate_op(
        path
    )

    op.Set(
        Gf.Vec3d(
            float(xyz[0]),
            float(xyz[1]),
            float(xyz[2])
        )
    )


def set_yaw(
    path,
    angle
):

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    prim = stage.GetPrimAtPath(
        path
    )

    xf = UsdGeom.Xformable(
        prim
    )

    rotate_op = None

    for op in xf.GetOrderedXformOps():

        if op.GetOpType() in (

            UsdGeom.XformOp.TypeRotateXYZ,
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
            float(angle)
        )

    else:

        actual = rotate_op.Get()

        if actual is None:

            rx = 0
            ry = 0

        else:

            rx = float(
                actual[0]
            )

            ry = float(
                actual[1]
            )

        rotate_op.Set(
            Gf.Vec3f(
                rx,
                ry,
                float(angle)
            )
        )


# ============================================================
# LOCAL BANDEJA -> WORLD
# ============================================================

def tray_local_to_world(
    x,
    y,
    z
):

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    prim = stage.GetPrimAtPath(
        BANDEJA_PATH
    )

    matrix = (

        UsdGeom.Xformable(
            prim
        )

        .ComputeLocalToWorldTransform(
            Usd.TimeCode.Default()
        )
    )

    p = matrix.Transform(

        Gf.Vec3d(
            float(x),
            float(y),
            float(z)
        )
    )

    return np.array(
        [
            float(p[0]),
            float(p[1]),
            float(p[2])
        ]
    )


# ============================================================
# SEMANTICA
# ============================================================

def apply_semantics():

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    prim = stage.GetPrimAtPath(
        BANDEJA_PATH
    )

    add_update_semantics(
        prim,
        SEMANTIC_LABEL,
        "class"
    )

    print(
        "[OK] Semantica aplicada:",
        BANDEJA_PATH
    )


# ============================================================
# OCLUSOR
# ============================================================

def remove_occluder():

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )

    prim = stage.GetPrimAtPath(
        OCCLUDER_PATH
    )

    if prim.IsValid():

        stage.RemovePrim(
            OCCLUDER_PATH
        )


def create_occluder(
    target_percent,
    rng
):

    remove_occluder()

    if target_percent == 0:

        return {
            "width": 0,
            "length": 0
        }

    stage = (
        omni.usd
        .get_context()
        .get_stage()
    )


    # ========================================================
    # AREA OBJETIVO
    # ========================================================

    tray_area = (
        TRAY_X
        *
        TRAY_Y
    )

    target_area = (

        tray_area

        *

        (
            target_percent
            /
            100.0
        )
    )


    # Proporcion aleatoria
    aspect = float(

        rng.uniform(
            0.70,
            1.40
        )
    )


    occ_x = np.sqrt(

        target_area

        *

        aspect
    )

    occ_y = (

        target_area

        /

        occ_x
    )


    occ_x = float(

        np.clip(
            occ_x,
            0.03,
            TRAY_X * 0.85
        )
    )


    occ_y = float(

        np.clip(
            occ_y,
            0.03,
            TRAY_Y * 0.85
        )
    )


    # ========================================================
    # POSICION DENTRO DE BANDEJA
    # ========================================================

    max_x = (

        (
            TRAY_X
            -
            occ_x
        )
        /
        2
        -
        0.01
    )

    max_y = (

        (
            TRAY_Y
            -
            occ_y
        )
        /
        2
        -
        0.01
    )


    local_x = float(

        rng.uniform(
            -max_x,
            max_x
        )
    )


    local_y = float(

        rng.uniform(
            -max_y,
            max_y
        )
    )


    world = tray_local_to_world(

        local_x,
        local_y,
        OCCLUDER_Z_LOCAL
    )


    # ========================================================
    # CREAR CUBO
    # ========================================================

    cube = UsdGeom.Cube.Define(

        stage,

        OCCLUDER_PATH
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

    scale = (
        xf.AddScaleOp()
    )


    translate.Set(

        Gf.Vec3d(
            float(world[0]),
            float(world[1]),
            float(world[2])
        )
    )


    scale.Set(

        Gf.Vec3f(
            float(occ_x),
            float(occ_y),
            float(OCCLUDER_HEIGHT)
        )
    )


    UsdGeom.Gprim(
        cube.GetPrim()
    ).CreateDisplayColorAttr(

        [
            Gf.Vec3f(
                *OCCLUDER_COLOR
            )
        ]
    )


    add_update_semantics(

        cube.GetPrim(),

        "occluder",

        "class"
    )


    return {

        "width":
            occ_x,

        "length":
            occ_y
    }


# ============================================================
# RGB
# ============================================================

def extract_rgb(
    data
):

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


# ============================================================
# MASK BANDEJA
# ============================================================

def extract_mask(
    data
):

    if not isinstance(
        data,
        dict
    ):

        return None


    seg = np.squeeze(

        np.asarray(
            data[
                "data"
            ]
        )
    )


    labels = (

        data
        .get(
            "info",
            {}
        )
        .get(
            "idToLabels",
            {}
        )
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
            "[WARN] No encontre bandeja:",
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
# FRAMES
# ============================================================

async def frames(
    n
):

    for _ in range(
        n
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
        80
    )

    print(
        "PRUEBA DE OCLUSION"
    )

    print(
        "="
        *
        80
    )


    rng = np.random.default_rng(
        RANDOM_SEED
    )


    apply_semantics()

    remove_occluder()


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


    await frames(
        FRAMES_INITIAL
    )


    tray_base = read_translate(
        BANDEJA_PATH
    )


    # ========================================================
    # CSV
    # ========================================================

    with open(
        CSV_PATH,
        "w",
        newline=""
    ) as f:

        writer = csv.writer(
            f
        )

        writer.writerow(
            [
                "scene",
                "target_occlusion",
                "measured_occlusion",
                "dx",
                "dy",
                "yaw",
                "base_pixels",
                "visible_pixels"
            ]
        )


    scene = 1


    # ========================================================
    # NIVELES
    # ========================================================

    for level in OCCLUSION_LEVELS:


        print("")

        print(
            "NIVEL:",
            level,
            "%"
        )


        for _ in range(
            SCENES_PER_LEVEL
        ):


            # =================================================
            # BANDEJA
            # =================================================

            dx = float(
                rng.uniform(
                    *DX_RANGE
                )
            )

            dy = float(
                rng.uniform(
                    *DY_RANGE
                )
            )

            yaw = float(
                rng.uniform(
                    *YAW_RANGE
                )
            )


            pos = tray_base.copy()

            pos[0] += dx

            pos[1] += dy


            write_translate(
                BANDEJA_PATH,
                pos
            )


            set_yaw(
                BANDEJA_PATH,
                yaw
            )


            remove_occluder()


            await frames(
                FRAMES_TRAY
            )


            # =================================================
            # MASK COMPLETA
            # =================================================

            base_mask = extract_mask(

                sem_ann
                .get_data()
            )


            if base_mask is None:

                continue


            base_pixels = int(

                np.count_nonzero(
                    base_mask
                )
            )


            if (
                base_pixels
                <
                MIN_MASK_PIXELS
            ):

                continue


            # =================================================
            # OCLUSOR
            # =================================================

            create_occluder(
                level,
                rng
            )


            await frames(
                FRAMES_OCCLUDER
            )


            # =================================================
            # CAPTURA FINAL
            # =================================================

            rgb = extract_rgb(

                rgb_ann
                .get_data()
            )


            visible_mask = extract_mask(

                sem_ann
                .get_data()
            )


            if (
                rgb is None
                or
                visible_mask is None
            ):

                continue


            visible_pixels = int(

                np.count_nonzero(
                    visible_mask
                )
            )


            occluded_pixels = max(

                0,

                base_pixels
                -
                visible_pixels
            )


            measured = (

                100.0

                *

                occluded_pixels

                /

                base_pixels
            )


            # =================================================
            # GUARDAR
            # =================================================

            name = (
                f"img_{scene:04d}"
            )


            Image.fromarray(
                rgb
            ).save(

                os.path.join(

                    IMAGES_DIR,

                    name + ".png"
                )
            )


            Image.fromarray(

                base_mask.astype(
                    np.uint8
                )

                *
                255

            ).save(

                os.path.join(

                    MASK_BASE_DIR,

                    name + ".png"
                )
            )


            Image.fromarray(

                visible_mask.astype(
                    np.uint8
                )

                *
                255

            ).save(

                os.path.join(

                    MASK_VISIBLE_DIR,

                    name + ".png"
                )
            )


            with open(
                CSV_PATH,
                "a",
                newline=""
            ) as f:

                writer = csv.writer(
                    f
                )

                writer.writerow(
                    [
                        scene,
                        level,
                        measured,
                        dx,
                        dy,
                        yaw,
                        base_pixels,
                        visible_pixels
                    ]
                )


            print(

                f"[OK] "

                f"{scene:03d}/{TOTAL}"

                f" | objetivo="
                f"{level}%"

                f" | medido="
                f"{measured:.2f}%"

                f" | yaw="
                f"{yaw:.1f}"
            )


            scene += 1


    # ========================================================
    # RESTAURAR
    # ========================================================

    remove_occluder()


    write_translate(
        BANDEJA_PATH,
        tray_base
    )


    set_yaw(
        BANDEJA_PATH,
        0
    )


    await frames(
        10
    )


    print("")

    print(
        "="
        *
        80
    )

    print(
        "PRUEBA TERMINADA"
    )

    print(
        "CSV:",
        CSV_PATH
    )

    print(
        "="
        *
        80
    )


asyncio.ensure_future(
    main()
)