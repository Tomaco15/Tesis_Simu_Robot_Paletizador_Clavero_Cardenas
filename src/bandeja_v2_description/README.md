# Bandeja v2: URDF para Isaac Sim

El archivo para importar es **`urdf/bandeja_v2_isaac.urdf`**, generado desde
`urdf/bandeja_v2.xacro`. El paquete ROS se llama `bandeja_v2_description` y
el modelo se llama `bandeja_v2`. Contiene un único enlace, `base_link`, sin
articulaciones.

La exportación conserva la geometría, el material, el centro de masa, la
masa de **0.530653056 kg** y el tensor de inercia del Xacro original. Las
dimensiones de la malla a escala son aproximadamente **500 × 300.110 × 66 mm**.

## Regenerar

Ejecutar desde la raíz del repositorio, con Xacro instalado:

```bash
source /opt/ros/humble/setup.bash
xacro src/bandeja_v2_description/urdf/bandeja_v2.xacro \
  include_ros_extensions:=false \
  mesh_directory:=../meshes \
  -o src/bandeja_v2_description/urdf/bandeja_v2_isaac.urdf
check_urdf src/bandeja_v2_description/urdf/bandeja_v2_isaac.urdf
```

No hace falta compilar el paquete para generar o importar este archivo.
Los archivos incluidos por el Xacro se buscan en su propio directorio.
El URDF exportado no contiene macros pendientes, búsquedas de paquetes,
rutas absolutas, transmisiones ROS ni etiquetas de Gazebo.

El procesamiento por defecto del Xacro conserva las extensiones ROS/Gazebo
y utiliza `package://bandeja_v2_description/meshes/base_link.stl`. Los
lanzadores existentes siguen procesando ese Xacro.

## Importar en Isaac Sim

Conservar juntos los siguientes archivos al copiar el modelo a otro equipo:

```text
bandeja_v2_description/
├── urdf/
│   └── bandeja_v2_isaac.urdf
└── meshes/
    └── base_link.stl
```

1. Habilitar `isaacsim.asset.importer.urdf` en **Window > Extensions** si
   hace falta. Abrir **File > Import** y seleccionar el URDF exportado.
2. Usar **Moveable Base** o desactivar **Fix Base**, según la versión, para
   permitir que el robot levante la bandeja.
3. Elegir **Convex Decomposition** para las colisiones y un directorio de
   salida con permiso de escritura.

Estas opciones se describen en la [documentación de NVIDIA del importador](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/importer_exporter/ext_isaacsim_asset_importer_urdf.html).
Si aparece **Import Inertia Tensor**, activarlo para conservar la inercia
del URDF; véanse las [opciones del importador clásico](https://docs.omniverse.nvidia.com/kit/docs/omniverse-urdf-importer/latest/index.html).

Mantener la escala de importación en `1.0` si se muestra esa opción: la
malla ya se convierte de milímetros a metros con `scale="0.001 0.001 0.001"`.
Por la forma de la bandeja, se recomienda revisar que los colisionadores
resultantes conserven su hueco interior. Un único casco convexo puede cubrirlo.

## Revisión realizada

- `colcon list --base-paths src` reconoce el paquete sin nombres duplicados.
- Nombre del paquete coherente en manifiesto, instalación, recursos Python
  y lanzadores; sin referencias al nombre anterior en los archivos revisados.
- `check_urdf`: XML válido, raíz `base_link`, sin articulaciones.
- Exportación reproducible desde el Xacro; propiedades originales
  conservadas y ambas referencias de malla resueltas dentro de este paquete.
- Masa positiva e inercia definida positiva, con momentos principales que
  satisfacen las desigualdades triangulares.
- STL binario de 84 794 triángulos, con coordenadas y normales finitas.
  Contiene **4 triángulos de área cero**, heredados de la malla original.
  La malla se conserva sin modificar; comprobar el resultado del
  procesamiento de colisiones al importar en Isaac Sim.
- Configuración de RViz corregida para mostrar solo `base_link`, retirando
  referencias a ruedas y motores que no pertenecen a la bandeja.

La revisión local no ejecuta Isaac Sim ni valida agarres o contactos físicos.
Las extensiones de control Gazebo del exportador CAD se conservan en el
Xacro por defecto, pero no forman parte del URDF de Isaac ni se han probado
en una simulación de Gazebo.
