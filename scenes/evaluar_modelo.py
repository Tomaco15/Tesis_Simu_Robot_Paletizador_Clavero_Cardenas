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

OUTPUT_DIR = "/home/cristian/Desktop/prueba_oclusion_pareada_100"

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
    "resultados_oclusion_pareada.csv"
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
# EXPERIMENTO
# ============================================================

OCCLUSION_LEVELS = [
    0,
    10,
    20,
    30,
    40
]

NUM_POSES = 20

TOTAL_SCENES = (
    NUM_POSES
    *
    len(OCCLUSION_LEVELS)
)

RANDOM_SEED = 20261019


# ============================================================
# BANDEJA
# ============================================================

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

    stage = omni.usd.get_context().get_stage()

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

    value = get_translate_op(
        path
    ).Get()

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

    if (
        op.GetPrecision()
        ==
        UsdGeom.XformOp.PrecisionDouble
    ):

        op.Set(
            Gf.Vec3d(
                float(xyz[0]),
                float(xyz[1]),
                float(xyz[2])
            )
        )

    else:

        op.Set(
            Gf.Vec3f(
                float(xyz[0]),
                float(xyz[1]),
                float(xyz[2])
            )
        )


def get_rotate_op(path):

    stage = omni.usd.get_context().get_stage()

    prim = stage.GetPrimAtPath(
        path
    )

    xf = UsdGeom.Xformable(
        prim
    )

    for op in xf.GetOrderedXformOps():

        if op.GetOpType() in (
            UsdGeom.XformOp.TypeRotateXYZ,
            UsdGeom.XformOp.TypeRotateZ
        ):

            return op

    return xf.AddRotateXYZOp()


def read_rotation(path):

    op = get_rotate_op(
        path
    )

    value = op.Get()

    if value is None:

        return (
            0.0,
            0.0,
            0.0
        )

    if (
        op.GetOpType()
        ==
        UsdGeom.XformOp.TypeRotateZ
    ):

        return (
            0.0,
            0.0,
            float(value)
        )

    return (
        float(value[0]),
        float(value[1]),
        float(value[2])
    )


def set_yaw(
    path,
    angle
):

    op = get_rotate_op(
        path
    )

    if (
        op.GetOpType()
        ==
        UsdGeom.XformOp.TypeRotateZ
    ):

        op.Set(
            float(angle)
        )

    else:

        actual = op.Get()

        if actual is None:

            rx = 0.0
            ry = 0.0

        else:

            rx = float(
                actual[0]
            )

            ry = float(
                actual[1]
            )

        op.Set(
            Gf.Vec3f(
                rx,
                ry,
                float(angle)
            )
        )


def restore_rotation(
    path,
    rotation
):

    op = get_rotate_op(
        path
    )

    if (
        op.GetOpType()
        ==
        UsdGeom.XformOp.TypeRotateZ
    ):

        op.Set(
            float(rotation[2])
        )

    else:

        op.Set(
            Gf.Vec3f(
                float(rotation[0]),
                float(rotation[1]),
                float(rotation[2])
            )
        )


# ============================================================
# BANDEJA LOCAL -> WORLD
# ============================================================

def tray_local_to_world(
    x,
    y,
    z
):

    stage = omni.usd.get_context().get_stage()

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
        ],
        dtype=np.float64
    )


# ============================================================
# SEMANTICA
# ============================================================

