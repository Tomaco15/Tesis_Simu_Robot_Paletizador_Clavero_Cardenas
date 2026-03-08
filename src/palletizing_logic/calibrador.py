import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
import sys

# =========================================================
# 🎯 CAMBIA ESTOS NÚMEROS Y GUARDA EL ARCHIVO
# =========================================================
PRUEBA_X = 0.20   # Límite: -0.40 a 0.20
PRUEBA_Y = -0.05  # Límite: -0.75 a 0.71
# =========================================================

class CalibradorManual(Node):
    def __init__(self):
        super().__init__('nodo_calibrador')
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
        # ¡AQUÍ ESTÁ LA MAGIA! Le enviamos los 4 nombres para que no entre en pánico
        msg.joint_names = ['Eje x', 'Eje y', 'Eje z', 'muneca']
        
        punto = JointTrajectoryPoint()
        
        # Posiciones: [X, Y, Z (arriba seguro), Muñeca (abierta)]
        punto.positions = [float(PRUEBA_X), float(PRUEBA_Y), -0.6, 0.08]
        punto.time_from_start = Duration(sec=2, nanosec=0)
        
        msg.points.append(punto)
        self.publisher_.publish(msg)
        
        self.get_logger().info(f'🎯 Motores enviados a -> X: {PRUEBA_X} | Y: {PRUEBA_Y}')
        self.enviado = True
        
        self.timer_apagado = self.create_timer(3.0, self.apagar)

    def apagar(self):
        self.get_logger().info('✅ Movimiento completado. Puedes cambiar los números y volver a ejecutar.')
        sys.exit(0)

def main(args=None):
    rclpy.init(args=args)
    nodo = CalibradorManual()
    try:
        rclpy.spin(nodo)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        pass
    nodo.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()