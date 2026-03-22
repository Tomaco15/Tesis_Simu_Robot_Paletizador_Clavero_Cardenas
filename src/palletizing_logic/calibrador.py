import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
import sys

# =========================================================
# 🎯 CONFIGURACIÓN DE PRUEBA (Calibra aquí)
# =========================================================
PRUEBA_X = 0.0 # Rango propuesto: 0.0 (Adelante) a 0.6 (Atras)
PRUEBA_Y = 0.75   # Rango: -0.75  (Izquierda )a 0.75 (Derecha)
PRUEBA_Z = 0.85 # Rango: 0.85 (Abajo) a -0.05 (Arriba)
PRUEBA_MUN = 0.08  # 0.08 (Abierta) | -0.05 (Cerrada)
# =========================================================

class CalibradorPaletizador(Node):
    def __init__(self):
        super().__init__('nodo_calibrador_avanzado')
        self.publisher_ = self.create_publisher(
            JointTrajectory, 
            '/paletizador_controller/joint_trajectory', 
            10)
        self.timer = self.create_timer(1.0, self.disparar_movimiento)
        self.enviado = False

    def disparar_movimiento(self):
        if self.enviado:
            return
        
        msg = JointTrajectory()
        # Nombres exactos de tus joints en el XACRO
        msg.joint_names = ['eje_x', 'eje_y', 'eje_z', 'muneca']
        
        punto = JointTrajectoryPoint()
        
        # Mapeo de posiciones enviadas a los 4 motores
        punto.positions = [
            float(PRUEBA_X), 
            float(PRUEBA_Y), 
            float(PRUEBA_Z), 
            float(PRUEBA_MUN)
        ]
        
        # Tiempo para completar el movimiento (2 segundos para suavidad)
        punto.time_from_start = Duration(sec=2, nanosec=0)
        
        msg.points.append(punto)
        self.publisher_.publish(msg)
        
        self.get_logger().info(f'🚀 Comandos -> X:{PRUEBA_X} | Y:{PRUEBA_Y} | Z:{PRUEBA_Z} | Pinza:{PRUEBA_MUN}')
        self.enviado = True
        
        # Cierra el nodo automáticamente tras el envío
        self.create_timer(3.0, lambda: sys.exit(0))

def main(args=None):
    rclpy.init(args=args)
    nodo = CalibradorPaletizador()
    try:
        rclpy.spin(nodo)
    except SystemExit:
        pass
    nodo.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()