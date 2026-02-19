import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

class ControladorPaletizador(Node):
    def __init__(self):
        super().__init__('nodo_cerebro_paletizador')
        # Creamos el publicador que hablará con tus motores virtuales
        self.publisher_ = self.create_publisher(
            JointTrajectory,
            '/paletizador_controller/joint_trajectory',
            10)
        
        # Le damos 2 segundos al nodo para conectarse a Gazebo antes de enviar la orden
        self.timer = self.create_timer(2.0, self.ejecutar_movimiento)
        self.movimiento_enviado = False

    def ejecutar_movimiento(self):
        if self.movimiento_enviado:
            return # Si ya se movió, no hacemos nada más
        
        msg = JointTrajectory()
        # ¡Estos nombres deben coincidir exactamente con los de tu .xacro!
        msg.joint_names = ['Eje x', 'Eje y', 'Eje z', 'muneca']
        
        punto = JointTrajectoryPoint()
        
        # Coordenadas de destino: X, Y, Z, Muñeca
        # Prueba cambiar estos números más adelante para probar nuevas posiciones
        punto.positions = [0.2, -0.3, -0.6, 0.0] 
        
        # Tiempo que tardará en llegar (2 segundos)
        punto.time_from_start = Duration(sec=2, nanosec=0) 
        
        msg.points.append(punto)
        
        self.publisher_.publish(msg)
        self.get_logger().info('🤖 ¡Coordenadas enviadas! Iniciando secuencia de paletizado...')
        self.movimiento_enviado = True

def main(args=None):
    rclpy.init(args=args)
    nodo = ControladorPaletizador()
    
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    
    nodo.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()