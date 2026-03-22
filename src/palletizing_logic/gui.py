import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
import tkinter as tk
from tkinter import ttk
import threading
import sys

# =========================================================
# 🤖 NODO ROS2 (Comunicación)
# =========================================================
class NodoPaletizador(Node):
    def __init__(self):
        super().__init__('nodo_gui_paletizador')
        self.publisher_ = self.create_publisher(
            JointTrajectory, 
            '/paletizador_controller/joint_trajectory', 
            10)

    def enviar_movimiento(self, x, y, z, mun):
        msg = JointTrajectory()
        # 1. ACTUALIZADO: Nombres sin espacios, igual que en el Xacro y YAML
        msg.joint_names = ['eje_x', 'eje_y', 'eje_z', 'muneca']
        
        punto = JointTrajectoryPoint()
        punto.positions = [float(x), float(y), float(z), float(mun)]
        
        # 0.2 segundos para fluidez en tiempo real
        punto.time_from_start = Duration(sec=0, nanosec=200000000) 
        
        msg.points.append(punto)
        self.publisher_.publish(msg)

# =========================================================
# 🎨 INTERFAZ GRÁFICA (Tkinter)
# =========================================================
class GuiMinimalista:
    def __init__(self, root, nodo_ros):
        self.root = root
        self.nodo_ros = nodo_ros
        self.root.title("Control Paletizador Avanzado")
        
        self.root.geometry("550x350") 
        self.root.resizable(False, False)
        
        style = ttk.Style()
        style.theme_use('clam')
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Control de movimiento", font=("Arial", 12, "bold")).pack(pady=(0, 15))

        # Valores iniciales dentro de los límites del Xacro
        self.vars = {
            'eje_x': tk.DoubleVar(value=0.0),
            'eje_y': tk.DoubleVar(value=0.0),
            'eje_z': tk.DoubleVar(value=0.0),  # Inicio en 0.0 (límite superior)
            'muneca': tk.DoubleVar(value=0.0)
        }

        # 2. ACTUALIZADO: Límites sincronizados con el archivo Xacro
        self.crear_fila_control(frame, "Eje X (Adelante - Atrás)", 'eje_x', 0.0, 0.6)
        self.crear_fila_control(frame, "Eje Y (Izq - Der)", 'eje_y', -0.75, 0.71)
        self.crear_fila_control(frame, "Eje Z (Abajo - Arriba)", 'eje_z', -0.84, 0.0)
        self.crear_fila_control(frame, "Pinza (Cerrada - Abierta)", 'muneca', -0.05, 0.08)

        ttk.Button(frame, text="Volver a Inicio", command=self.reset_posiciones).pack(pady=15)

    def crear_fila_control(self, parent, label_text, var_name, min_val, max_val):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=8)
        
        ttk.Label(row, text=label_text, width=22).pack(side=tk.LEFT)
        
        entry_var = tk.StringVar(value=f"{self.vars[var_name].get():.3f}")
        entrada = ttk.Entry(row, textvariable=entry_var, width=8, justify='center')
        entrada.pack(side=tk.RIGHT, padx=5)

        slider = ttk.Scale(row, from_=min_val, to=max_val, variable=self.vars[var_name], 
                           orient=tk.HORIZONTAL, length=250)
        slider.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)

        # --- LÓGICA DE ACTUALIZACIÓN BIDIRECCIONAL ---
        def on_slider_move(val):
            entry_var.set(f"{float(val):.3f}")
            self.enviar_a_ros()
            
        slider.config(command=on_slider_move)

        def on_entry_enter(event):
            try:
                val = float(entry_var.get())
                val = max(min_val, min(val, max_val))
                
                self.vars[var_name].set(val)
                entry_var.set(f"{val:.3f}")
                self.enviar_a_ros()
                
                self.root.focus_set() 
            except ValueError:
                entry_var.set(f"{self.vars[var_name].get():.3f}")

        entrada.bind('<Return>', on_entry_enter)
        entrada.bind('<FocusOut>', on_entry_enter)

    def enviar_a_ros(self):
        # 3. ACTUALIZADO: Las llaves ahora coinciden con self.vars
        self.nodo_ros.enviar_movimiento(
            self.vars['eje_x'].get(),
            self.vars['eje_y'].get(),
            self.vars['eje_z'].get(),
            self.vars['muneca'].get()
        )

    def reset_posiciones(self):
        # 4. ACTUALIZADO: Valores de reseteo consistentes
        self.vars['eje_x'].set(0.0)
        self.vars['eje_y'].set(0.0)
        self.vars['eje_z'].set(0.0)
        self.vars['muneca'].set(0.0)
        self.root.focus_set()
        self.enviar_a_ros()

# =========================================================
# 🚀 INICIALIZACIÓN
# =========================================================
def main(args=None):
    rclpy.init(args=args)
    nodo_ros = NodoPaletizador()

    hilo_ros = threading.Thread(target=rclpy.spin, args=(nodo_ros,), daemon=True)
    hilo_ros.start()

    root = tk.Tk()
    app = GuiMinimalista(root, nodo_ros)
    
    def on_closing():
        root.destroy()
        nodo_ros.destroy_node()
        rclpy.shutdown()
        sys.exit(0)
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == '__main__':
    main()