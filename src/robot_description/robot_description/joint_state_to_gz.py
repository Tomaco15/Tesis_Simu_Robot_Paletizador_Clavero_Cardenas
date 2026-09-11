# Copyright 2026 Tesis_Simu_Robot_Paletizador_Clavero_Cardenas contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

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
