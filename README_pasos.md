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

## 9. Modificar el robot

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

## 10. Validar el Xacro

Genera un URDF y comprueba su estructura:

```bash
ros2 run xacro xacro \
  "$(ros2 pkg prefix robot_description)/share/robot_description/urdf/robot.xacro" \
  -o /tmp/robot.urdf
check_urdf /tmp/robot.urdf
```

Una validación correcta termina con el mensaje `Successfully Parsed XML`.

## 11. Ejecutar pruebas

```bash
colcon test --packages-select robot_description bandeja_description
colcon test-result --verbose
```

## 12. Compilación limpia

Si el entorno instalado quedó desactualizado, elimina únicamente los resultados generados y vuelve a compilar:

```bash
rm -rf build install log
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

No ejecutes este comando desde otro directorio: `build`, `install` y `log` deben ser los directorios generados en la raíz de este workspace.

## Resumen de comandos

| Acción | Comando |
| --- | --- |
| Compilar todo | `colcon build --symlink-install` |
| Cargar el entorno | `source install/setup.bash` |
| Robot en RViz2 | `ros2 launch robot_description display.launch.py` |
| Robot en Gazebo Classic | `ros2 launch robot_description gazebo.launch.py` |
| Bandeja en RViz2 | `ros2 launch bandeja_description display.launch.py` |
| Bandeja en Gazebo Sim | `ros2 launch bandeja_description gazebo.launch.py` |
