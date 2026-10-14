import os
import csv
import asyncio
import numpy as np
import cv2
from PIL import Image

import omni.usd
import omni.replicator.core as rep

from pxr import Usd, UsdGeom, UsdPhysics, Gf
from isaacsim.sensors.camera import Camera
from isaacsim.core.utils.semantics import add_update_semantics


# =============================================================================
# CONFIGURACION
# =============================================================================

WIDTH = 640
HEIGHT = 480

CAMERA_RGB_PATH = "/World/Camera_RGB_Astra"
PIVOTE_PATH = "/World/Bandeja_Centrada"
BASE_LINK_PATH = "/World/Bandeja_Centrada/bandeja/base_link"
ROBOT_ROOT_PATH = "/World/robot_parametrico"

ROBOT_JOINT_NAMES = (
    "x_joint",
    "y_joint",
    "z_joint",
    "r_joint",
)

# Dataset nuevo; no pisa el anterior.
OUTPUT_DIR = "/home/cristian/Desktop/dataset_astra_blanca_200"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
LABELS_DIR = os.path.join(OUTPUT_DIR, "labels")
MASKS_DIR = os.path.join(OUTPUT_DIR, "masks")
META_CSV = os.path.join(OUTPUT_DIR, "metadata.csv")

os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(LABELS_DIR, exist_ok=True)
os.makedirs(MASKS_DIR, exist_ok=True)

# 4 bloques x 50 imagenes validas
N_POR_BLOQUE = 50
TOTAL_IMGS = 4 * N_POR_BLOQUE

RANDOM_SEED = 20261009

# La bandeja SIEMPRE cambia
DX_RANGE_M = (-0.10, 0.10)
DY_RANGE_M = (-0.10, 0.10)
YAW_RANGE_DEG = (0.0, 180.0)

# Iluminacion variable solo en bloques 3 y 4
LIGHT_FACTOR_RANGE = (0.65, 1.35)

# Margen de seguridad respecto a los limites de joints
ROBOT_LIMIT_MARGIN = 0.15

# Frames de estabilizacion
FRAMES_INICIALES = 8
FRAMES_BANDEJA = 4
FRAMES_ROBOT = 10
FRAMES_LUZ = 3
FRAMES_CAPTURA = 2

# Calidad minima de mascara
MIN_MASK_PIXELS = 1200
MAX_INTENTOS_POR_BLOQUE = 300

# YOLO-seg
CLASS_ID = 0
SEMANTIC_LABEL = "bandeja"
POLY_EPSILON_FACTOR = 0.0025


# =============================================================================
# TRANSFORMS BANDEJA
# =============================================================================

def obtener_translate_op(path):
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(path)

    if not prim.IsValid():
        raise RuntimeError("No existe: " + path)

    xformable = UsdGeom.Xformable(prim)

    for op in xformable.GetOrderedXformOps():
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            return op

    return xformable.AddTranslateOp()


def leer_translate(path):
    op = obtener_translate_op(path)
    value = op.Get()

    if value is None:
        return np.zeros(3, dtype=np.float64)

    return np.array(
        [float(value[0]), float(value[1]), float(value[2])],
        dtype=np.float64,
    )


def escribir_translate(path, xyz):
    op = obtener_translate_op(path)

    if op.GetPrecision() == UsdGeom.XformOp.PrecisionDouble:
        value = Gf.Vec3d(float(xyz[0]), float(xyz[1]), float(xyz[2]))
    else:
        value = Gf.Vec3f(float(xyz[0]), float(xyz[1]), float(xyz[2]))

    op.Set(value)


def establecer_angulo_bandeja(angle_deg):
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(PIVOTE_PATH)

    if not prim.IsValid():
        raise RuntimeError("No existe: " + PIVOTE_PATH)

    xformable = UsdGeom.Xformable(prim)
    rotate_op = None

    for op in xformable.GetOrderedXformOps():
        if op.GetOpType() in (
            UsdGeom.XformOp.TypeRotateXYZ,
            UsdGeom.XformOp.TypeRotateZYX,
            UsdGeom.XformOp.TypeRotateZ,
        ):
            rotate_op = op
            break

    if rotate_op is None:
        rotate_op = xformable.AddRotateXYZOp()

    if rotate_op.GetOpType() == UsdGeom.XformOp.TypeRotateZ:
        rotate_op.Set(float(angle_deg))
    else:
        actual = rotate_op.Get()

        if actual is None:
            x = 0.0
            y = 0.0
        else:
            x = float(actual[0])
            y = float(actual[1])

        rotate_op.Set(Gf.Vec3f(x, y, float(angle_deg)))


