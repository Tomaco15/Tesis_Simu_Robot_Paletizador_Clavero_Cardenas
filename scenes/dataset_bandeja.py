
import os
import csv
import asyncio
from collections import Counter

import numpy as np
from PIL import Image

import omni.usd
import omni.replicator.core as rep

from pxr import Usd, UsdGeom, Gf
from isaacsim.core.utils.semantics import add_update_semantics


# ============================================================
# CONFIGURACION GENERAL
# ============================================================

CAMERA_PATH = "/World/Camera_RGB_Astra"
TRAY_PATH = "/World/bandeja_v2"
ROBOT_PATH = "/World/robot_ensamble"

OUTPUT_DIR = (
    "/home/cristian/Desktop/"
    "dataset_bandeja_sola_600"
)

WIDTH = 640
HEIGHT = 480

N_IMAGES = 600
MAX_ATTEMPTS = 15000

SEED = 20261021


# ============================================================
# DISTRIBUCION POR DISTANCIA
# ============================================================

DISTANCE_GROUPS = [
    ("cerca", 180),
    ("media", 240),
    ("lejos", 180)
]

DISTANCE_FACTORS = {
    "cerca": (0.65, 0.85),
    "media": (0.90, 1.10),
    "lejos": (1.20, 1.50)
}

# Comprobar que los grupos sumen 600
assert sum(
    count for _, count in DISTANCE_GROUPS
) == N_IMAGES, (
    "ERROR: DISTANCE_GROUPS no suma N_IMAGES"
)


# ============================================================
# DESPLAZAMIENTOS
# ============================================================

DX_RANGE = (-0.35, 0.35)
DY_RANGE = (-0.35, 0.35)

# Mantener la altura anterior
DZ_RANGE = (0.05, 0.30)


# ============================================================
# ROTACIONES
# ============================================================

ROLL_RANGE = (-60.0, 60.0)
PITCH_RANGE = (-60.0, 60.0)
YAW_RANGE = (0.0, 360.0)


# ============================================================
# VALIDACION
# ============================================================

MIN_MASK_PIXELS = 1000
MAX_BORDER_FRACTION = 0.04

SEMANTIC_LABEL = "bandeja"


# ============================================================
# CALIDAD DE CAPTURA
# ============================================================

DELAY_SECONDS = 1.0
SETTLE_SUBFRAMES = 8


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def get_required_prim(stage, path):

    prim = stage.GetPrimAtPath(path)

    if not prim.IsValid():
        raise RuntimeError(
            "No existe el prim: " + path
        )

    return prim


def vec_to_numpy(v):

    return np.array(
        [float(v[0]), float(v[1]), float(v[2])],
        dtype=np.float64
    )


def to_gf_vec(v):

    return Gf.Vec3d(
        float(v[0]),
        float(v[1]),
        float(v[2])
    )


def extract_rgb(payload):

    if isinstance(payload, dict):
        arr = np.asarray(payload.get("data"))
    else:
        arr = np.asarray(payload)

    if arr.ndim != 3:
        return None

    if arr.shape[:2] != (HEIGHT, WIDTH):
        return None

    if arr.shape[2] < 3:
        return None

    return np.asarray(
        arr[:, :, :3],
        dtype=np.uint8
    ).copy()


def extract_mask(payload):

    if not isinstance(payload, dict):
        return None

    if "data" not in payload:
        return None

    seg = np.squeeze(
        np.asarray(payload["data"])
    )

    if seg.shape != (HEIGHT, WIDTH):
        return None

    labels = (
        payload
        .get("info", {})
        .get("idToLabels", {})
    )

    ids = []

    for key, val in labels.items():

        if isinstance(val, dict):
            label = val.get("class", "")
        else:
            label = str(val)

        if SEMANTIC_LABEL.lower() == str(label).lower():

            try:
                ids.append(int(key))
            except (TypeError, ValueError):
                pass

    if not ids:
        return None

    return np.isin(
        seg,
        np.asarray(ids, dtype=seg.dtype)
    )


def border_fraction(mask):

    edge = np.zeros(
        mask.shape,
        dtype=bool
    )

    edge[:2, :] = True
    edge[-2:, :] = True
    edge[:, :2] = True
    edge[:, -2:] = True

    total = max(
        1,
        np.count_nonzero(mask)
    )

    return float(
        np.count_nonzero(mask & edge) / total
    )


