# Robot v2: ROS 2 e Isaac Sim

Para Isaac Sim, importar **`urdf/robot_v2_isaac.urdf`**. El modelo contiene
18 enlaces y 17 articulaciones: 11 fijas, 5 móviles independientes y una
seguidora. Mantener las carpetas `urdf/` y `meshes/` juntas al copiarlo.

## Correcciones de la exportación

El URDF anterior pasaba `check_urdf`, pero contenía estos problemas:

- `horn_Servo_1` tenía una masa positiva y un tensor de inercia nulo.
- `Soporte_1_1` y `Soporte_2_1` tenían `iyy=0` con `ixy=4e-6`, lo que
  producía una inercia principal negativa de aproximadamente
  `-1.76e-8 kg·m²` en cada soporte.
- Las 36 referencias a mallas apuntaban mediante rutas absolutas a
  `install/robot_v2_description/`. Esas rutas existían en el equipo de
  desarrollo, pero dependían de su instalación y ubicación.

Las tres inercias se estimaron integrando el volumen de sus STL, con
densidad uniforme y la masa original. Se comprobó que esas mallas fueran
cerradas y tuvieran orientación consistente. La integración usa la escala
`0.001` y el origen visual, y expresa el tensor respecto al origen inercial
CAD existente. La diferencia entre el centroide de malla y ese origen es
menor que 6 micrómetros. Son estimaciones en kg·m², no mediciones físicas.

La corrección está en `robot_v2.xacro` y en ambas exportaciones. Se conservan
las masas, los orígenes, las articulaciones, sus límites y los materiales.
El URDF para Isaac usa `../meshes/*.stl` y excluye transmisiones y etiquetas
Gazebo. `robot_v2.urdf` conserva las extensiones ROS/Gazebo y utiliza rutas
`package://robot_v2_description/meshes/`.

## Regenerar

Desde la raíz del repositorio, sin necesidad de compilar el paquete:

```bash
source /opt/ros/humble/setup.bash
xacro src/robot_v2_description/urdf/robot_v2.xacro \
  -o src/robot_v2_description/urdf/robot_v2.urdf
xacro src/robot_v2_description/urdf/robot_v2.xacro \
  include_ros_extensions:=false \
  mesh_directory:=../meshes \
  -o src/robot_v2_description/urdf/robot_v2_isaac.urdf
check_urdf src/robot_v2_description/urdf/robot_v2_isaac.urdf
```

## Importar

Seleccionar `robot_v2_isaac.urdf` en el importador URDF y un directorio de
salida con permiso de escritura. Usar base estática (**Static Base**) y
mantener **Ignore Mimic** desactivado para conservar `grid_der = -grid`.
Comenzar con **Self Collision** desactivado y usar **Convex Decomposition**
para representar mejor las piezas cóncavas. Estas opciones se describen en
la [documentación de NVIDIA para Isaac Sim 5.1](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/importer_exporter/ext_isaacsim_asset_importer_urdf.html);
sus nombres pueden variar entre versiones.

Los mandos independientes son `x_joint`, `y_joint`, `z_joint`, `r_joint` y
`grid`. La escala de las mallas ya convierte milímetros a metros.

La validación local revisa ambas exportaciones, las rutas a las 18 mallas,
la estructura, Mimic y los tensores de inercia. La importación USD y el
comportamiento dinámico requieren comprobarse en Isaac Sim. Sin el mensaje
de error del importador, no se puede confirmar cuál de los problemas
detectados explica el fallo observado.
