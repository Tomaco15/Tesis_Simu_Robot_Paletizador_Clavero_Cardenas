import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node

def generate_launch_description():
    # El nombre del paquete es intento_3_description (definido en package.xml)
    pkg_share = get_package_share_directory('intento_3_description')
    
    # Ruta al archivo xacro
    xacro_file = os.path.join(pkg_share, 'urdf', 'intento_3.xacro')

    # Ruta por defecto del archivo de configuración de RViz
    default_rviz_config_path = os.path.join(pkg_share, 'config', 'urdf.rviz')

    # Declarar argumento para cambiar la configuración de RViz2 si es necesario
    rviz_config_arg = DeclareLaunchArgument(
        name='rvizconfig',
        default_value=default_rviz_config_path,
        description='Ruta absoluta al archivo de configuración de RViz2'
    )

    return LaunchDescription([
        rviz_config_arg,
        
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
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
            output='screen',
            arguments=['-d', LaunchConfiguration('rvizconfig')]
        )
    ])
