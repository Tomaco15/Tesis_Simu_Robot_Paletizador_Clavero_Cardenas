# ============================================================
# DIAGNOSTICO DE INTRINSECOS EFECTIVOS - ISAAC SIM 4.5.x
# Compara la cámara IR de Isaac Sim con los intrínsecos Astra
# usados en la reconstrucción 3D.
#
# Ejecutar en Isaac Sim -> Window -> Script Editor
# ============================================================

import asyncio
import numpy as np
import omni.usd
import omni.replicator.core as rep

from pxr import UsdGeom
from isaacsim.sensors.camera import Camera


# ============================================================
# CONFIGURACION
# ============================================================

CAMERA_PATH = "/World/Camera_IR_Astra"

WIDTH = 640
HEIGHT = 480

# Intrínsecos Astra Pro IR usados actualmente
K_ASTRA = np.array([
    [582.5099,   0.0,      322.4116],
    [0.0,        582.2891, 249.9390],
    [0.0,        0.0,        1.0]
], dtype=np.float64)

FRAMES_ESTABILIZACION = 5


# ============================================================
# UTILIDADES
# ============================================================

def imprimir_matriz(nombre, M):
    print("")
    print(nombre)
    print(np.array2string(
        np.asarray(M),
        precision=6,
        suppress_small=False
    ))


def leer_attr(obj, nombre):
    try:
        attr = getattr(obj, nombre)()
        return attr.Get()
    except Exception:
        return None


def calcular_intrinsecos_desde_usd(camera_prim, width, height):
    """
    Calcula fx, fy y una estimación del principal point a partir
    de los parámetros ópticos USD.

    Para focales:
        fx = width  * focalLength / horizontalAperture
        fy = height * focalLength / verticalAperture

    La cámara USD normalmente queda centrada si los aperture offsets
    son 0. Los offsets se imprimen por separado y se comparan con el
    K obtenido directamente desde Isaac.
    """
    cam = UsdGeom.Camera(camera_prim)

    focal = cam.GetFocalLengthAttr().Get()
    h_ap = cam.GetHorizontalApertureAttr().Get()
    v_ap = cam.GetVerticalApertureAttr().Get()

    h_off = cam.GetHorizontalApertureOffsetAttr().Get()
    v_off = cam.GetVerticalApertureOffsetAttr().Get()

    fx = width * float(focal) / float(h_ap)
    fy = height * float(focal) / float(v_ap)

    # Centro geométrico de imagen como referencia.
    cx_center = width / 2.0
    cy_center = height / 2.0

    return {
        "focalLength": float(focal),
        "horizontalAperture": float(h_ap),
        "verticalAperture": float(v_ap),
        "horizontalApertureOffset": float(h_off),
        "verticalApertureOffset": float(v_off),
        "fx_usd": float(fx),
        "fy_usd": float(fy),
        "cx_center": float(cx_center),
        "cy_center": float(cy_center),
    }


def imprimir_comparacion(K_isaac):
    fx_i = float(K_isaac[0, 0])
    fy_i = float(K_isaac[1, 1])
    cx_i = float(K_isaac[0, 2])
    cy_i = float(K_isaac[1, 2])

    fx_a = float(K_ASTRA[0, 0])
    fy_a = float(K_ASTRA[1, 1])
    cx_a = float(K_ASTRA[0, 2])
    cy_a = float(K_ASTRA[1, 2])

    print("")
    print("=" * 90)
    print(" COMPARACION ISAAC vs ASTRA USADO EN RECONSTRUCCION")
    print("=" * 90)

    print(f"fx Isaac : {fx_i:.6f} px")
    print(f"fx Astra : {fx_a:.6f} px")
    print(f"dif fx   : {fx_i - fx_a:+.6f} px")
    print(f"dif fx % : {(fx_i - fx_a) / fx_a * 100.0:+.6f} %")
    print("")

    print(f"fy Isaac : {fy_i:.6f} px")
    print(f"fy Astra : {fy_a:.6f} px")
    print(f"dif fy   : {fy_i - fy_a:+.6f} px")
    print(f"dif fy % : {(fy_i - fy_a) / fy_a * 100.0:+.6f} %")
    print("")

    print(f"cx Isaac : {cx_i:.6f} px")
    print(f"cx Astra : {cx_a:.6f} px")
    print(f"dif cx   : {cx_i - cx_a:+.6f} px")
    print("")

    print(f"cy Isaac : {cy_i:.6f} px")
    print(f"cy Astra : {cy_a:.6f} px")
    print(f"dif cy   : {cy_i - cy_a:+.6f} px")

    print("")
    print("Relación fx/fy:")
    print(f"  Isaac : {fx_i / fy_i:.9f}")
    print(f"  Astra : {fx_a / fy_a:.9f}")
    print(f"  cambio: {(fx_i / fy_i) - (fx_a / fy_a):+.9f}")

    print("")
    print("IMPORTANTE:")
    print("Si fx, fy, cx o cy de Isaac difieren del K_ASTRA,")
    print("la nube 3D se está reconstruyendo con una cámara")
    print("matemática distinta de la que realmente renderiza Isaac.")