# =============================================================================
# BANDEJA KINEMATIC
# =============================================================================

def set_base_link_kinematic(value=True):
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(BASE_LINK_PATH)

    if not prim.IsValid():
        print("[WARN] No existe BASE_LINK_PATH:", BASE_LINK_PATH)
        return

    if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
        print("[WARN] base_link no tiene RigidBodyAPI. Continuo sin tocar kinematic.")
        return

    api = UsdPhysics.RigidBodyAPI(prim)
    attr = api.GetKinematicEnabledAttr()

    if not attr:
        attr = api.CreateKinematicEnabledAttr()

    attr.Set(bool(value))


# =============================================================================
# LUCES
# =============================================================================

def descubrir_luces():
    stage = omni.usd.get_context().get_stage()
    luces = []

    for prim in stage.Traverse():
        attr = prim.GetAttribute("inputs:intensity")

        if not attr:
            continue

        try:
            value = attr.Get()
        except Exception:
            value = None

        if value is None:
            continue

        try:
            base = float(value)
        except Exception:
            continue

        luces.append(
            {
                "path": str(prim.GetPath()),
                "attr": attr,
                "base": base,
            }
        )

    return luces


def aplicar_factor_luz(luces, factor):
    for item in luces:
        try:
            item["attr"].Set(float(item["base"] * factor))
        except Exception:
            pass


# =============================================================================
# ROBOT / GARRA
# =============================================================================

def descubrir_joints_robot():
    stage = omni.usd.get_context().get_stage()
    root = stage.GetPrimAtPath(ROBOT_ROOT_PATH)

    if not root.IsValid():
        print("[WARN] No existe:", ROBOT_ROOT_PATH)
        return {}

    wanted = set(ROBOT_JOINT_NAMES)
    encontrados = {}

    for prim in Usd.PrimRange(root):
        name = prim.GetName()

        if name not in wanted:
            continue

        drive_attr = None
        drive_kind = None

        for kind in ("linear", "angular"):
            attr = prim.GetAttribute(f"drive:{kind}:physics:targetPosition")

            if attr:
                try:
                    if attr.Get() is not None:
                        drive_attr = attr
                        drive_kind = kind
                        break
                except Exception:
                    pass

        if drive_attr is None:
            continue

        lower_attr = prim.GetAttribute("physics:lowerLimit")
        upper_attr = prim.GetAttribute("physics:upperLimit")

        lower = lower_attr.Get() if lower_attr else None
        upper = upper_attr.Get() if upper_attr else None

        try:
            lower = float(lower)
            upper = float(upper)
        except Exception:
            continue

        if not np.isfinite(lower) or not np.isfinite(upper):
            continue

        lo = min(lower, upper)
        hi = max(lower, upper)

        if hi - lo < 1e-9:
            continue

        try:
            current_target = float(drive_attr.Get())
        except Exception:
            current_target = 0.5 * (lo + hi)

        encontrados[name] = {
            "prim_path": str(prim.GetPath()),
            "drive_attr": drive_attr,
            "drive_kind": drive_kind,
            "lower": lo,
            "upper": hi,
            "fixed_target": current_target,
        }

    return encontrados


def restaurar_robot_fijo(joints):
    targets = {}

    for name, data in joints.items():
        target = float(data["fixed_target"])

        try:
            data["drive_attr"].Set(target)
            targets[name] = target
        except Exception:
            pass

    return targets


def randomizar_robot(joints, rng):
    targets = {}

    for name, data in joints.items():
        lo = float(data["lower"])
        hi = float(data["upper"])
        span = hi - lo

        safe_lo = lo + ROBOT_LIMIT_MARGIN * span
        safe_hi = hi - ROBOT_LIMIT_MARGIN * span

        if safe_hi <= safe_lo:
            safe_lo = lo
            safe_hi = hi

        target = float(rng.uniform(safe_lo, safe_hi))

        try:
            data["drive_attr"].Set(target)
            targets[name] = target
        except Exception:
            pass

    return targets


# =============================================================================
# SEMANTICA GT DE LA BANDEJA
# =============================================================================

