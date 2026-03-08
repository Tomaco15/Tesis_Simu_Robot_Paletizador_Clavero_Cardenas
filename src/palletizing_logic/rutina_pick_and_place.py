import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

class RutinaPickAndPlace(Node):
    def __init__(self):
        super().__init__('nodo_rutina_paletizado')
        self.publisher_ = self.create_publisher(
            JointTrajectory,
            '/paletizador_controller/joint_trajectory',
            10)
        
        self.timer = self.create_timer(2.0, self.ejecutar_rutina)
        self.rutina_enviada = False

    def crear_punto(self, x, y, z, muneca, segundos):
        punto = JointTrajectoryPoint()
        punto.positions = [float(x), float(y), float(z), float(muneca)]
        punto.time_from_start = Duration(sec=segundos, nanosec=0)
        return punto

    def ejecutar_rutina(self):
        if self.rutina_enviada:
            return 
        
        msg = JointTrajectory()
        msg.joint_names = ['Eje x', 'Eje y', 'Eje z', 'muneca']
        
# =========================================================
        # 🛠️ COORDENADAS DE LOS MOTORES (No del mundo)
        # Tienes que jugar con estos valores respetando los límites de tu .xacro
        # Límite Eje X: -0.40 a 0.20
        # Límite Eje Y: -0.75 a 0.71
        # =========================================================
        Z_SEGURO = 0.5      
        Z_CAJA =  0.1       
        Z_PALLET = 0.8    
        
        # Valores de los motores para llegar a la CAJA
        MOTOR_X_CAJA = 0.1   # Ajustar mediante prueba y error
        MOTOR_Y_CAJA = -0.05   # Ajustar mediante prueba y error
        
        # Valores de los motores para llegar al PALLET
        MOTOR_X_PALLET = 0.16 # Ajustar mediante prueba y error
        MOTOR_Y_PALLET = 1  # Ajustar mediante prueba y error
        
        ABIERTO = 0.08        
        CERRADO = -0.01       
        # =========================================================

        self.get_logger().info('🚀 Iniciando secuencia automática de Pick & Place...')

        # 1. Ir a posición segura (Home)
        msg.points.append(self.crear_punto(0.0, 0.0, Z_SEGURO, ABIERTO, segundos=2))
        
        # 2. Moverse justo sobre la caja
        msg.points.append(self.crear_punto(MOTOR_X_CAJA, MOTOR_Y_CAJA, Z_SEGURO, ABIERTO, segundos=5))
        
        # 3. Bajar a la caja
        msg.points.append(self.crear_punto(MOTOR_X_CAJA, MOTOR_Y_CAJA, Z_CAJA, ABIERTO, segundos=8))
        
        # 4. Cerrar las pinzas (Agarrar)
        msg.points.append(self.crear_punto(MOTOR_X_CAJA, MOTOR_Y_CAJA, Z_CAJA, CERRADO, segundos=9))
        
        # 5. Subir con la caja
        msg.points.append(self.crear_punto(MOTOR_X_CAJA, MOTOR_Y_CAJA, Z_SEGURO, CERRADO, segundos=12))
        
        # 6. Moverse sobre el pallet
        msg.points.append(self.crear_punto(MOTOR_X_PALLET, MOTOR_Y_PALLET, Z_SEGURO, CERRADO, segundos=16))
        
        # 7. Bajar al pallet
        msg.points.append(self.crear_punto(MOTOR_X_PALLET, MOTOR_Y_PALLET, Z_PALLET, CERRADO, segundos=19))
        
        # 8. Abrir pinzas (Soltar)
        msg.points.append(self.crear_punto(MOTOR_X_PALLET, MOTOR_Y_PALLET, Z_PALLET, ABIERTO, segundos=20))
        
        # 9. Subir dejando la caja y volver a Home
        msg.points.append(self.crear_punto(0.0, 0.0, Z_SEGURO, ABIERTO, segundos=23))

        self.publisher_.publish(msg)
        self.get_logger().info('✅ ¡Coreografía enviada con éxito! Observa Gazebo.')
        self.rutina_enviada = True

def main(args=None):
    rclpy.init(args=args)
    nodo = RutinaPickAndPlace()
    try:
        rclpy.spin(nodo)
    except KeyboardInterrupt:
        pass
    nodo.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()