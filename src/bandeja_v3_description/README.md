# Bandeja v3: URDF para Isaac Sim

El archivo generado es `urdf/bandeja_v3_isaac.urdf`. Contiene un único
enlace, `base_link`, sin articulaciones, y conserva la geometría, el material,
la masa y la inercia del Xacro.

Para regenerarlo desde la raíz del repositorio:

```bash
source /opt/ros/humble/setup.bash
xacro src/bandeja_v3_description/urdf/bandeja_v3.xacro \
  include_ros_extensions:=false \
  mesh_directory:=../meshes \
  -o src/bandeja_v3_description/urdf/bandeja_v3_isaac.urdf
check_urdf src/bandeja_v3_description/urdf/bandeja_v3_isaac.urdf
```

No es necesario compilar el paquete para generar este archivo. Las rutas
de las mallas son relativas: al copiar el modelo, conservar las carpetas
`urdf/` y `meshes/` juntas dentro de `bandeja_v3_description/`.
La escala `0.001 0.001 0.001` convierte la malla de milímetros a metros.

La exportación excluye las extensiones ROS/Gazebo. El Xacro mantiene estas
extensiones por defecto y usa rutas `package://bandeja_v3_description/meshes`
para los lanzadores ROS existentes.
