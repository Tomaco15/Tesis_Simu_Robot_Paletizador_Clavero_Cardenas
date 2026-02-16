import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_description():
    # 1. Ruta al archivo URDF (o Xacro)
    package_name = 'robot_description' # Cambia si usas otro nombre
    urdf_file = os.path.join(get_package_share_directory(package_name), 'urdf', 'robot.urdf')

    with open(urdf_file, 'r') as infp:
        robot_desc = infp.read()

    return LaunchDescription([
        # Publica el estado del robot basado en el URDF
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_desc}]
        ),
        # Abre una interfaz gráfica para mover las articulaciones manualmente
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui'
        ),
        # Abre RViz2
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen'
        )
    ])