# Robot ensamble: ROS 2 e Isaac Sim

El modelo fuente es `urdf/robot_ensamble.xacro`. El archivo para importar en
Isaac Sim es **`urdf/robot_ensamble_isaac.urdf`**: contiene 17 enlaces y
16 articulaciones (10 fijas, 5 móviles independientes y 1 seguidora).

La exportación conserva los cambios de posición del Xacro:

| Articulación | Origen `xyz` en metros, respecto a su enlace padre |
| --- | --- |
| `x_link` | `-0.02001 0.031 0.6215` |
| `z_link` | `0.005 0.0115 0.0` |
| `rig_9` | `0.000197 -0.32 -0.033` |
| `rig_10` | `0.000197 -0.32 -0.129` |

Los mandos independientes son `x_link`, `y_link`, `z_link`, `r_joint` y
`grid_izq`. La pinza conserva `grid_der = -grid_izq`: comandar `grid_izq`
entre `0` y `0.04 m` produce un recorrido de `0` a `-0.04 m` en `grid_der`.
La transmisión independiente de `grid_der` se retiró de
`robot_ensamble.trans` para reflejar esta relación.

## Regenerar después de editar el Xacro

Desde la raíz del workspace:

```bash
source /opt/ros/humble/setup.bash
xacro src/robot_ensamble_description/urdf/robot_ensamble.xacro \
  include_ros_extensions:=false \
  mesh_prefix:=../meshes/ \
  -o src/robot_ensamble_description/urdf/robot_ensamble_isaac.urdf
check_urdf src/robot_ensamble_description/urdf/robot_ensamble_isaac.urdf
```

El URDF generado usa rutas relativas y excluye transmisiones y etiquetas
Gazebo. No requiere ROS para importarse. Al trasladarlo a otro equipo,
copiar las carpetas `urdf/` y `meshes/` juntas, conservando su disposición:

```text
robot_ensamble_description/
├── urdf/robot_ensamble_isaac.urdf
└── meshes/*.stl
```

Por defecto, el Xacro mantiene las extensiones ROS/Gazebo y utiliza rutas
`package://robot_ensamble_description/meshes/` para los lanzadores existentes.
Las referencias de `robot_ensamble.gazebo` y el material `silver` de
`materials.xacro` ya corresponden al modelo; no duplican las poses editadas.
El esquema de control legado de Gazebo no constituye una configuración de
`ros2_control` y queda excluido del URDF para Isaac.

## Importar en Isaac Sim

Abrir **File > Import** y seleccionar `robot_ensamble_isaac.urdf`.
La extensión es `isaacsim.asset.importer.urdf`. Los nombres de las opciones
pueden variar entre versiones; consultar la
[documentación del importador de NVIDIA para 5.1](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/importer_exporter/ext_isaacsim_asset_importer_urdf.html).

- Seleccionar base estática (**Static Base / Fix Base**).
- Mantener **Ignore Mimic** desactivado; si aparece **Parse Mimic**, activarlo.
- Usar **Convex Decomposition** y comenzar con **Self Collision** desactivado.
- Mantener la escala global en `1.0`: cada malla ya incluye `0.001` de mm a m.
- Si están disponibles, activar **Import Inertia Tensor** y desactivar
  **Merge Fixed Joints** para conservar los 17 enlaces.
- Configurar los cinco mandos en posición y mantener `grid_der` como Mimic.

Revisar los colisionadores del pórtico y la pinza después de importar.
Los límites de esfuerzo y velocidad del CAD se conservan; las ganancias de
control deben ajustarse en el simulador.

La inercia nula de `horn_Servo_1` se sustituyó por una estimación mediante
integración del volumen de su STL, suponiendo densidad uniforme y conservando
la masa y el origen inercial CAD. Las unidades son kg·m²; no es una medición
física. Los demás tensores se conservan.

La validación local comprueba la expansión Xacro, la lectura con `check_urdf`,
las referencias a mallas, la relación Mimic y las inercias. Isaac Sim no está
disponible en este entorno, por lo que la importación USD y la dinámica de
contacto quedan pendientes de comprobar en el simulador.
