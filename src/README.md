# Paquetes ROS 2 del proyecto

Este directorio contiene el código fuente del workspace. Actualmente hay dos paquetes Python de ROS 2: uno describe el robot paletizador y otro describe la bandeja.

## Paquetes disponibles

| Paquete | Modelo principal | Lanzadores |
| --- | --- | --- |
| `robot_description` | `urdf/robot.xacro` | `display.launch.py`, `gazebo.launch.py` |
| `bandeja_description` | `urdf/bandeja.xacro` | `display.launch.py`, `gazebo.launch.py` |

## `robot_description`

Contiene la cadena cinemática, las mallas y la configuración de simulación del robot cartesiano con garra.

```text
robot_description/
├── config/
│   ├── display.rviz
│   ├── gazebo.rviz
│   └── ros_gz_bridge_gazebo.yaml
├── launch/
│   ├── display.launch.py
│   └── gazebo.launch.py
├── meshes/
├── robot_description/
│   └── joint_state_to_gz.py
├── urdf/
│   ├── materials.xacro
│   ├── robot.gazebo
│   ├── robot.trans
│   ├── robot.xacro
│   └── robot_description_isaac.urdf
├── package.xml
└── setup.py
```

### Modelo activo

Los dos lanzadores procesan `urdf/robot.xacro`. Este es el archivo que debe modificarse para cambiar la geometría, las articulaciones o sus límites.

`urdf/robot_description_isaac.urdf` es la exportación pura del modelo completo para NVIDIA Isaac Sim. No es cargada por los lanzadores ROS 2. Los demás archivos llamados `robot_description.xacro`, `robot_description.gazebo` y `robot_description.ros2control` son modelos auxiliares y tampoco forman parte del flujo activo.

### Exportación para Isaac Sim

El archivo `robot_description_isaac.urdf` contiene 14 enlaces, 13 articulaciones y rutas relativas hacia las 14 mallas STL. No contiene macros Xacro, expresiones `$(find ...)`, transmisiones ROS ni etiquetas específicas de Gazebo.

Las rutas tienen el formato:

```xml
<mesh filename="../meshes/base_link.stl" scale="0.001 0.001 0.001"/>
```

Esto permite importar el modelo sin cargar ROS 2, siempre que `urdf/` y `meshes/` conserven su relación de directorios. El enlace original `cabezal_2.0_v1_1_1` se llama `cabezal_2_0_v1_1_1` únicamente en esta exportación, porque los puntos en nombres de prims no cumplen las convenciones de nombres USD.

### Articulaciones móviles

| Nombre | Tipo | Rango | Observación |
| --- | --- | --- | --- |
| `x_joint` | Prismática | `0.02` a `0.94 m` | Eje cartesiano X |
| `y_joint` | Prismática | `0.065` a `0.838 m` | Eje cartesiano Y |
| `z_joint` | Prismática | `-0.93` a `0.0 m` | Eje cartesiano Z |
| `R_joint` | Continua | Sin límites | Rotación del cabezal |
| `Grid_DER` | Prismática | `0.0` a `0.04 m` | Control principal de la garra |
| `Grid_IZQ` | Prismática | `-0.04` a `0.0 m` | Seguidora de `Grid_DER` |

La sincronización de la garra está declarada en `Grid_IZQ`:

```xml
<mimic joint="Grid_DER" multiplier="-1" offset="0"/>
```

Por lo tanto, solo se debe comandar `Grid_DER`. Mandar comandos independientes a la articulación seguidora puede entrar en conflicto con la relación `mimic`.

### Flujo de RViz2

```text
robot.xacro
    ├── robot_state_publisher
    ├── joint_state_publisher_gui
    └── RViz2
```

`display.launch.py` acepta el argumento `gui`. Su valor predeterminado es `true`.

### Flujo de Gazebo Classic

```text
robot.xacro → robot_state_publisher → spawn_entity.py → Gazebo Classic
```

`gazebo.launch.py` inicia `gzserver` pausado y abre `gzclient`. El complemento declarado en `robot.gazebo` es `libgazebo_ros_control.so`.

### Archivos auxiliares de comunicación

`config/ros_gz_bridge_gazebo.yaml` y `robot_description/joint_state_to_gz.py` contienen una propuesta de puente de posiciones para X, Y y Z. El lanzador actual de Gazebo Classic no inicia esos componentes y `joint_state_to_gz.py` no está registrado como ejecutable en `setup.py`; por tanto, no forman parte del flujo activo.

## `bandeja_description`

Contiene el modelo de la bandeja y su configuración para RViz2 y Gazebo Sim.

```text
bandeja_description/
├── config/
│   ├── display.rviz
│   ├── gazebo.rviz
│   └── ros_gz_bridge_gazebo.yaml
├── launch/
│   ├── display.launch.py
│   └── gazebo.launch.py
├── meshes/
├── urdf/
│   ├── bandeja.gazebo
│   ├── bandeja.ros2control
│   ├── bandeja.xacro
│   ├── bandeja_isaac.urdf
│   └── materials.xacro
├── package.xml
└── setup.py
```

`display.launch.py` utiliza RViz2. `gazebo.launch.py` utiliza Gazebo Sim, inicia un mundo vacío, publica el modelo con `robot_state_publisher`, crea la entidad `bandeja` y levanta `ros_gz_bridge`.

## Cómo editar una articulación

Una articulación prismática se define mediante su origen, enlaces padre e hijo, dirección y límites:

```xml
<joint name="ejemplo_joint" type="prismatic">
  <origin xyz="0 0 0" rpy="0 0 0"/>
  <parent link="enlace_padre"/>
  <child link="enlace_hijo"/>
  <axis xyz="1 0 0"/>
  <limit lower="0.0" upper="0.1" effort="100" velocity="1"/>
</joint>
```

- `axis` define la dirección positiva del movimiento.
- `lower` y `upper` definen el intervalo permitido.
- `effort` define el esfuerzo máximo.
- `velocity` define la velocidad máxima.
- En articulaciones prismáticas, las posiciones se expresan en metros.

Si se invierte `axis`, hay que revisar también el signo de los límites para conservar el movimiento físico esperado.

## Compilación

Desde la raíz del workspace:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install \
  --packages-select robot_description bandeja_description
source install/setup.bash
```

## Validación de cambios

Después de editar `robot.xacro`:

```bash
ros2 run xacro xacro \
  "$(ros2 pkg prefix robot_description)/share/robot_description/urdf/robot.xacro" \
  -o /tmp/robot.urdf
check_urdf /tmp/robot.urdf
```

Después de editar `bandeja.xacro`:

```bash
ros2 run xacro xacro \
  "$(ros2 pkg prefix bandeja_description)/share/bandeja_description/urdf/bandeja.xacro" \
  -o /tmp/bandeja.urdf
check_urdf /tmp/bandeja.urdf
```

Ejecuta también las pruebas declaradas en ambos paquetes:

```bash
colcon test --packages-select robot_description bandeja_description
colcon test-result --verbose
```

## Convenciones de desarrollo

- Mantener los nombres de enlaces y articulaciones sincronizados entre Xacro, transmisiones y configuraciones de control.
- No editar las mallas STL como texto.
- Usar rutas de recursos basadas en `$(find nombre_del_paquete)`.
- Recompilar y volver a cargar `install/setup.bash` después de agregar archivos o cambiar `setup.py`.
- Validar el URDF antes de abrir RViz2 o Gazebo.

La guía general está en [`../README.md`](../README.md) y los comandos paso a paso en [`../README_pasos.md`](../README_pasos.md).