# ============================================================
# PRINCIPAL
# ============================================================

async def main():

    print("")
    print("=" * 90)
    print(" DIAGNOSTICO INTRINSECOS - CAMERA IR ASTRA")
    print("=" * 90)
    print("Camera path:", CAMERA_PATH)
    print("Resolución esperada:", WIDTH, "x", HEIGHT)

    stage = omni.usd.get_context().get_stage()

    prim = stage.GetPrimAtPath(CAMERA_PATH)

    if not prim.IsValid():
        print("")
        print("ERROR: no existe el prim:", CAMERA_PATH)
        return

    if not prim.IsA(UsdGeom.Camera):
        print("")
        print("ERROR: el prim existe, pero no es UsdGeom.Camera")
        print("Tipo:", prim.GetTypeName())
        return

    # --------------------------------------------------------
    # Parámetros USD crudos
    # --------------------------------------------------------

    datos_usd = calcular_intrinsecos_desde_usd(
        prim,
        WIDTH,
        HEIGHT
    )

    print("")
    print("-" * 90)
    print(" PARAMETROS OPTICOS USD")
    print("-" * 90)

    for k, v in datos_usd.items():
        print(f"{k:28s}: {v}")

    print("")
    print("Intrínsecos derivados manualmente desde USD:")
    print(f"fx_usd = {datos_usd['fx_usd']:.6f} px")
    print(f"fy_usd = {datos_usd['fy_usd']:.6f} px")
    print(f"centro geométrico = ({datos_usd['cx_center']:.6f}, {datos_usd['cy_center']:.6f}) px")

    # --------------------------------------------------------
    # Camera API de Isaac
    # --------------------------------------------------------

    camera = Camera(
        prim_path=CAMERA_PATH,
        resolution=(WIDTH, HEIGHT)
    )

    try:
        camera.initialize()
    except Exception as e:
        print("")
        print("Aviso initialize():", repr(e))

    for _ in range(FRAMES_ESTABILIZACION):
        await rep.orchestrator.step_async()

    # --------------------------------------------------------
    # Intrínsecos efectivos reportados por Isaac
    # --------------------------------------------------------

    K_isaac = None

    try:
        K_isaac = np.asarray(
            camera.get_intrinsics_matrix(),
            dtype=np.float64
        )

        imprimir_matriz(
            "K EFECTIVO REPORTADO POR ISAAC:",
            K_isaac
        )

    except Exception as e:
        print("")
        print("ERROR al llamar camera.get_intrinsics_matrix():")
        print(repr(e))

    imprimir_matriz(
        "K ASTRA USADO ACTUALMENTE EN RECONSTRUCCION:",
        K_ASTRA
    )

    # --------------------------------------------------------
    # FOV aproximado
    # --------------------------------------------------------

    print("")
    print("-" * 90)
    print(" FOV APROXIMADO")
    print("-" * 90)

    if K_isaac is not None:
        fx = float(K_isaac[0, 0])
        fy = float(K_isaac[1, 1])

        hfov = np.degrees(
            2.0 * np.arctan(WIDTH / (2.0 * fx))
        )

        vfov = np.degrees(
            2.0 * np.arctan(HEIGHT / (2.0 * fy))
        )

        print(f"HFOV Isaac ≈ {hfov:.6f} grados")
        print(f"VFOV Isaac ≈ {vfov:.6f} grados")

    fx_a = K_ASTRA[0, 0]
    fy_a = K_ASTRA[1, 1]

    hfov_a = np.degrees(
        2.0 * np.arctan(WIDTH / (2.0 * fx_a))
    )

    vfov_a = np.degrees(
        2.0 * np.arctan(HEIGHT / (2.0 * fy_a))
    )

    print(f"HFOV Astra ≈ {hfov_a:.6f} grados")
    print(f"VFOV Astra ≈ {vfov_a:.6f} grados")

    # --------------------------------------------------------
    # Comparación final
    # --------------------------------------------------------

    if K_isaac is not None:
        imprimir_comparacion(K_isaac)

    print("")
    print("=" * 90)
    print(" DIAGNOSTICO TERMINADO")
    print("=" * 90)


asyncio.ensure_future(main())