def apply_semantics():

    stage = omni.usd.get_context().get_stage()

    prim = stage.GetPrimAtPath(
        BANDEJA_PATH
    )

    if not prim.IsValid():

        raise RuntimeError(
            "No existe bandeja: "
            +
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

    stage = omni.usd.get_context().get_stage()

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

    if target_percent <= 0:

        return {
            "occ_x_m": 0.0,
            "occ_y_m": 0.0,
            "local_x_m": 0.0,
            "local_y_m": 0.0
        }


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


    max_x = max(
        0.0,
        (
            TRAY_X
            -
            occ_x
        )
        /
        2.0
        -
        0.01
    )


    max_y = max(
        0.0,
        (
            TRAY_Y
            -
            occ_y
        )
        /
        2.0
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


    stage = omni.usd.get_context().get_stage()

    cube = UsdGeom.Cube.Define(
        stage,
        OCCLUDER_PATH
    )

    cube.CreateSizeAttr(
        1.0
    )


    prim = cube.GetPrim()

    xf = UsdGeom.Xformable(
        prim
    )


    translate_op = xf.AddTranslateOp()
    scale_op = xf.AddScaleOp()


    translate_op.Set(
        Gf.Vec3d(
            float(world[0]),
            float(world[1]),
            float(world[2])
        )
    )


    scale_op.Set(
        Gf.Vec3f(
            float(occ_x),
            float(occ_y),
            float(OCCLUDER_HEIGHT)
        )
    )


    UsdGeom.Gprim(
        prim
    ).CreateDisplayColorAttr(
        [
            Gf.Vec3f(
                float(OCCLUDER_COLOR[0]),
                float(OCCLUDER_COLOR[1]),
                float(OCCLUDER_COLOR[2])
            )
        ]
    )


    add_update_semantics(
        prim,
        "occluder",
        "class"
    )


    return {
        "occ_x_m": occ_x,
        "occ_y_m": occ_y,
        "local_x_m": local_x,
        "local_y_m": local_y
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
            data["data"]
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


    if "data" not in data:

        return None


    seg = np.squeeze(
        np.asarray(
            data["data"]
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
            SEMANTIC_LABEL.lower()
            in
            str(value).lower()
        ):

            try:

                ids.append(
                    int(key)
                )

            except Exception:

                pass


    if len(ids) == 0:

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
        int(n)
    ):

        await rep.orchestrator.step_async()


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
        "PRUEBA DE OCLUSION PAREADA"
    )

    print(
        "="
        *
        90
    )

    print(
        "Poses:",
        NUM_POSES
    )

    print(
        "Niveles:",
        OCCLUSION_LEVELS
    )

    print(
        "Total:",
        TOTAL_SCENES
    )

    print(
        "Salida:",
        OUTPUT_DIR
    )

    print(
        "="
        *
        90
    )


    rng = np.random.default_rng(
        RANDOM_SEED
    )


    stage = omni.usd.get_context().get_stage()


    if stage is None:

        raise RuntimeError(
            "No hay Stage abierto."
        )


    for path in (
        CAMERA_RGB_PATH,
        BANDEJA_PATH
    ):

        if not stage.GetPrimAtPath(
            path
        ).IsValid():

            raise RuntimeError(
                "No existe: "
                +
                path
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

    tray_rotation_base = read_rotation(
        BANDEJA_PATH
    )


    # ========================================================
    # GENERAR 20 POSES BASE
    # ========================================================

    poses = []


    for pose_id in range(
        1,
        NUM_POSES + 1
    ):

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

        poses.append(
            {
                "pose_id":
                    pose_id,
                "dx":
                    dx,
                "dy":
                    dy,
                "yaw":
                    yaw
            }
        )


    # ========================================================
    # CSV
    # ========================================================

    with open(
        CSV_PATH,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.writer(
            f
        )

        writer.writerow(
            [
                "scene",
                "pose_id",
                "target_occlusion",
                "measured_occlusion",
                "dx",
                "dy",
                "yaw",
                "base_pixels",
                "visible_pixels",
                "occluded_pixels",
                "occ_x_m",
                "occ_y_m",
                "occ_local_x_m",
                "occ_local_y_m"
            ]
        )


    scene = 1


    # ========================================================
    # BUCLE PAREADO
    # ========================================================

    for pose in poses:


        pose_id = pose["pose_id"]
        dx = pose["dx"]
        dy = pose["dy"]
        yaw = pose["yaw"]


        print("")

        print(
            "#" * 90
        )

        print(
            f"POSE {pose_id:02d}/{NUM_POSES}"
            f" | dx={dx:.3f}"
            f" | dy={dy:.3f}"
            f" | yaw={yaw:.2f}"
        )

        print(
            "#" * 90
        )


        # ====================================================
        # APLICAR ESTA POSE UNA SOLA VEZ
        # ====================================================

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


        # ====================================================
        # MASCARA BASE SIN OCLUSION
        # ====================================================

        await frames(
            FRAMES_CAPTURE
        )


        base_mask = extract_mask(
            sem_ann.get_data()
        )


        if base_mask is None:

            print(
                "[ERROR] No se pudo obtener base_mask."
            )

            continue


        base_pixels = int(
            np.count_nonzero(
                base_mask
            )
        )


        if base_pixels < MIN_MASK_PIXELS:

            print(
                "[ERROR] Mascara base demasiado pequena:",
                base_pixels
            )

            continue


        # ====================================================
        # LOS 5 NIVELES SOBRE EXACTAMENTE LA MISMA POSE
        # ====================================================

        for level in OCCLUSION_LEVELS:


            remove_occluder()


            # Para que el oclusor sea reproducible dentro
            # de la pose y el nivel.
            local_seed = (
                RANDOM_SEED
                +
                pose_id * 100
                +
                level
            )

            local_rng = np.random.default_rng(
                local_seed
            )


            occ_data = create_occluder(
                level,
                local_rng
            )


            await frames(
                FRAMES_OCCLUDER
            )


            await frames(
                FRAMES_CAPTURE
            )


            rgb = extract_rgb(
                rgb_ann.get_data()
            )


            visible_mask = extract_mask(
                sem_ann.get_data()
            )


            if (
                rgb is None
                or
                visible_mask is None
            ):

                print(
                    "[WARN] Captura invalida"
                )

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
            # NOMBRE
            # =================================================

            name = (
                f"pose_{pose_id:02d}"
                f"_occ_{level:02d}"
            )


            image_path = os.path.join(
                IMAGES_DIR,
                name + ".png"
            )


            base_mask_path = os.path.join(
                MASK_BASE_DIR,
                name + ".png"
            )


            visible_mask_path = os.path.join(
                MASK_VISIBLE_DIR,
                name + ".png"
            )


            # =================================================
            # GUARDAR
            # =================================================

            Image.fromarray(
                rgb
            ).save(
                image_path
            )


            Image.fromarray(
                base_mask.astype(
                    np.uint8
                )
                *
                255
            ).save(
                base_mask_path
            )


            Image.fromarray(
                visible_mask.astype(
                    np.uint8
                )
                *
                255
            ).save(
                visible_mask_path
            )


            with open(
                CSV_PATH,
                "a",
                newline="",
                encoding="utf-8"
            ) as f:

                writer = csv.writer(
                    f
                )

                writer.writerow(
                    [
                        scene,
                        pose_id,
                        level,
                        measured,
                        dx,
                        dy,
                        yaw,
                        base_pixels,
                        visible_pixels,
                        occluded_pixels,
                        occ_data["occ_x_m"],
                        occ_data["occ_y_m"],
                        occ_data["local_x_m"],
                        occ_data["local_y_m"]
                    ]
                )


            print(
                f"[OK] "
                f"{scene:03d}/{TOTAL_SCENES}"
                f" | pose={pose_id:02d}"
                f" | objetivo={level:2d}%"
                f" | medido={measured:6.2f}%"
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


    restore_rotation(
        BANDEJA_PATH,
        tray_rotation_base
    )


    await frames(
        FRAMES_INITIAL
    )


    print("")

    print(
        "="
        *
        90
    )

    print(
        "PRUEBA PAREADA TERMINADA"
    )

    print(
        "CSV:",
        CSV_PATH
    )

    print(
        "Imagenes:",
        IMAGES_DIR
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