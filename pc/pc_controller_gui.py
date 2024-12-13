import tkinter as tk
from tkinter import ttk
import serial.tools.list_ports
from pc_controller import LEDClient
import time

class LEDGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LED Controller")
        self.client = LEDClient()
        self.connected = False
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status Frame
        self.status_frame = ttk.LabelFrame(self.main_frame, text="Status", padding="5")
        self.status_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Connection status
        ttk.Label(self.status_frame, text="Connection:").grid(row=0, column=0, padx=5)
        self.conn_status = ttk.Label(self.status_frame, text="Disconnected", foreground="red")
        self.conn_status.grid(row=0, column=1, padx=5)
        
        # Mode status
        ttk.Label(self.status_frame, text="Mode:").grid(row=0, column=2, padx=5)
        self.mode_status = ttk.Label(self.status_frame, text="Unknown", foreground="gray")
        self.mode_status.grid(row=0, column=3, padx=5)
        
        # Control Frame
        self.control_frame = ttk.LabelFrame(self.main_frame, text="Controls", padding="5")
        self.control_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # COM Port dropdown
        self.port_var = tk.StringVar()
        self.port_dropdown = ttk.Combobox(self.control_frame, textvariable=self.port_var)
        self.port_dropdown.grid(row=0, column=0, padx=5)
        self.refresh_ports()
        
        # Connect/Disconnect button
        self.connect_btn = ttk.Button(self.control_frame, text="Connect", 
                                    command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=1, padx=5)
        
        # Test Connection button
        self.test_conn_btn = ttk.Button(self.control_frame, text="Test Connection", 
                                      command=self.test_connection, state='disabled')
        self.test_conn_btn.grid(row=0, column=2, padx=5)
        
        # Switch Mode button
        self.mode_btn = ttk.Button(self.control_frame, text="Switch Mode", 
                                 command=self.toggle_mode, state='disabled')
        self.mode_btn.grid(row=0, column=3, padx=5)
        
        # LED Control Frame
        self.led_frame = ttk.LabelFrame(self.main_frame, text="LED Controls", padding="5")
        self.led_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # RGB controls
        self.r_var = tk.StringVar(value="0")
        self.g_var = tk.StringVar(value="0")
        self.b_var = tk.StringVar(value="0")
        
        # RGB entries
        ttk.Label(self.led_frame, text="R:").grid(row=0, column=0, padx=2)
        self.r_entry = ttk.Entry(self.led_frame, width=5, textvariable=self.r_var)
        self.r_entry.grid(row=0, column=1, padx=2)
        
        ttk.Label(self.led_frame, text="G:").grid(row=0, column=2, padx=2)
        self.g_entry = ttk.Entry(self.led_frame, width=5, textvariable=self.g_var)
        self.g_entry.grid(row=0, column=3, padx=2)
        
        ttk.Label(self.led_frame, text="B:").grid(row=0, column=4, padx=2)
        self.b_entry = ttk.Entry(self.led_frame, width=5, textvariable=self.b_var)
        self.b_entry.grid(row=0, column=5, padx=2)
        
        # Color button
        self.color_btn = ttk.Button(self.led_frame, text="Set Color", 
                                  command=self.set_color, state='disabled')
        self.color_btn.grid(row=0, column=6, padx=5)
        
        # Brightness control
        ttk.Label(self.led_frame, text="Brightness:").grid(row=1, column=0, columnspan=2, pady=5)
        self.brightness_var = tk.IntVar(value=128)
        self.brightness_scale = ttk.Scale(self.led_frame, from_=0, to=255, 
                                        orient=tk.HORIZONTAL, variable=self.brightness_var)
        self.brightness_scale.grid(row=1, column=2, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        self.brightness_btn = ttk.Button(self.led_frame, text="Set Brightness", 
                                       command=self.set_brightness, state='disabled')
        self.brightness_btn.grid(row=1, column=6, pady=5)
        
        # Test and Off buttons
        self.test_pattern_btn = ttk.Button(self.led_frame, text="Test Pattern", 
                                         command=self.test_pattern, state='disabled')
        self.test_pattern_btn.grid(row=2, column=0, columnspan=3, padx=5, pady=5)
        
        self.off_btn = ttk.Button(self.led_frame, text="Turn Off", 
                                 command=self.turn_off, state='disabled')
        self.off_btn.grid(row=2, column=4, columnspan=3, padx=5, pady=5)

    def refresh_ports(self):
        """Refresh the list of available COM ports."""
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.port_dropdown['values'] = ports
        if ports and not self.port_var.get():
            self.port_var.set(ports[0])

    def update_status(self, connected=None, mode=None):
        """Update status indicators."""
        if connected is not None:
            self.conn_status['text'] = "Connected" if connected else "Disconnected"
            self.conn_status['foreground'] = "green" if connected else "red"
            
        if mode is not None:
            self.mode_status['text'] = mode
            if mode == "LED":
                self.mode_status['foreground'] = "blue"
            elif mode == "Terminal":
                self.mode_status['foreground'] = "orange"
            else:
                self.mode_status['foreground'] = "gray"

    def toggle_connection(self):
        """Connect or disconnect from serial port."""
        if not self.connected:
            try:
                print("Attempting to connect...")
                self.client.port = self.port_var.get()
                if self.client.connect():
                    print("Connection successful!")
                    self.connected = True
                    self.connect_btn['text'] = "Disconnect"
                    self.test_conn_btn['state'] = 'normal'
                    self.mode_btn['state'] = 'normal'
                    self.port_dropdown['state'] = 'disabled'
                    
                    # Get and update mode
                    connected, mode = self.client.test_connection()
                    self.update_status(connected=True, mode=mode)
                    
                    # Enable LED controls if in LED mode
                    if mode == "LED":
                        self.enable_led_controls()
                    else:
                        self.disable_led_controls()
                    
                else:
                    print("Connection failed!")
                    self.update_status(connected=False, mode="Not Connected")
                    
            except Exception as e:
                print(f"Connection error: {e}")
                self.connected = False
                self.update_status(connected=False, mode="Error")
        else:
            self.client.disconnect()
            self.connected = False
            self.connect_btn['text'] = "Connect"
            self.test_conn_btn['state'] = 'disabled'
            self.mode_btn['state'] = 'disabled'
            self.port_dropdown['state'] = 'normal'
            self.update_status(connected=False, mode="Unknown")
            self.disable_led_controls()

    def test_connection(self):
        """Test connection and update status."""
        try:
            connected, mode = self.client.test_connection()
            self.update_status(connected=connected, mode=mode)
            
            # Enable/disable LED controls based on mode
            if connected and mode == "LED":
                self.enable_led_controls()
            else:
                self.disable_led_controls()
                
        except Exception as e:
            print(f"Test connection error: {e}")
            self.update_status(connected=False, mode="Error")
            self.disable_led_controls()

    def toggle_mode(self):
        """Switch between LED and Terminal modes."""
        try:
            # First test current mode
            connected, mode = self.client.test_connection()
            if not connected:
                print("Cannot switch mode: not connected")
                return
            
            # Disable all controls during mode switch
            self.test_conn_btn['state'] = 'disabled'
            self.mode_btn['state'] = 'disabled'
            self.disable_led_controls()
            
            if mode == "LED":
                # Send EXIT command to stop LED service
                response = self.client.send_command("EXIT")
                print(f"Exit command response: {response}")
                print("Waiting for LED service to stop...")
                time.sleep(3)  # Give more time for service to fully stop
            else:
                # Start LED service
                cmd = "sudo systemctl restart led-controller.service"
                self.client.send_command(cmd)
                print("Waiting for LED service to start...")
                time.sleep(5)  # Give more time for service to fully start
            
            # Test new mode
            connected, new_mode = self.client.test_connection()
            self.update_status(connected=connected, mode=new_mode)
            
            # Re-enable controls based on new state
            self.test_conn_btn['state'] = 'normal'
            self.mode_btn['state'] = 'normal'
            
            # Enable/disable LED controls based on new mode
            if connected and new_mode == "LED":
                self.enable_led_controls()
            else:
                self.disable_led_controls()
                
        except Exception as e:
            print(f"Error toggling mode: {e}")
            self.update_status(mode="Error")
            # Re-enable basic controls even on error
            self.test_conn_btn['state'] = 'normal'
            self.mode_btn['state'] = 'normal'

    def enable_led_controls(self):
        """Enable LED control buttons."""
        for widget in [self.color_btn, self.brightness_btn, self.test_pattern_btn, 
                      self.off_btn, self.brightness_scale, self.r_entry, 
                      self.g_entry, self.b_entry]:
            widget['state'] = 'normal'

    def disable_led_controls(self):
        """Disable LED control buttons."""
        for widget in [self.color_btn, self.brightness_btn, self.test_pattern_btn, 
                      self.off_btn, self.brightness_scale, self.r_entry, 
                      self.g_entry, self.b_entry]:
            widget['state'] = 'disabled'

    def set_color(self):
        """Set LED color."""
        try:
            r = int(self.r_var.get())
            g = int(self.g_var.get())
            b = int(self.b_var.get())
            
            response = self.client.set_color(r, g, b)
            print(f"Color command response: {response}")
            
            if "ERROR" in response:
                print(f"Error setting color: {response}")
            
        except ValueError:
            print("Invalid color values - must be integers between 0-255")
        except Exception as e:
            print(f"Error setting color: {e}")

    def set_brightness(self):
        """Set LED brightness."""
        try:
            brightness = self.brightness_var.get()
            response = self.client.set_brightness(brightness)
            if "ERROR" in response:
                print(f"Error setting brightness: {response}")
        except ValueError:
            print("Invalid brightness value")

    def test_pattern(self):
        """Run LED test pattern."""
        response = self.client.test_pattern()
        if "ERROR" in response:
            print(f"Error running test pattern: {response}")

    def turn_off(self):
        """Turn off LEDs."""
        response = self.client.turn_off()
        if "ERROR" in response:
            print(f"Error turning off LEDs: {response}")

def main():
    root = tk.Tk()
    app = LEDGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()