def aplicar_semantica_bandeja():
    stage = omni.usd.get_context().get_stage()
    root = stage.GetPrimAtPath(PIVOTE_PATH)

    if not root.IsValid():
        raise RuntimeError("No existe: " + PIVOTE_PATH)

    n = 0

    for prim in Usd.PrimRange(root):
        if prim.IsA(UsdGeom.Gprim):
            try:
                add_update_semantics(prim, SEMANTIC_LABEL, "class")
                n += 1
            except Exception as e:
                print("[WARN] Semantica:", prim.GetPath(), e)

    print(f"[OK] Semantica '{SEMANTIC_LABEL}' aplicada a {n} prims.")


# =============================================================================
# CAPTURA RGB + SEMANTIC SEGMENTATION
# =============================================================================

def extraer_rgb(rgb_data):
    if isinstance(rgb_data, dict):
        rgb = np.asarray(rgb_data["data"])
    else:
        rgb = np.asarray(rgb_data)

    if rgb.ndim != 3:
        return None

    if rgb.shape[2] == 4:
        rgb = rgb[:, :, :3]

    return np.ascontiguousarray(rgb.astype(np.uint8))


def extraer_mask_bandeja(semantic_data):
    if not isinstance(semantic_data, dict):
        return None

    if "data" not in semantic_data:
        return None

    seg = np.asarray(semantic_data["data"])
    seg = np.squeeze(seg)

    if seg.ndim != 2:
        return None

    info = semantic_data.get("info", {})
    id_to_labels = info.get("idToLabels", {})
    ids_bandeja = []

    if isinstance(id_to_labels, dict):
        for key, value in id_to_labels.items():
            texto = str(value).lower()

            if SEMANTIC_LABEL.lower() in texto:
                try:
                    ids_bandeja.append(int(key))
                except Exception:
                    pass

    if len(ids_bandeja) == 0:
        print("[WARN] No encontre el ID semantico de 'bandeja'.")
        print("idToLabels =", id_to_labels)
        return None

    mask = np.isin(seg, np.asarray(ids_bandeja, dtype=seg.dtype))
    return mask.astype(bool)


# =============================================================================
# MASK -> YOLO-SEG
# =============================================================================

def mask_a_poligono_yolo(mask):
    mask_u8 = mask.astype(np.uint8) * 255

    contours, _ = cv2.findContours(
        mask_u8,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )

    if len(contours) == 0:
        return None

    contour = max(contours, key=cv2.contourArea)

    if cv2.contourArea(contour) < 100.0:
        return None

    perimeter = cv2.arcLength(contour, True)
    epsilon = max(1.0, POLY_EPSILON_FACTOR * perimeter)
    approx = cv2.approxPolyDP(contour, epsilon, True)
    pts = approx.reshape(-1, 2)

    if len(pts) < 3:
        return None

    h, w = mask.shape
    coords = []

    for x, y in pts:
        xn = np.clip(float(x) / float(w), 0.0, 1.0)
        yn = np.clip(float(y) / float(h), 0.0, 1.0)
        coords.extend([xn, yn])

    return coords


def guardar_par_yolo(scene_id, rgb, mask):
    name = f"img_{scene_id:04d}"

    image_path = os.path.join(IMAGES_DIR, name + ".png")
    label_path = os.path.join(LABELS_DIR, name + ".txt")
    mask_path = os.path.join(MASKS_DIR, name + ".png")

    polygon = mask_a_poligono_yolo(mask)

    if polygon is None:
        return False, "", "", ""

    Image.fromarray(rgb).save(image_path)
    Image.fromarray(mask.astype(np.uint8) * 255).save(mask_path)

    with open(label_path, "w", encoding="utf-8") as f:
        valores = " ".join(f"{v:.6f}" for v in polygon)
        f.write(f"{CLASS_ID} {valores}\n")

    return True, image_path, label_path, mask_path


# =============================================================================
# BLOQUES
# =============================================================================

def configuracion_bloque(bloque):
    if bloque == 1:
        return False, False, "B1_bandeja"
    if bloque == 2:
        return True, False, "B2_bandeja_garra"
    if bloque == 3:
        return False, True, "B3_bandeja_luz"
    if bloque == 4:
        return True, True, "B4_bandeja_garra_luz"

    raise ValueError("Bloque invalido")


# =============================================================================
# FRAMES
# =============================================================================

async def avanzar_frames(n):
    for _ in range(int(n)):
        await rep.orchestrator.step_async()


# =============================================================================
# METADATA
# =============================================================================

def preparar_csv():
    with open(META_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "scene_id",
                "bloque",
                "nombre_bloque",
                "dx_m",
                "dy_m",
                "yaw_deg",
                "garra_random",
                "luz_random",
                "light_factor",
                "x_joint",
                "y_joint",
                "z_joint",
                "r_joint",
                "mask_pixels",
                "image_path",
                "label_path",
                "mask_path",
            ]
        )


