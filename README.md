# Sistema robótico de paletizado de bandejas de arándanos

Workspace de ROS 2 para visualizar y simular un robot cartesiano de paletizado y una bandeja de cosecha. El repositorio forma parte del proyecto de tesis de Ingeniería Civil en Automatización de la Universidad del Bío-Bío.

## Autores

- Tomás Cárdenas
- Benjamín Clavero

## Alcance actual

El workspace contiene dos paquetes:

| Paquete | Propósito | Visualización y simulación |
| --- | --- | --- |
| `robot_description` | Descripción Xacro, mallas y articulaciones del robot paletizador | RViz2 y Gazebo Classic |
| `bandeja_description` | Descripción Xacro y malla de la bandeja | RViz2 y Gazebo Sim |

El objetivo general de la tesis también contempla percepción mediante visión artificial y automatización del paletizado. Este repositorio contiene actualmente la descripción y simulación de los modelos; el código de percepción no forma parte todavía de este workspace.

## Requisitos

- Ubuntu 22.04
- ROS 2 Humble
- `colcon`
- Xacro
- RViz2
- `robot_state_publisher`
- `joint_state_publisher` y `joint_state_publisher_gui`
- Gazebo Classic con `gazebo_ros` para el robot
- Gazebo Sim con `ros_gz_sim` y `ros_gz_bridge` para la bandeja

## Instalación

```bash
git clone git@github.com:Tomaco15/Tesis_Simu_Robot_Paletizador_Clavero_Cardenas.git
cd Tesis_Simu_Robot_Paletizador_Clavero_Cardenas
sudo apt update
sudo apt install python3-pip
python3 -m pip install -r requirements.txt
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

El último comando debe ejecutarse en cada terminal nueva desde la raíz del workspace.

## Ejecución rápida

### Robot en RViz2

```bash
ros2 launch robot_description display.launch.py
```

El argumento `gui` permite activar o desactivar el panel de control de articulaciones:

```bash
ros2 launch robot_description display.launch.py gui:=false
```

### Robot en Gazebo Classic

```bash
ros2 launch robot_description gazebo.launch.py
```

La simulación se inicia pausada. Presiona el botón de reproducción de Gazebo para comenzar la simulación física.

### Bandeja en RViz2

```bash
ros2 launch bandeja_description display.launch.py
```

### Bandeja en Gazebo Sim

```bash
ros2 launch bandeja_description gazebo.launch.py
```

Para una explicación paso a paso, consulta [README_pasos.md](README_pasos.md). La descripción técnica de los paquetes está en [src/README.md](src/README.md).

## Articulaciones del robot

Las distancias de las articulaciones prismáticas están expresadas en metros y las articulaciones rotacionales utilizan radianes.

| Articulación | Tipo | Límite inferior | Límite superior | Función |
| --- | --- | ---: | ---: | --- |
| `x_joint` | Prismática | `0.02` | `0.94` | Movimiento del primer carro cartesiano |
| `y_joint` | Prismática | `0.065` | `0.838` | Movimiento del segundo carro cartesiano |
| `z_joint` | Prismática | `-0.93` | `0.0` | Movimiento vertical |
| `R_joint` | Continua | Sin límite angular | Sin límite angular | Giro del cabezal |
| `Grid_DER` | Prismática | `0.0` | `0.04` | Articulación principal de la garra |
| `Grid_IZQ` | Prismática con `mimic` | `-0.04` | `0.0` | Articulación seguidora de la garra |

La garra se controla mediante `Grid_DER`. La articulación izquierda sigue a la derecha en sentido contrario:

```text
posición(Grid_IZQ) = -1 × posición(Grid_DER)
```

Esta relación se define en el Xacro con:

```xml
<mimic joint="Grid_DER" multiplier="-1" offset="0"/>
```

## Estructura del repositorio

```text
.
├── README.md
├── README_pasos.md
├── requirements.txt
└── src
    ├── README.md
    ├── robot_description
    │   ├── config
    │   ├── launch
    │   ├── meshes
    │   └── urdf
    └── bandeja_description
        ├── config
        ├── launch
        ├── meshes
        └── urdf
```

Los directorios `build/`, `install/` y `log/` son generados por `colcon` y no contienen código fuente.

## Archivos principales

- `src/robot_description/urdf/robot.xacro`: modelo completo que cargan los lanzadores del robot.
- `src/robot_description/urdf/robot.trans`: transmisiones de sus articulaciones.
- `src/robot_description/urdf/robot.gazebo`: propiedades utilizadas por Gazebo Classic.
- `src/robot_description/launch/display.launch.py`: visualización del robot en RViz2.
- `src/robot_description/launch/gazebo.launch.py`: simulación del robot en Gazebo Classic.
- `src/bandeja_description/urdf/bandeja.xacro`: modelo de la bandeja.
- `src/bandeja_description/launch/gazebo.launch.py`: simulación de la bandeja en Gazebo Sim.

## Validación y pruebas

Después de modificar un Xacro, recompila y carga nuevamente el entorno:

```bash
colcon build --symlink-install
source install/setup.bash
```

Para generar y comprobar el URDF del robot:

```bash
ros2 run xacro xacro \
  "$(ros2 pkg prefix robot_description)/share/robot_description/urdf/robot.xacro" \
  -o /tmp/robot.urdf
check_urdf /tmp/robot.urdf
```

Para ejecutar las pruebas de los paquetes:

```bash
colcon test --packages-select robot_description bandeja_description
colcon test-result --verbose
```

## Problemas frecuentes

### ROS 2 no encuentra un paquete

Comprueba que el workspace esté compilado y cargado:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 pkg list | grep description
```

### Los cambios del Xacro no aparecen

Vuelve a compilar con enlaces simbólicos y reinicia el lanzamiento:

```bash
colcon build --symlink-install --packages-select robot_description
source install/setup.bash
```

### Gazebo no inicia

Verifica qué integración requiere el modelo: el robot utiliza Gazebo Classic (`gazebo_ros`) y la bandeja utiliza Gazebo Sim (`ros_gz_sim`).

## Licencia

Este proyecto se distribuye bajo la licencia MIT. Consulta [LICENSE](LICENSE).
