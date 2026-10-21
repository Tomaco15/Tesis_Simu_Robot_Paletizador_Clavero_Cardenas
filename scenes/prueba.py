import omni.usd
from pxr import UsdShade, Gf

# ==================================================
# 1. CONFIGURACIÓN
# ==================================================

stage = omni.usd.get_context().get_stage()

MESH_PATH = (
    "/World/bandeja_v2/base_link/"
    "visuals/base_link/mesh"
)

# Solo modificaremos divisiones y fondo.
# El marco conservará sus valores actuales.

CONFIG = {
    "DBG_Divisiones": {
        "color": (0.97, 0.97, 0.96),
        "reflection": 1.0,
        "subsurface": 0.12,
        "roughness": 0.80,
        "transmission_color": (0.97, 0.97, 0.96),
    },

    "DBG_Fondo": {
        "color": (0.99, 0.99, 0.98),
        "reflection": 1.0,
        "subsurface": 0.30,
        "roughness": 0.85,
        "transmission_color": (1.0, 1.0, 1.0),
    }
}

# ==================================================
# 2. OBTENER GEOMSUBSETS
# ==================================================

mesh_prim = stage.GetPrimAtPath(MESH_PATH)

if not mesh_prim.IsValid():
    raise RuntimeError("No se encontró la bandeja.")

if mesh_prim.IsInstanceProxy():
    raise RuntimeError("El Mesh continúa instanciado.")

binding = UsdShade.MaterialBindingAPI(mesh_prim)

subsets = {
    s.GetPrim().GetName(): s
    for s in binding.GetMaterialBindSubsets()
}

# ==================================================
# 3. VALIDAR MATERIALES Y PARÁMETROS
# ==================================================

preparados = {}

parametros = [
    "diffuse_reflection_color",
    "diffuse_reflection_weight",
    "subsurface_weight",
    "enable_diffuse_transmission",
    "subsurface_transmission_color",
    "specular_reflection_roughness",
    "thin_walled",
    "enable_opacity",
    "geometry_opacity",
]

for nombre, config in CONFIG.items():

    if nombre not in subsets:
        raise RuntimeError(
            "No se encontró el GeomSubset: " + nombre
        )

    subset = subsets[nombre]

    material, _ = (
        UsdShade.MaterialBindingAPI(
            subset.GetPrim()
        ).ComputeBoundMaterial()
    )

    if not material or not material.GetPrim().IsValid():
        raise RuntimeError(
            "Material no encontrado: " + nombre
        )

    shader_path = str(material.GetPath()) + "/Shader"

    shader_prim = stage.GetPrimAtPath(shader_path)

    if not shader_prim.IsValid():
        raise RuntimeError(
            "Shader no encontrado: " + shader_path
        )

    shader = UsdShade.Shader(shader_prim)

    for parametro in parametros:
        if not shader.GetInput(parametro):
            raise RuntimeError(
                f"Falta {parametro} en {shader_path}"
            )

    preparados[nombre] = shader


# Evitar modificar el marco si comparte material
marco, _ = (
    UsdShade.MaterialBindingAPI(
        subsets["DBG_Marco"].GetPrim()
    ).ComputeBoundMaterial()
)

materiales_modificables = [
    shader.GetPrim().GetParent().GetPath()
    for shader in preparados.values()
]

if marco and marco.GetPath() in materiales_modificables:
    raise RuntimeError(
        "El marco comparte material con otra región. "
        "No se realizará el ajuste."
    )

if len(set(materiales_modificables)) != len(
    materiales_modificables
):
    raise RuntimeError(
        "Divisiones y fondo comparten un material."
    )

# ==================================================
# 4. MODIFICAR MATERIALES
# ==================================================

print("\n========== AJUSTANDO BANDEJA ==========")

for nombre, config in CONFIG.items():

    shader = preparados[nombre]

    # Color blanco
    shader.GetInput(
        "diffuse_reflection_color"
    ).Set(Gf.Vec3f(*config["color"]))

    # Reflexión difusa
    shader.GetInput(
        "diffuse_reflection_weight"
    ).Set(config["reflection"])

    # Activar dispersión subsuperficial
    shader.GetInput(
        "enable_diffuse_transmission"
    ).Set(True)

    # Intensidad de translucidez
    shader.GetInput(
        "subsurface_weight"
    ).Set(config["subsurface"])

    # Color de transmisión
    shader.GetInput(
        "subsurface_transmission_color"
    ).Set(
        Gf.Vec3f(*config["transmission_color"])
    )

    # Rugosidad
    shader.GetInput(
        "specular_reflection_roughness"
    ).Set(config["roughness"])

    # Geometría sin espesor
    shader.GetInput(
        "thin_walled"
    ).Set(True)

    # Mantener opacidad alfa completa
    shader.GetInput(
        "enable_opacity"
    ).Set(False)

    shader.GetInput(
        "geometry_opacity"
    ).Set(1.0)

    print("\nRegión:", nombre)
    print("Color:", config["color"])
    print("Reflection:", config["reflection"])
    print("Subsurface:", config["subsurface"])
    print("Roughness:", config["roughness"])

print("\n====================================")
print("AJUSTES REALIZADOS")
print("====================================")

print("Marco exterior: SIN CAMBIOS")
print("Divisiones: blanco ligeramente translúcido")
print("Fondo: blanco lechoso con transmisión difusa")

print("\nNo se modificaron los GeomSubsets.")
print("No se modificaron las colisiones.")