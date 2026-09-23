# Visualizar con_grupo_rigido en ROS 2 Humble

Desde la raíz del workspace:

```bash
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select con_grupo_rigido_description
source install/setup.bash
ros2 launch con_grupo_rigido_description display.launch.py
```

Se abren RViz y el panel `joint_state_publisher_gui`. Mueve sus deslizadores
para cambiar la posición del robot. `display.launch.py` se ejecuta mediante
`ros2 launch`, no mediante `python3`.

| Control | Rango | Unidad |
| --- | --- | --- |
| `x_joint` | 0.02 a 0.94 | m |
| `y_joint` | 0.065 a 0.838 | m |
| `z_joint` | -0.93 a 0 | m |
| `R_joint` | Giro continuo; el panel representa -π a π | rad |
| `Grid_DER` | 0 a 0.04 | m |

`Grid_IZQ` sigue automáticamente a `Grid_DER` con el signo contrario
(`mimic`), dentro del rango -0.04 a 0 m. Así se mueven las dos palas con
un solo control. Los joints de tipo `fixed` mantienen unidas las piezas y
no tienen deslizador.

Los rangos están definidos en `urdf/con_grupo_rigido.xacro` y se tomaron del modelo
`robot_description`, cuyos joints móviles tienen los mismos ejes y orígenes.
La configuración de RViz utiliza `base_link` como referencia y recibe
`/robot_description` con durabilidad `Transient Local`.

En una terminal nueva, carga ambos archivos `setup.bash` antes del lanzamiento.
Tras editar el paquete, repite la compilación y vuelve a abrir el lanzamiento.
Cierra otros lanzamientos de estos modelos antes de abrir este: comparten
los tópicos `/robot_description`, `/joint_states` y los nombres de los frames.
