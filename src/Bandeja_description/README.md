# Bandeja: exportación para Isaac Sim

Importar `urdf/bandeja_isaac.urdf`, generado desde `urdf/bandeja.xacro`.
El modelo tiene un solo cuerpo, `base_link`, sin articulaciones. Conserva
el material, el centro de masa, la masa de **0.530653056 kg**, el tensor de
inercia y las geometrías visual y de colisión del Xacro original.

Esta carpeta, **`Bandeja_description` con B mayúscula**, contiene un modelo
distinto del que está en `src/bandeja_description`. Ambos declaran el nombre
ROS `bandeja_description`; no deben descubrirse juntos en una compilación
con colcon. La importación directa del URDF no requiere compilar el paquete.

## Regenerar el URDF

Desde la raíz del repositorio:

```bash
source /opt/ros/humble/setup.bash
xacro src/Bandeja_description/urdf/bandeja.xacro \
  include_ros_extensions:=false \
  mesh_directory:=../meshes \
  -o src/Bandeja_description/urdf/bandeja_isaac.urdf
check_urdf src/Bandeja_description/urdf/bandeja_isaac.urdf
```

Las inclusiones del Xacro se resuelven desde su propio directorio. La
exportación excluye Gazebo y las transmisiones ROS, y no contiene macros
pendientes, búsquedas de paquetes ni rutas absolutas. El procesamiento por
defecto del Xacro mantiene las extensiones ROS/Gazebo y usa rutas `package://`.

Para trasladar el modelo a otro equipo, conservar esta estructura:

```text
Bandeja_description/
├── urdf/
│   └── bandeja_isaac.urdf
└── meshes/
    └── base_link.stl
```

## Importar en Isaac Sim

1. Habilitar `isaacsim.asset.importer.urdf` en **Window > Extensions** si hace
   falta. Abrir **File > Import** y seleccionar `urdf/bandeja_isaac.urdf`.
2. Elegir una base móvil (**Moveable/Mobile**, o **Fix Base** desactivado,
   según la versión) para que el robot pueda levantar la bandeja.
3. Seleccionar **Convex Decomposition** para las colisiones. Por la forma
   de la bandeja, conviene revisar que los colisionadores conserven su hueco
   interior; un único casco convexo puede cubrirlo.
4. Si aparecen las opciones **Import Inertia Tensor** y **Distance Scale**,
   activar la primera y mantener la escala en `1.0`. El URDF ya convierte
   los milímetros de la malla a metros con `scale="0.001 0.001 0.001"`.
5. Elegir un directorio de salida con permiso de escritura e importar.
   Revisar la geometría de colisión y el registro de importación.

Referencias de NVIDIA: [URDF Importer](https://docs.isaacsim.omniverse.nvidia.com/latest/importer_exporter/ext_isaacsim_asset_importer_urdf.html)
y [opciones del importador clásico](https://docs.omniverse.nvidia.com/kit/docs/omniverse-urdf-importer/latest/index.html).

## Revisión realizada

- `check_urdf`: XML válido, un enlace raíz y ninguna articulación.
- Exportación sincronizada con el Xacro; masa, inercia, poses, material y
  escala conservados; ambas referencias de malla apuntan al STL de esta carpeta.
- Inercia definida positiva con momentos principales que satisfacen las
  desigualdades triangulares.
- STL binario de 84 794 triángulos, con coordenadas y normales finitas.
  Dimensiones a escala: aproximadamente **500 × 300.110 × 66 mm**.
- La malla original contiene **4 triángulos de área cero**. Se conserva sin
  modificar; este hallazgo queda pendiente de comprobar en el procesamiento
  de colisiones de Isaac Sim.

La validación local no incluye una importación ejecutada en Isaac Sim ni
pruebas de agarre o de contactos físicos.
