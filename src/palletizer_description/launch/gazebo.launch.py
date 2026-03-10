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
                   '-z', '-0.1', # Elevado -10 centímetro
                   '-Y', '1.5708'],   #  Rotación de 90 grados en y para que cioncida los ejes x y z dek robot con los de la simulacion
        output='screen'
    )

    #5.1 Añadir la caja en la zona de alimentación
    spawn_caja = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-file', os.path.join(get_package_share_directory(pkg_name), 'urdf', 'caja.sdf'),
                   '-name', 'caja_1',
                   '-x', '-0.59', '-y', '0.85', '-z', '0.1'], # Coordenada dentro del alcance del robot
        output='screen'
    )

    # 5.2 Añadir el pallet en la zona de paletizado
    spawn_pallet = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=['-file', os.path.join(get_package_share_directory(pkg_name), 'urdf', 'pallet.sdf'),
                   '-name', 'base_pallet',
                   '-x', '0.69', '-y', '0.71', '-z', '0.07'], # Zona opuesta al robot
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
        spawn_caja,      
        spawn_pallet,
    ])
    bridge_node = Node(
    package='ros_gz_bridge',
    executable='parameter_bridge',
    arguments=[
        # Formato: /topico_gazebo@tipo_mensaje_ros[tipo_mensaje_gazebo
        '/camera/image_raw@sensor_msgs/msg/Image[ignition.msgs.Image',
        '/camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo'
    ],
    output='screen'
    )