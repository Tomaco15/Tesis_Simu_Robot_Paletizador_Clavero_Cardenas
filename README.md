# Tesis_Simu_Robot_Paletizador_Clavero_Cardenas
# Sistema Robótico de Paletizado para Bandejas de Arándanos
**Autors:** Tomás Cárdenas y Benjamín CLavero | 
**Institución:** Universidad del Bío-Bío - Ingeniería Civil en Automatización

## Descripción
Este proyecto consiste en el desarrollo de un gemelo digital para un sistema automatizado para el ordenamiento y paletizado de bandejas de cosecha de arándanos utilizando visión artificial y control robótico.

## Tecnologías Utilizadas
* **Sistema Operativo:** Ubuntu 22.04 (Jammy Jellyfish) en WSL2.
* **Framework:** ROS 2 Humble.
* **Visión Artificial:** Python + YOLO (detección de bandejas).
* **Diseño CAD:** Modelado en Fusion 360.

## Estructura del Workspace
* `/src`: Paquetes de ROS 2 para control y percepción.
* `/models`: Exportaciones de piezas y ensambles del robot.
* `/docs`: Documentación técnica y diagramas.

## Instalación y Uso
1. Clonar el repositorio:
   `git clone gitgit@github.com:Tomaco15/Tesis_Simu_Robot_Paletizador_Clavero_Cardenas.git`
2. Compilar el espacio de trabajo:
   `colcon build`
3. Cargar el entorno:
   `source install/setup.bash`
