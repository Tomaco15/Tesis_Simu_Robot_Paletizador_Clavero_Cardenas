# Correr priemras simualciones
Para pdoer correr las priemras simulaciones es encesario estar en el directrorio src , (eje: cd .../...../src)

## opcional ; para remover la compilaciona anteiror:
rm -rf build/ install/ log/

## Compilar
 colcon build --packages-select robot_description --symlink-install

## Correr launcher de rviz
ros2 launch robot_description display.launch.py

 ### Pasos en Rviz
 Si todo sale bien deveria salir la pestaña de rviz y la pestana de Join State Publicher.

 #### seguir los sigueintes pasos:
 - cambiar en Fixed Frame : map --> base_link
 - Add --> RobotModel 
 - en RobotModel seleccionar --> Description Topic --> robot_description
 - finalmente seleccionar Join State Puplicher y mover los ejes.
    nota: con el click izquierdo y derecho se navega en el partado de vizualizacion del robot.

## Correr launcher de gazebo
 ros2 launch palletizer_descroption gazebo.launch.py
 ### Pasos en gazebo
 Si todo sale bien deveria abrirse la pestaña del gazebo
  #### seguir los sigueintes pasos:
 - 
 - 
 - 
 - 