def escribir_metadata(
    scene_id,
    bloque,
    nombre_bloque,
    dx,
    dy,
    yaw,
    garra_random,
    luz_random,
    light_factor,
    robot_targets,
    mask_pixels,
    image_path,
    label_path,
    mask_path,
):
    with open(META_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                scene_id,
                bloque,
                nombre_bloque,
                dx,
                dy,
                yaw,
                int(garra_random),
                int(luz_random),
                light_factor,
                robot_targets.get("x_joint", ""),
                robot_targets.get("y_joint", ""),
                robot_targets.get("z_joint", ""),
                robot_targets.get("r_joint", ""),
                mask_pixels,
                image_path,
                label_path,
                mask_path,
            ]
        )


# =============================================================================
# MAIN
# =============================================================================

async def main():
    print("")
    print("=" * 90)
    print(" DATASET YOLO-SEG - BANDEJA BLANCA - 200 IMAGENES")
    print("=" * 90)
    print("")
    print("Bloque 1 [001-050] Bandeja SI | Garra NO | Luz NO")
    print("Bloque 2 [051-100] Bandeja SI | Garra SI | Luz NO")
    print("Bloque 3 [101-150] Bandeja SI | Garra NO | Luz SI")
    print("Bloque 4 [151-200] Bandeja SI | Garra SI | Luz SI")
    print("")
    print("Salida:", OUTPUT_DIR)

    rng = np.random.default_rng(RANDOM_SEED)
    stage = omni.usd.get_context().get_stage()

    if stage is None:
        raise RuntimeError("No hay Stage USD abierto.")

    for p in (CAMERA_RGB_PATH, PIVOTE_PATH):
        if not stage.GetPrimAtPath(p).IsValid():
            raise RuntimeError("No existe: " + p)

    # Semantica GT para crear las etiquetas sin usar YOLO.
    aplicar_semantica_bandeja()

    # Evita que PhysX derive la pose de la bandeja.
    set_base_link_kinematic(True)

    # Camara RGB Astra
    camera_rgb = Camera(
        prim_path=CAMERA_RGB_PATH,
        resolution=(WIDTH, HEIGHT),
    )
    camera_rgb.initialize()

    rgb_annotator = rep.AnnotatorRegistry.get_annotator("rgb")
    sem_annotator = rep.AnnotatorRegistry.get_annotator(
        "semantic_segmentation",
        init_params={"colorize": False},
    )

    rgb_annotator.attach([camera_rgb._render_product_path])
    sem_annotator.attach([camera_rgb._render_product_path])

    # Estados que se consideran "fijos"
    translate_base = leer_translate(PIVOTE_PATH)
    luces = descubrir_luces()
    joints_robot = descubrir_joints_robot()

    print("")
    print("Traslacion base bandeja:", translate_base)
    print("Luces detectadas:", len(luces))
    print("Joints detectados:", list(joints_robot.keys()))

    print("")
    print("Targets fijos de robot/garra:")
    for name, data in joints_robot.items():
        print(f"  {name}: {data['fixed_target']:.6f}")

    print("")
    print("Intensidades fijas de luz:")
    for item in luces:
        print(" ", item["path"], "=", item["base"])

    preparar_csv()

    restaurar_robot_fijo(joints_robot)
    aplicar_factor_luz(luces, 1.0)
    await avanzar_frames(FRAMES_INICIALES)

    global_scene_id = 0

    for bloque in range(1, 5):
        mover_garra, mover_luz, nombre_bloque = configuracion_bloque(bloque)

        print("")
        print("#" * 90)
        print(f" INICIANDO BLOQUE {bloque}/4 -> {nombre_bloque}")
        print("#" * 90)

        # Al entrar a un bloque fijo, restauramos exactamente el estado inicial.
        if not mover_garra:
            restaurar_robot_fijo(joints_robot)

        if not mover_luz:
            aplicar_factor_luz(luces, 1.0)

        await avanzar_frames(max(FRAMES_ROBOT, FRAMES_LUZ))

        validas_bloque = 0
        intentos = 0

        while validas_bloque < N_POR_BLOQUE:
            intentos += 1

            if intentos > MAX_INTENTOS_POR_BLOQUE:
                raise RuntimeError(
                    f"Demasiados intentos en bloque {bloque}. "
                    f"Validas: {validas_bloque}/{N_POR_BLOQUE}"
                )

            # -----------------------------------------------------------------
            # BANDEJA: SIEMPRE CAMBIA
            # -----------------------------------------------------------------

            dx = float(rng.uniform(DX_RANGE_M[0], DX_RANGE_M[1]))
            dy = float(rng.uniform(DY_RANGE_M[0], DY_RANGE_M[1]))
            yaw = float(rng.uniform(YAW_RANGE_DEG[0], YAW_RANGE_DEG[1]))

            nueva_t = translate_base.copy()
            nueva_t[0] += dx
            nueva_t[1] += dy

            escribir_translate(PIVOTE_PATH, nueva_t)
            establecer_angulo_bandeja(yaw)
            await avanzar_frames(FRAMES_BANDEJA)

            # -----------------------------------------------------------------
            # GARRA / ROBOT
            # -----------------------------------------------------------------

            if mover_garra:
                robot_targets = randomizar_robot(joints_robot, rng)
                await avanzar_frames(FRAMES_ROBOT)
            else:
                robot_targets = restaurar_robot_fijo(joints_robot)

            # -----------------------------------------------------------------
            # ILUMINACION
            # -----------------------------------------------------------------

            if mover_luz:
                light_factor = float(
                    rng.uniform(LIGHT_FACTOR_RANGE[0], LIGHT_FACTOR_RANGE[1])
                )
                aplicar_factor_luz(luces, light_factor)
                await avanzar_frames(FRAMES_LUZ)
            else:
                light_factor = 1.0
                aplicar_factor_luz(luces, 1.0)

            # Captura fresca
            await avanzar_frames(FRAMES_CAPTURA)

            rgb = extraer_rgb(rgb_annotator.get_data())
            semantic_data = sem_annotator.get_data()
            mask = extraer_mask_bandeja(semantic_data)

            if rgb is None:
                print("[REINTENTO] RGB invalido.")
                continue

            if mask is None:
                print("[REINTENTO] Mascara semantica invalida.")
                continue

            if mask.shape != (HEIGHT, WIDTH):
                print("[REINTENTO] Shape mascara:", mask.shape)
                continue

            mask_pixels = int(np.count_nonzero(mask))

            if mask_pixels < MIN_MASK_PIXELS:
                print("[REINTENTO] Muy pocos pixeles:", mask_pixels)
                continue

            # El ID solo avanza cuando RGB+label son validos.
            next_scene_id = global_scene_id + 1

            ok, image_path, label_path, mask_path = guardar_par_yolo(
                next_scene_id,
                rgb,
                mask,
            )

            if not ok:
                print("[REINTENTO] No pude generar poligono YOLO.")
                continue

            global_scene_id = next_scene_id
            validas_bloque += 1

            escribir_metadata(
                scene_id=global_scene_id,
                bloque=bloque,
                nombre_bloque=nombre_bloque,
                dx=dx,
                dy=dy,
                yaw=yaw,
                garra_random=mover_garra,
                luz_random=mover_luz,
                light_factor=light_factor,
                robot_targets=robot_targets,
                mask_pixels=mask_pixels,
                image_path=image_path,
                label_path=label_path,
                mask_path=mask_path,
            )

            print(
                f"[OK] {global_scene_id:03d}/{TOTAL_IMGS}"
                f" | B{bloque}"
                f" | dx={dx:+.3f}"
                f" | dy={dy:+.3f}"
                f" | yaw={yaw:6.2f}"
                f" | garra={'MOV' if mover_garra else 'FIJA'}"
                f" | luz={'MOV' if mover_luz else 'FIJA'}"
                f" | factor={light_factor:.3f}"
                f" | mask={mask_pixels}"
            )

    # Restaurar escena al terminar
    escribir_translate(PIVOTE_PATH, translate_base)
    establecer_angulo_bandeja(0.0)
    restaurar_robot_fijo(joints_robot)
    aplicar_factor_luz(luces, 1.0)
    await avanzar_frames(FRAMES_INICIALES)

    print("")
    print("=" * 90)
    print(" DATASET TERMINADO")
    print("=" * 90)
    print("Imagenes validas:", global_scene_id)
    print("Images:", IMAGES_DIR)
    print("Labels:", LABELS_DIR)
    print("Masks:", MASKS_DIR)
    print("Metadata:", META_CSV)
    print("=" * 90)


# =============================================================================
# EJECUTAR EN SCRIPT EDITOR
# =============================================================================

asyncio.ensure_future(main())
