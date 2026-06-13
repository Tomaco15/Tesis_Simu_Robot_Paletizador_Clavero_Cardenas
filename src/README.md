# Instrucciones de Compilación y Lanzamiento (src)

Este directorio contiene los paquetes de ROS 2 para la simulación y control del robot paletizador. A continuación se detallan los comandos necesarios para limpiar, compilar y ejecutar los diferentes entornos.

---

## 1. Limpieza del Workspace
Si deseas realizar una compilación limpia (eliminar archivos temporales de compilaciones previas), ejecuta desde la raíz del proyecto:

```bash
rm -rf build/ install/ log/
```

---

## 2. Compilación del Paquete
Para compilar el paquete `robot_paletizador` puedes usar los siguientes comandos desde la raíz del proyecto:

* **Compilación rápida (solo el paquete del robot):**
  ```bash
  colcon build --packages-select robot_paletizador
  ```

* **Compilación en modo desarrollador (crea enlaces simbólicos a los archivos de launch/config de forma que los cambios se apliquen sin volver a compilar):**
  ```bash
  colcon build --packages-select robot_paletizador --symlink-install
  ```

* **Compilación completa (de todo el workspace):**
  ```bash
  colcon build
  ```

---

## 3. Cargar el Entorno (Sourcing)
Antes de ejecutar cualquier comando de lanzamiento, debes cargar las variables de entorno de tu workspace (ejecutar en cada terminal nueva desde la raíz):

```bash
source install/setup.bash
```

---

## 4. Visualización en RViz2
Para visualizar el robot en RViz junto con el panel interactivo para mover las articulaciones (`joint_state_publisher_gui`), ejecuta:

```bash
ros2 launch robot_paletizador display.launch.py
```

---

## 5. Simulación en Gazebo
Para cargar el robot en el simulador físico Gazebo, ejecuta:

```bash
ros2 launch robot_paletizador gazebo.launch
```
