import omni.usd
from pxr import UsdGeom

# Obtener la escena actual
ctx = omni.usd.get_context()
stage = ctx.get_stage()

# Obtener el objeto seleccionado
selection = ctx.get_selection().get_selected_prim_paths()

if not selection:
    print("ERROR: Selecciona el Mesh de la bandeja.")
else:
    path = selection[0]
    prim = stage.GetPrimAtPath(path)

    if prim.IsA(UsdGeom.Mesh):
        mesh = UsdGeom.Mesh(prim)

        # Obtener información de la geometría
        faces = mesh.GetFaceVertexCountsAttr().Get()
        vertices = mesh.GetPointsAttr().Get()

        print("================================")
        print("INFORMACIÓN DE LA BANDEJA")
        print("================================")
        print("Ruta:", path)
        print("Número de caras:", len(faces))
        print("Número de vértices:", len(vertices))
        print("================================")
    else:
        print("El objeto seleccionado no es un Mesh.")
