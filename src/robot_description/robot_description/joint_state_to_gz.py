import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64

class JointStateToGz(Node):
    def __init__(self):
        super().__init__('joint_state_to_gz')
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.listener_callback,
            10)
        self.pub_x = self.create_publisher(Float64, '/x_joint_cmd', 10)
        self.pub_y = self.create_publisher(Float64, '/y_joint_cmd', 10)
        self.pub_z = self.create_publisher(Float64, '/z_joint_cmd', 10)

    def listener_callback(self, msg):
        for i, name in enumerate(msg.name):
            val = Float64()
            val.data = msg.position[i]
            if name == 'x_joint':
                self.pub_x.publish(val)
            elif name == 'y_joint':
                self.pub_y.publish(val)
            elif name == 'z_joint':
                self.pub_z.publish(val)

def main(args=None):
    rclpy.init(args=args)
    node = JointStateToGz()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
