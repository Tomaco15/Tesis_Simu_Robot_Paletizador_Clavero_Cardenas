import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node

def generate_launch_description():
    # Este deve contener el nombre del paquete y la ruta al archivo xacro
    pkg_share = get_package_share_directory('palletizer_description')
    
    # Ruta al archivo xacro
    xacro_file = os.path.join(pkg_share, 'urdf', 'palletizer.xacro')

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            # ¡Corregido el nombre del parámetro a 'robot_description'!
            parameters=[{'robot_description': Command(['xacro ', xacro_file])}]
        ),
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui'
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen'
        )
    ])