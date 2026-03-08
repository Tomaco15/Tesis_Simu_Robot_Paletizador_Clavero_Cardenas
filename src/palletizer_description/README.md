# Correr primeras simulaciones
Para pdoer correr las priemras simulaciones es encesario estar en el directrorio src , (eje: cd .../...../src)

## opcional ; para remover la compilacion anterior:
rm -rf build/ install/ log/

## Compilar
 ### Para una compilar mas rapida y solo visualizar el robot
 colcon build --packages-select palletizer_description --symlink-install
 ### Para un compilado completo
 colcon build 
## Carga el proyecto:
 source install/setup.bash

## Correr launcher de rviz para visualizacion del robot y movimientos simples de ejes
ros2 launch palletizer_description display.launch.py

 ### Pasos en Rviz
 Si todo sale bien deveria salir la pestaña de rviz y la pestana de Join State Publicher (es el controlador de las articualciones del robot carteciano).

 #### seguir los sigueintes pasos:
 - cambiar en Fixed Frame : map --> base_link
 - Add --> RobotModel 
 - en RobotModel seleccionar --> Description Topic --> palletizer_description
 - finalmente seleccionar Join State Puplicher y mover los ejes.
    nota: con el click izquierdo y derecho se navega en el partado de vizualizacion del robot.

## Correr launcher de gazebo 
### ejecutar el comando que le enseña la ruta de la uvicacion de las piezas a Gazebo:
export IGN_GAZEBO_RESOURCE_PATH=$IGN_GAZEBO_RESOURCE_PATH:~/proyectos/Tesis_Simu_Robot_Paletizador_Clavero_Cardenas/install/palletizer_description/share/ 
### avilitar el reloj
ros2 run ros_gz_bridge parameter_bridge /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock
### Lanzar gazebo
ros2 launch palletizer_description gazebo.launch.py
 ### Pasos en gazebo
 Si todo sale bien deveria abrirse la pestaña del gazebo
  #### seguir los sigueintes pasos:
 - en abir una nueva pestñla de la teminal y correr el codigo correspondiente:
 - 
 - 
 - 