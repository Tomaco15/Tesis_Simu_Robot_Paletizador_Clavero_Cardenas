import omni.usd
from pxr import Gf

stage = omni.usd.get_context().get_stage()

shader = stage.GetPrimAtPath(
    "/World/PlasticoBlancoBandeja/Shader"
)

if shader.IsValid():

    # Blanco lechoso
    shader.GetAttribute(
        "inputs:diffuseColor"
    ).Set(Gf.Vec3f(0.85, 0.85, 0.83))

    # Plástico no metálico
    shader.GetAttribute(
        "inputs:metallic"
    ).Set(0.0)

    # Superficie satinada
    shader.GetAttribute(
        "inputs:roughness"
    ).Set(0.65)

    # Completamente opaco
    shader.GetAttribute(
        "inputs:opacity"
    ).Set(1.0)

    print("Material plástico blanco aplicado correctamente")