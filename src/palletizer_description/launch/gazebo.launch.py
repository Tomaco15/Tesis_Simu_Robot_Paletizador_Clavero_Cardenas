import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro

def generate_launch_description():

    # 1. Definir nombres y rutas
    pkg_name = 'palletizer_description'
    file_subpath = 'urdf/palletizer.xacro'

    # 2. Procesar el archivo XACRO
    xacro_file = os.path.join(get_package_share_directory(pkg_name), file_subpath)
    robot_description_raw = xacro.process_file(xacro_file).toxml()

    # 3. Configurar Robot State Publisher
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_raw,
                     'use_sim_time': True}] 
    )

    # 4. Lanzar el NUEVO Gazebo (Ignition Fortress) con un mundo vacío
    pkg_ros_ign_gazebo = get_package_share_directory('ros_ign_gazebo')
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_ign_gazebo, 'launch', 'ign_gazebo.launch.py')
        ),
        launch_arguments={'ign_args': '-r empty.sdf'}.items(),
    )

    # 5. Spawnear el robot usando la herramienta de Ignition
    spawn_entity = Node(
        package='ros_ign_gazebo',
        executable='create',
        arguments=['-topic', 'robot_description',
                   '-name', 'paletizador',
                   '-z', '0.01'], # Elevado 1 centímetro
        output='screen'
    )

    # 6. Cargar los controladores
    load_joint_state_broadcaster = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             'joint_state_broadcaster'],
        output='screen'
    )

    load_paletizador_controller = ExecuteProcess(
        cmd=['ros2', 'control', 'load_controller', '--set-state', 'active',
             'paletizador_controller'],
        output='screen'
    )

    # 7. Crear la descripción de lanzamiento
    return LaunchDescription([
        RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=spawn_entity,
                on_exit=[load_joint_state_broadcaster, load_paletizador_controller],
            )
        ),
        gazebo,
        node_robot_state_publisher,
        spawn_entity,
    ])