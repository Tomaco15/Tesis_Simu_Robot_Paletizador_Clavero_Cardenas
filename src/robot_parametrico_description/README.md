# Robot paramétrico: ROS 2 e Isaac Sim 4.5.0

La fuente del modelo es `urdf/robot_parametrico.xacro`. La exportación
`urdf/robot_parametrico_isaac.urdf` contiene 16 enlaces y 15 articulaciones:
9 fijas, 5 móviles independientes y 1 móvil seguidora. Conserva las poses,
masas, límites y mallas del Xacro, incluidas las correcciones geométricas
existentes en el archivo.

## Un solo control de la pinza

Se comanda **`grid_der`**. La articulación `grid_izq` sigue su posición mediante:

```xml
<mimic joint="grid_der" multiplier="-1" offset="0"/>
```

Ambos ejes apuntan en la misma dirección, por lo que el signo negativo produce
movimientos opuestos. Se conserva el rango original de `-0.04` a `0.04 m` de
cada mordaza: aumentar `grid_der` abre la pinza y disminuirlo la cierra.
Cero conserva la postura CAD; no representa necesariamente el contacto entre
las mordazas. El recorrido cambia la separación entre ellas en el doble del
desplazamiento de cada articulación.

Los cinco controles independientes son `x_joint`, `y_joint`, `z_joint`,
`r_joint` y `grid_der`. Los publicadores ROS usan `use_mimic_tags=true` y la
transmisión independiente de `grid_izq` fue retirada. No se debe enviar un
segundo objetivo de posición a la seguidora.

## Compilar y abrir RViz2

Desde la raíz del workspace:

```bash
source /opt/ros/humble/setup.bash
colcon build --base-paths src --packages-select robot_parametrico_description --symlink-install
source install/setup.bash
ros2 launch robot_parametrico_description display.launch.py
```

RViz obtiene los enlaces del modelo y usa `base_link` como marco fijo. El
panel de articulaciones debe mostrar cinco controles y solo `grid_der` para
la pinza. Con `gui:=false` se utiliza el publicador sin panel gráfico.

## Regenerar el URDF para Isaac

No editar el URDF exportado a mano. Después de modificar el Xacro:

```bash
source /opt/ros/humble/setup.bash
xacro src/robot_parametrico_description/urdf/robot_parametrico.xacro \
  include_ros_extensions:=false \
  mesh_prefix:=../meshes/ \
  -o src/robot_parametrico_description/urdf/robot_parametrico_isaac.urdf
check_urdf src/robot_parametrico_description/urdf/robot_parametrico_isaac.urdf
```

La exportación elimina las etiquetas Gazebo y las transmisiones ROS. No
contiene búsquedas de paquetes, rutas absolutas de Linux ni macros sin
resolver. Las rutas relativas se interpretan desde el directorio del URDF.
Para trasladarlo a Windows, copiar ambos directorios juntos:

```text
robot_parametrico_description/
├── urdf/
│   └── robot_parametrico_isaac.urdf
└── meshes/
    └── *.stl
```

## Importación en Isaac Sim 4.5.0

Habilitar `isaacsim.asset.importer.urdf` y seleccionar el URDF exportado desde
**File > Import**. Usar un directorio local de salida con permiso de escritura.
La [documentación de NVIDIA para 4.5.0](https://docs.isaacsim.omniverse.nvidia.com/4.5.0/robot_setup/ext_isaacsim_asset_importer_urdf.html)
describe el tratamiento de `mimic`, nombres y colisiones.

| Opción | Configuración para este modelo |
| --- | --- |
| Base | Static / Fix Base: activado |
| Ignore Mimic | Desactivado; si aparece Parse Mimic, activarlo |
| Merge Fixed Joints | Desactivado para conservar los 16 enlaces; API: `merge_fixed_joints=False` |
| Import Inertia Tensor | Activado |
| Distance Scale | `1.0`; las mallas ya tienen escala `0.001` de mm a m |
| Collider Type | Convex Decomposition |
| Self Collision | Desactivado inicialmente |
| Drives | Position para los cinco mandos; conservar Mimic en `grid_izq` |

Evitar un único Convex Hull para toda la base: podría rellenar el espacio
vacío del pórtico. Revisar los colisionadores resultantes antes de ensayar
agarres. El URDF conserva las colisiones originales, que usan las mismas
mallas que la geometría visual.

Una vez importado, comprobar que `grid_izq` conserva la relación Mimic y
mover únicamente `grid_der` dentro de sus límites. Comenzar con objetivos
cercanos a la postura inicial y ajustar stiffness/damping en el simulador;
los límites de esfuerzo y velocidad del CAD no constituyen una sintonía
validada del controlador.

## Comprobaciones y alcance

```bash
source /opt/ros/humble/setup.bash
python3 -m pytest src/robot_parametrico_description/test/test_model.py -q
```

Las pruebas verifican sincronización Xacro/URDF, árbol conectado sin ciclos,
nombres compatibles con USD, rango del mimic, transmisiones, referencias
Gazebo, integridad de los 16 STL utilizados e inercias positivas físicamente
admisibles. `robot_Servo_1.stl` es una malla adicional sin referencia en el
Xacro; no se inventa un enlace para ella.

La inercia originalmente nula de `robot_Servo_horn__1` se sustituyó por una
estimación obtenida integrando el volumen de su STL a escala métrica, con
densidad uniforme y la masa original de 0.005099610361289279 kg. No sustituye
una medición física. Los demás tensores se conservan.

La auditoría de las mallas encontró aristas compartidas por más de dos
triángulos en `base_link.stl` (11) y `robot_mg996R_1.stl` (91), al soldar
vértices coincidentes de los conjuntos CAD. Los STL tienen datos finitos,
triángulos no degenerados y se leen con Assimp. Esto no certifica la
descomposición convexa de PhysX; debe inspeccionarse tras la importación.

La validación local no ejecuta Isaac Sim 4.5.0 ni certifica la dinámica de
contacto. La instalación Windows encontrada corresponde a 5.0.0. Los
archivos `.trans` y `.gazebo` conservan el esquema de control legado del
exportador CAD; no se incluyen en el URDF de Isaac y no equivalen a una
configuración de control ROS 2/Gazebo validada.