def distance_3d(a, b):

    return float(
        np.linalg.norm(
            np.asarray(a) - np.asarray(b)
        )
    )


# ============================================================
# GENERADOR PRINCIPAL
# ============================================================

async def generar():

    stage = omni.usd.get_context().get_stage()

    if stage is None:
        raise RuntimeError(
            "Abre la escena USD antes de ejecutar."
        )

    camera = get_required_prim(
        stage,
        CAMERA_PATH
    )

    if not camera.IsA(UsdGeom.Camera):
        raise RuntimeError(
            "El prim de camara no es UsdGeom.Camera"
        )

    tray = get_required_prim(
        stage,
        TRAY_PATH
    )

    robot = stage.GetPrimAtPath(
        ROBOT_PATH
    )

    # ========================================================
    # CARPETAS
    # ========================================================

    out_rgb = os.path.join(
        OUTPUT_DIR,
        "images"
    )

    out_mask = os.path.join(
        OUTPUT_DIR,
        "masks_visible"
    )

    out_preview = os.path.join(
        OUTPUT_DIR,
        "previews"
    )

    for folder in (
        out_rgb,
        out_mask,
        out_preview
    ):
        os.makedirs(
            folder,
            exist_ok=True
        )

    csv_path = os.path.join(
        OUTPUT_DIR,
        "metadata.csv"
    )

    rng = np.random.default_rng(SEED)

    # ========================================================
    # POSICION REAL DE CAMARA
    # ========================================================

    camera_xf = UsdGeom.Xformable(camera)

    camera_world_matrix = (
        camera_xf.ComputeLocalToWorldTransform(
            Usd.TimeCode.Default()
        )
    )

    camera_world_pos = vec_to_numpy(
        camera_world_matrix.ExtractTranslation()
    )

    print(
        "[CAMARA] Posicion global:",
        camera_world_pos
    )

    # ========================================================
    # TRANSFORMACIONES DE BANDEJA
    # ========================================================

    xf = UsdGeom.Xformable(tray)

    original_ops = list(
        xf.GetOrderedXformOps()
    )

    original_values = [
        (op, op.Get())
        for op in original_ops
    ]

    original_names = [
        op.GetName()
        for op in original_ops
    ]

    translate_op = next(
        (
            op for op in original_ops
            if op.GetOpType()
            == UsdGeom.XformOp.TypeTranslate
        ),
        None
    )

    if translate_op is None:

        translate_op = xf.AddTranslateOp(
            opSuffix="datasetPose"
        )

        base_xyz = np.zeros(3)

    else:

        base_xyz = vec_to_numpy(
            translate_op.Get()
        )

    rotate_op = next(
        (
            op for op in original_ops
            if op.GetOpType()
            == UsdGeom.XformOp.TypeRotateXYZ
        ),
        None
    )

    if rotate_op is None:

        rotate_op = xf.AddRotateXYZOp(
            opSuffix="datasetPose"
        )

        base_rpy = np.zeros(3)

    else:

        base_rpy = vec_to_numpy(
            rotate_op.Get()
        )

    # ========================================================
    # TRANSFORMACION PADRE / MUNDO
    # ========================================================

    cache = UsdGeom.XformCache(
        Usd.TimeCode.Default()
    )

    parent_to_world = (
        cache.GetParentToWorldTransform(tray)
    )

    world_to_parent = (
        parent_to_world.GetInverse()
    )

    tray_base_world = vec_to_numpy(
        parent_to_world.Transform(
            to_gf_vec(base_xyz)
        )
    )

    base_distance = distance_3d(
        tray_base_world,
        camera_world_pos
    )

    print(
        "[BANDEJA] Posicion base:",
        tray_base_world
    )

    print(
        "[DISTANCIA ORIGINAL]",
        round(base_distance, 3)
    )

    # ========================================================
    # ROBOT
    # ========================================================

    robot_img = None
    old_robot_visibility = None

    if (
        robot.IsValid()
        and robot.IsA(UsdGeom.Imageable)
    ):

        robot_img = UsdGeom.Imageable(robot)

        old_robot_visibility = (
            robot_img.GetVisibilityAttr().Get()
        )

    rgb_ann = None
    seg_ann = None
    render_product = None

    attempts = 0
    saved = 0

    rejected = Counter()

    try:

        if robot_img is not None:
            robot_img.MakeInvisible()

        # ====================================================
        # SEMANTICA
        # ====================================================

        add_update_semantics(
            tray,
            SEMANTIC_LABEL,
            "class"
        )

        # ====================================================
        # RENDER PRODUCT
        # ====================================================

        render_product = rep.create.render_product(
            CAMERA_PATH,
            (WIDTH, HEIGHT)
        )

        rgb_ann = (
            rep.AnnotatorRegistry
            .get_annotator("rgb")
        )

        seg_ann = (
            rep.AnnotatorRegistry
            .get_annotator(
                "semantic_segmentation",
                init_params={
                    "colorize": False,
                    "semanticTypes": ["class"]
                }
            )
        )

        rgb_ann.attach(
            [render_product]
        )

        seg_ann.attach(
            [render_product]
        )

        rep.orchestrator.set_capture_on_play(False)

        await rep.orchestrator.step_async(
            rt_subframes=SETTLE_SUBFRAMES,
            delta_time=0.0
        )

        # ====================================================
        # CSV
        # ====================================================

        with open(
            csv_path,
            "w",
            newline=""
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                "image",
                "distance_group",
                "distance_factor",
                "distance_world",
                "x_local_op",
                "y_local_op",
                "z_local_op",
                "x_world_approx",
                "y_world_approx",
                "z_world_approx",
                "roll_op_deg",
                "pitch_op_deg",
                "yaw_op_deg",
                "mask_pixels",
                "border_fraction",
                "attempt"
            ])

            # =================================================
            # GENERAR 600 IMAGENES
            # =================================================

            for group_name, group_count in DISTANCE_GROUPS:

                group_saved = 0

                factor_range = DISTANCE_FACTORS[
                    group_name
                ]

                print("\n" + "=" * 60)

                print(
                    "GRUPO:",
                    group_name.upper()
                )

                print(
                    "OBJETIVO:",
                    group_count,
                    "imagenes"
                )

                print("=" * 60)

                while (
                    group_saved < group_count
                    and attempts < MAX_ATTEMPTS
                ):

                    attempts += 1

                    # =========================================
                    # DISTANCIA ALEATORIA
                    # =========================================

                    factor = float(
                        rng.uniform(*factor_range)
                    )

                    target_world = (
                        camera_world_pos
                        +
                        factor * (
                            tray_base_world
                            -
                            camera_world_pos
                        )
                    )

                    # =========================================
                    # DESPLAZAMIENTO LATERAL
                    # =========================================

                    dx = float(
                        rng.uniform(*DX_RANGE)
                    )

                    dy = float(
                        rng.uniform(*DY_RANGE)
                    )

                    target_world[0] += dx
                    target_world[1] += dy

                    # =========================================
                    # COORDENADAS LOCALES
                    # =========================================

                    target_local = vec_to_numpy(
                        world_to_parent.Transform(
                            to_gf_vec(target_world)
                        )
                    )

                    dz = float(
                        np.clip(
                            target_local[2] - base_xyz[2],
                            DZ_RANGE[0],
                            DZ_RANGE[1]
                        )
                    )

                    xyz = target_local.copy()

                    xyz[2] = base_xyz[2] + dz

                    # =========================================
                    # ROTACIONES
                    # =========================================

                    rpy = base_rpy + np.array([
                        rng.uniform(*ROLL_RANGE),
                        rng.uniform(*PITCH_RANGE),
                        rng.uniform(*YAW_RANGE)
                    ])

                    translate_op.Set(
                        Gf.Vec3d(
                            *map(float, xyz)
                        )
                    )

                    rotate_op.Set(
                        Gf.Vec3f(
                            *map(float, rpy)
                        )
                    )

                    # =========================================
                    # DISTANCIA RESULTANTE
                    # =========================================

                    actual_world = vec_to_numpy(
                        parent_to_world.Transform(
                            to_gf_vec(xyz)
                        )
                    )

                    distance = distance_3d(
                        camera_world_pos,
                        actual_world
                    )

                    # =========================================
                    # ESTABILIZACION DEL RENDER
                    # =========================================

                    await rep.orchestrator.step_async(
                        rt_subframes=SETTLE_SUBFRAMES,
                        delta_time=0.0
                    )

                    # Esperar 1 segundo
                    await asyncio.sleep(
                        DELAY_SECONDS
                    )

                    # Segundo render
                    await rep.orchestrator.step_async(
                        rt_subframes=SETTLE_SUBFRAMES,
                        delta_time=0.0
                    )

                    # =========================================
                    # CAPTURAR
                    # =========================================

                    rgb = extract_rgb(
                        rgb_ann.get_data()
                    )

                    mask = extract_mask(
                        seg_ann.get_data()
                    )

                    if rgb is None:
                        rejected["rgb_invalido"] += 1
                        continue

                    if mask is None:
                        rejected["sin_mascara"] += 1
                        continue

                    # =========================================
                    # VISIBILIDAD
                    # =========================================

                    mask_pixels = int(
                        np.count_nonzero(mask)
                    )

                    if mask_pixels < MIN_MASK_PIXELS:

                        rejected["pocos_pixeles"] += 1
                        continue

                    edge_frac = border_fraction(mask)

                    if edge_frac > MAX_BORDER_FRACTION:

                        rejected["recortada"] += 1
                        continue

                    # =========================================
                    # GUARDAR IMAGENES
                    # =========================================

                    saved += 1
                    group_saved += 1

                    name = f"img_{saved:04d}.png"

                    Image.fromarray(
                        rgb
                    ).save(
                        os.path.join(
                            out_rgb,
                            name
                        )
                    )

                    mask_image = (
                        mask.astype(np.uint8) * 255
                    )

                    Image.fromarray(
                        mask_image
                    ).save(
                        os.path.join(
                            out_mask,
                            name
                        )
                    )

                    # =========================================
                    # PREVIEW
                    # =========================================

                    overlay = rgb.copy()

                    overlay[mask] = (
                        0.55 * rgb[mask]
                        +
                        0.45 * np.array([255, 0, 0])
                    ).astype(np.uint8)

                    Image.fromarray(
                        overlay
                    ).save(
                        os.path.join(
                            out_preview,
                            name
                        )
                    )

                    # =========================================
                    # METADATOS
                    # =========================================

                    writer.writerow([
                        name,
                        group_name,
                        factor,
                        distance,
                        *map(float, xyz),
                        *map(float, actual_world),
                        *map(float, rpy),
                        mask_pixels,
                        round(edge_frac, 6),
                        attempts
                    ])

                    f.flush()

                    print(
                        f"[GUARDADA] {saved:03d}/{N_IMAGES}"
                        f" | grupo={group_name}"
                        f" | distancia={distance:.3f}"
                        f" | pixeles={mask_pixels}"
                        f" | roll={rpy[0]:.1f}"
                        f" | pitch={rpy[1]:.1f}"
                        f" | yaw={rpy[2]:.1f}"
                    )

                if group_saved < group_count:

                    print(
                        "[AVISO] Grupo incompleto:",
                        group_name
                    )

                if attempts >= MAX_ATTEMPTS:
                    break

        # ====================================================
        # RESUMEN FINAL
        # ====================================================

        print("\n" + "=" * 60)

        print("DATASET FINALIZADO")

        print(
            "Imagenes guardadas:",
            saved,
            "/",
            N_IMAGES
        )

        print(
            "Intentos totales:",
            attempts
        )

        print(
            "Descartes:",
            dict(rejected)
        )

        print(
            "Carpeta:",
            OUTPUT_DIR
        )

        print("=" * 60)

    finally:

        # ====================================================
        # RESTAURAR ESCENA
        # ====================================================

        for op, old_value in original_values:

            if old_value is not None:
                op.Set(old_value)

        # Quitar operaciones temporales del orden
        xf.SetXformOpOrder(original_ops)

        if (
            robot_img is not None
            and old_robot_visibility is not None
        ):

            robot_img.GetVisibilityAttr().Set(
                old_robot_visibility
            )

        if rgb_ann is not None:
            rgb_ann.detach()

        if seg_ann is not None:
            seg_ann.detach()

        if render_product is not None:
            render_product.destroy()

        print(
            "[OK] Escena restaurada."
        )


# ============================================================
# EJECUTAR
# ============================================================

asyncio.ensure_future(
    generar()
)
