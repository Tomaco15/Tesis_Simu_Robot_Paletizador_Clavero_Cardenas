# Guía de compilación y ejecución

Esta guía reúne los comandos necesarios para preparar, compilar y ejecutar el workspace. Todos los comandos, salvo que se indique lo contrario, deben ejecutarse desde la raíz del repositorio.

## 1. Preparar ROS 2

Abre una terminal y carga ROS 2 Humble:

```bash
source /opt/ros/humble/setup.bash
```

Comprueba que ROS 2 esté disponible:

```bash
ros2 --help
```

## 2. Instalar dependencias

Instala `pip` y las dependencias Python del proyecto:

```bash
sudo apt update
sudo apt install python3-pip
python3 -m pip install -r requirements.txt
```

Si `rosdep` todavía no está inicializado en el equipo:

```bash
sudo rosdep init
rosdep update
```

Instala las dependencias declaradas por los paquetes:

```bash
rosdep install --from-paths src --ignore-src -r -y
```

El proyecto utiliza dos integraciones de Gazebo:

- `gazebo_ros` para simular `robot_description` en Gazebo Classic.
- `ros_gz_sim` y `ros_gz_bridge` para simular `bandeja_description` en Gazebo Sim.

Si alguna no está instalada, agrega los paquetes correspondientes para ROS 2 Humble:

```bash
sudo apt update
sudo apt install \
  python3-colcon-common-extensions \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-joint-state-publisher-gui \
  ros-humble-ros-gz-bridge \
  ros-humble-ros-gz-sim \
  ros-humble-rviz2 \
  ros-humble-xacro
```

## 3. Compilar

Para compilar todo el workspace:

```bash
colcon build --symlink-install
```

Para compilar únicamente los paquetes de descripción:

```bash
colcon build --symlink-install \
  --packages-select robot_description bandeja_description
```

## 4. Cargar el workspace

Después de cada compilación, y en cada terminal nueva, ejecuta:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
```

Comprueba que ambos paquetes sean visibles:

```bash
ros2 pkg prefix robot_description
ros2 pkg prefix bandeja_description
```

## 5. Visualizar el robot en RViz2

```bash
ros2 launch robot_description display.launch.py
```

El panel `joint_state_publisher_gui` permite mover las articulaciones dentro de los límites configurados. La garra presenta un solo control independiente: `Grid_DER`; `Grid_IZQ` sigue su movimiento con factor `-1`.

Para abrir RViz2 sin el panel gráfico:

```bash
ros2 launch robot_description display.launch.py gui:=false
```

## 6. Simular el robot en Gazebo Classic

```bash
ros2 launch robot_description gazebo.launch.py
```

El servidor se inicia pausado. Cuando aparezca el robot, usa el botón de reproducción de Gazebo para habilitar la física.

## 7. Visualizar la bandeja en RViz2

```bash
ros2 launch bandeja_description display.launch.py
```

## 8. Simular la bandeja en Gazebo Sim

```bash
ros2 launch bandeja_description gazebo.launch.py
```

El lanzador inicia un mundo vacío, publica la descripción y crea la bandeja aproximadamente cinco segundos después.

## 9. Importar el robot en NVIDIA Isaac Sim

Utiliza el archivo URDF puro:

```text
src/robot_description/urdf/robot_isaac.urdf
```

No es necesario compilar ni cargar ROS 2 para importarlo directamente desde el archivo:

1. Abre Isaac Sim.
2. En `Window > Extensions`, busca y habilita **URDF Importer**.
3. Abre `File > Import` y selecciona `robot_isaac.urdf`.
4. Selecciona **Static Base** para fijar la base del robot.
5. Elige el directorio donde Isaac Sim guardará el USD.
6. Pulsa **Import** y revisa posibles advertencias en `Output Log`.

El archivo espera que las mallas estén en `src/robot_description/meshes/`. Si copias el URDF fuera del repositorio, conserva esta disposición:

```text
robot_description/
├── meshes/
│   └── *.stl
└── urdf/
    └── robot_isaac.urdf
```

La articulación `Grid_IZQ` conserva la relación `mimic` con `Grid_DER` y un multiplicador de `-1`. Después de importar, verifica en Isaac Sim que ambas paletas se desplacen en sentidos opuestos.

## 10. Modificar el robot

El archivo activo del robot es:

```text
src/robot_description/urdf/robot.xacro
```

Los lanzadores `display.launch.py` y `gazebo.launch.py` procesan ese archivo. Después de modificarlo:

```bash
colcon build --symlink-install --packages-select robot_description
source install/setup.bash
ros2 launch robot_description display.launch.py
```

## 11. Validar el Xacro

Genera un URDF y comprueba su estructura:

```bash
ros2 run xacro xacro \
  "$(ros2 pkg prefix robot_description)/share/robot_description/urdf/robot.xacro" \
  -o /tmp/robot.urdf
check_urdf /tmp/robot.urdf
```

Una validación correcta termina con el mensaje `Successfully Parsed XML`.

## 12. Ejecutar pruebas

```bash
colcon test --packages-select robot_description bandeja_description
colcon test-result --verbose
```

## 13. Compilación limpia

Realiza una compilación limpia en cualquiera de estas situaciones:

- Se eliminó o renombró un archivo, pero todavía aparece dentro de `install/`.
- ROS 2 continúa utilizando una versión anterior del Xacro, URDF o `launch`.
- Una compilación fue interrumpida o terminó con artefactos inconsistentes.
- Se cambió de rama y ambas ramas tienen estructuras de paquetes diferentes.

### 13.1 Detener procesos

Cierra los lanzamientos que estén usando el workspace. Detén ROS 2, RViz o Gazebo con `Ctrl+C` en sus respectivas terminales.

### 13.2 Confirmar el directorio

Antes de ejecutar `rm -rf`, comprueba la ubicación actual:

```bash
pwd
ls
```

Debes estar en la raíz de `Tesis_Simu_Robot_Paletizador_Clavero_Cardenas`. La salida de `ls` debe mostrar al menos:

```text
src  build  install  log
```

Si no aparece `src/`, no continúes hasta volver a la raíz correcta.

### 13.3 Eliminar artefactos generados

Ejecuta:

```bash
rm -rf -- build/ install/ log/
```

El comando elimina:

- `build/`: archivos intermedios utilizados durante la compilación.
- `install/`: paquetes instalados y scripts para cargar el workspace.
- `log/`: registros creados por `colcon`.

No elimina `src/`, los README, las mallas ni el historial de Git.

### 13.4 Recompilar

Vuelve a cargar ROS 2, compila y carga el entorno reconstruido:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### Precauciones

- No ejecutes el comando desde otro directorio.
- No agregues `/`, `~`, `$HOME` ni comodines al comando.
- No es necesario utilizar `sudo`.
- Si alguno de los tres directorios no existe, `rm -rf` continuará sin producir un error.

## Resumen de comandos

| Acción | Comando |
| --- | --- |
| Compilar todo | `colcon build --symlink-install` |
| Limpiar compilación | `rm -rf -- build/ install/ log/` |
| Cargar el entorno | `source install/setup.bash` |
| Robot en RViz2 | `ros2 launch robot_description display.launch.py` |
| Robot en Gazebo Classic | `ros2 launch robot_description gazebo.launch.py` |
| Bandeja en RViz2 | `ros2 launch bandeja_description display.launch.py` |
| Bandeja en Gazebo Sim | `ros2 launch bandeja_description gazebo.launch.py` |
| Robot en Isaac Sim | `File > Import > robot_isaac.urdf` |
