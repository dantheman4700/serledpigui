import tkinter as tk
from tkinter import ttk
import serial.tools.list_ports
from pc_controller import LEDClient
import time
from tkinter import colorchooser

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
        
        # Add config editor button to control frame
        self.config_btn = ttk.Button(self.control_frame, text="Edit Config",
                                    command=self.open_config_editor, state='disabled')
        self.config_btn.grid(row=0, column=4, padx=5)
        
        # LED Control Frame
        self.led_frame = ttk.LabelFrame(self.main_frame, text="LED Controls", padding="5")
        self.led_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Strip selection
        ttk.Label(self.led_frame, text="Strip:").grid(row=0, column=0, padx=2)
        self.strip_var = tk.StringVar(value="All Strips")
        self.strip_name_to_id = {'All Strips': 'ALL'}
        self.strip_dropdown = ttk.Combobox(self.led_frame, textvariable=self.strip_var, 
                                         state='readonly', width=10)
        self.strip_dropdown['values'] = ['All Strips']
        self.strip_dropdown.grid(row=0, column=1, columnspan=2, padx=2)
        self.strip_dropdown.bind('<<ComboboxSelected>>', self.on_strip_selected)
        
        # RGB controls
        self.r_var = tk.StringVar(value="0")
        self.g_var = tk.StringVar(value="0")
        self.b_var = tk.StringVar(value="0")
        
        # RGB entries
        ttk.Label(self.led_frame, text="R:").grid(row=1, column=0, padx=2)
        self.r_entry = ttk.Entry(self.led_frame, width=5, textvariable=self.r_var)
        self.r_entry.grid(row=1, column=1, padx=2)
        
        ttk.Label(self.led_frame, text="G:").grid(row=1, column=2, padx=2)
        self.g_entry = ttk.Entry(self.led_frame, width=5, textvariable=self.g_var)
        self.g_entry.grid(row=1, column=3, padx=2)
        
        ttk.Label(self.led_frame, text="B:").grid(row=1, column=4, padx=2)
        self.b_entry = ttk.Entry(self.led_frame, width=5, textvariable=self.b_var)
        self.b_entry.grid(row=1, column=5, padx=2)
        
        # Choose Color button
        self.choose_color_btn = ttk.Button(self.led_frame, text="Choose Color",
                                         command=self.open_color_chooser, state='disabled')
        self.choose_color_btn.grid(row=1, column=6, padx=5, pady=5)
        
        # Color button
        self.color_btn = ttk.Button(self.led_frame, text="Set Color", 
                                  command=self.set_color, state='disabled')
        self.color_btn.grid(row=1, column=7, padx=5, pady=5)
        
        # Brightness control
        ttk.Label(self.led_frame, text="Brightness:").grid(row=2, column=0, pady=5)
        self.brightness_var = tk.IntVar(value=128)
        self.brightness_scale = ttk.Scale(self.led_frame, from_=0, to=255, 
                                        orient=tk.HORIZONTAL, variable=self.brightness_var)
        self.brightness_scale.grid(row=2, column=1, columnspan=5, sticky=(tk.W, tk.E), pady=5, padx=2)
        self.brightness_btn = ttk.Button(self.led_frame, text="Set Brightness", 
                                       command=self.set_brightness, state='disabled')
        self.brightness_btn.grid(row=2, column=6, pady=5, padx=5)
        
        # Test and Off buttons
        self.test_pattern_btn = ttk.Button(self.led_frame, text="Test Pattern", 
                                         command=self.test_pattern, state='disabled')
        self.test_pattern_btn.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky=tk.W)
        
        self.off_btn = ttk.Button(self.led_frame, text="Turn Off", 
                                 command=self.turn_off, state='disabled')
        self.off_btn.grid(row=3, column=3, columnspan=4, padx=5, pady=5, sticky=tk.E)
        
        # Group Control Frame
        self.group_frame = ttk.LabelFrame(self.main_frame, text="Group Controls", padding="5")
        self.group_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Grouping selection
        ttk.Label(self.group_frame, text="Grouping:").grid(row=0, column=0, padx=2)
        self.grouping_var = tk.StringVar()
        self.grouping_dropdown = ttk.Combobox(self.group_frame, textvariable=self.grouping_var, 
                                            state='readonly', width=15)
        self.grouping_dropdown.grid(row=0, column=1, columnspan=2, padx=2)
        self.grouping_dropdown.bind('<<ComboboxSelected>>', self.update_group_dropdown)
        
        # Group selection
        ttk.Label(self.group_frame, text="Group:").grid(row=0, column=3, padx=2)
        self.group_var = tk.StringVar()
        self.group_dropdown = ttk.Combobox(self.group_frame, textvariable=self.group_var, 
                                         state='readonly', width=15)
        self.group_dropdown.grid(row=0, column=4, columnspan=2, padx=2)
        
        # RGB controls for group
        self.group_r_var = tk.StringVar(value="0")
        self.group_g_var = tk.StringVar(value="0")
        self.group_b_var = tk.StringVar(value="0")
        
        ttk.Label(self.group_frame, text="R:").grid(row=1, column=0, padx=2, pady=5)
        self.group_r_entry = ttk.Entry(self.group_frame, width=5, textvariable=self.group_r_var)
        self.group_r_entry.grid(row=1, column=1, padx=2, pady=5)
        
        ttk.Label(self.group_frame, text="G:").grid(row=1, column=2, padx=2, pady=5)
        self.group_g_entry = ttk.Entry(self.group_frame, width=5, textvariable=self.group_g_var)
        self.group_g_entry.grid(row=1, column=3, padx=2, pady=5)
        
        ttk.Label(self.group_frame, text="B:").grid(row=1, column=4, padx=2, pady=5)
        self.group_b_entry = ttk.Entry(self.group_frame, width=5, textvariable=self.group_b_var)
        self.group_b_entry.grid(row=1, column=5, padx=2, pady=5)
        
        # Group color button
        self.group_color_btn = ttk.Button(self.group_frame, text="Set Group Color", 
                                        command=self.set_group_color, state='disabled')
        self.group_color_btn.grid(row=1, column=6, padx=5, pady=5)
        
        # Disable group controls initially
        self.disable_group_controls()
        
        # Effects Frame
        self.effects_frame = ttk.LabelFrame(self.main_frame, text="Effects", padding="5")
        self.effects_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Animation speed control
        ttk.Label(self.effects_frame, text="Animation Speed (ms):").grid(row=0, column=0, padx=2)
        self.animation_speed_var = tk.StringVar(value="20")
        self.animation_speed_entry = ttk.Entry(self.effects_frame, width=5, textvariable=self.animation_speed_var)
        self.animation_speed_entry.grid(row=0, column=1, padx=2)
        
        # Active Effects Frame
        self.active_effects_frame = ttk.LabelFrame(self.effects_frame, text="Active Effects", padding="5")
        self.active_effects_frame.grid(row=0, column=2, rowspan=5, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5)
        
        # Active effects listbox
        self.active_effects_listbox = tk.Listbox(self.active_effects_frame, height=4, width=40)
        self.active_effects_listbox.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        # Start Strip Effect button (moved)
        self.start_strip_effect_btn = ttk.Button(self.active_effects_frame, text="Start Strip Effect", 
                                               command=self.start_strip_effect, state='disabled')
        self.start_strip_effect_btn.grid(row=1, column=0, padx=2, pady=2)
        
        # Start Group Set Effect button (moved)
        self.start_group_set_effect_btn = ttk.Button(self.active_effects_frame, text="Start Group Set Effect", 
                                                   command=self.start_group_set_effect, state='disabled')
        self.start_group_set_effect_btn.grid(row=2, column=0, padx=2, pady=2)

        # Start Group Effect button (moved)
        self.start_group_effect_btn = ttk.Button(self.active_effects_frame, text="Start Group Effect", 
                                               command=self.start_group_effect, state='disabled')
        self.start_group_effect_btn.grid(row=3, column=0, padx=2, pady=2)
        
        # Stop All Effects button
        self.stop_all_effects_btn = ttk.Button(self.active_effects_frame, text="Stop All", 
                                             command=self.stop_all_effects, state='disabled')
        self.stop_all_effects_btn.grid(row=3, column=1, padx=2, pady=2) # Adjusted column
        
        # Strip Effects
        ttk.Label(self.effects_frame, text="Strip Effect:").grid(row=1, column=0, padx=2)
        self.strip_effect_var = tk.StringVar()
        self.strip_effect_dropdown = ttk.Combobox(self.effects_frame, textvariable=self.strip_effect_var, 
                                                state='readonly', width=20)
        self.strip_effect_dropdown['values'] = ['Rainbow Wave']  # Add more effects here
        self.strip_effect_dropdown.grid(row=1, column=1, padx=2)
        
        # Group Set Effects
        ttk.Label(self.effects_frame, text="Group Set Effect:").grid(row=2, column=0, padx=2)
        self.group_set_effect_var = tk.StringVar()
        self.group_set_effect_dropdown = ttk.Combobox(self.effects_frame, textvariable=self.group_set_effect_var, 
                                                    state='readonly', width=20)
        self.group_set_effect_dropdown['values'] = ['Rainbow Wave']  # Add more effects here
        self.group_set_effect_dropdown.grid(row=2, column=1, padx=2)
        
        # Individual Group Effects
        ttk.Label(self.effects_frame, text="Group Effect:").grid(row=3, column=0, padx=2)
        self.group_effect_var = tk.StringVar()
        self.group_effect_dropdown = ttk.Combobox(self.effects_frame, textvariable=self.group_effect_var, 
                                                state='readonly', width=20)
        self.group_effect_dropdown['values'] = ['Rainbow Wave']  # Add more effects here
        self.group_effect_dropdown.grid(row=3, column=1, padx=2)

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
                if self.client.connect():  # This already includes the test_connection
                    print("Connection successful!")
                    self.connected = True
                    self.connect_btn['text'] = "Disconnect"
                    self.test_conn_btn['state'] = 'normal'
                    self.mode_btn['state'] = 'normal'
                    self.port_dropdown['state'] = 'disabled'
                    
                    # Get current mode from client's last test_connection result
                    self.update_status(connected=True, mode=self.client.last_mode)
                    
                    # Enable LED controls if in LED mode
                    if self.client.last_mode == "LED":
                        self.update_strip_dropdown()  # Update strip options
                        self.enable_led_controls()
                        self.enable_group_controls()  # Enable group controls too
                        self.update_grouping_dropdown()  # Initialize grouping options
                    else:
                        self.disable_led_controls()
                        self.disable_group_controls()
                    
                    # Enable config editor when connected
                    self.config_btn['state'] = 'normal'
                    
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
            self.disable_group_controls()
            self.config_btn['state'] = 'disabled'

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
                # Request config after switching to LED mode
                if self.client.get_config():
                    print("Configuration received successfully!")
                    self.update_strip_dropdown()  # Update strip options
                    self.enable_led_controls()
                    self.enable_group_controls()  # Enable group controls too
                    self.update_grouping_dropdown()  # Initialize grouping options
                else:
                    print("Warning: Failed to get LED configuration")
                    self.disable_led_controls()
                    self.disable_group_controls()
            else:
                self.disable_led_controls()
                self.disable_group_controls()
                
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
                      self.g_entry, self.b_entry, self.strip_dropdown,
                      self.choose_color_btn,
                      self.animation_speed_entry, self.strip_effect_dropdown,
                      self.group_set_effect_dropdown, self.group_effect_dropdown,
                      self.start_strip_effect_btn, self.start_group_set_effect_btn,
                      self.start_group_effect_btn, self.stop_all_effects_btn]:
            if widget in [self.strip_dropdown, self.strip_effect_dropdown, 
                        self.group_set_effect_dropdown, self.group_effect_dropdown]:
                widget['state'] = 'readonly'
            else:
                widget['state'] = 'normal'
            
            # Set initial values for effect dropdowns
            if not self.strip_effect_var.get():
                self.strip_effect_var.set('Rainbow Wave')
            if not self.group_set_effect_var.get():
                self.group_set_effect_var.set('Rainbow Wave')
            if not self.group_effect_var.get():
                self.group_effect_var.set('Rainbow Wave')

    def disable_led_controls(self):
        """Disable LED control buttons."""
        for widget in [self.color_btn, self.brightness_btn, self.test_pattern_btn, 
                      self.off_btn, self.brightness_scale, self.r_entry, 
                      self.g_entry, self.b_entry, self.strip_dropdown,
                      self.choose_color_btn,
                      self.animation_speed_entry, self.strip_effect_dropdown,
                      self.group_set_effect_dropdown, self.group_effect_dropdown,
                      self.start_strip_effect_btn, self.start_group_set_effect_btn,
                      self.start_group_effect_btn, self.stop_all_effects_btn]:
            widget['state'] = 'disabled'

    def set_color(self):
        """Set LED color."""
        try:
            r = int(self.r_var.get())
            g = int(self.g_var.get())
            b = int(self.b_var.get())
            
            # Convert display name to strip ID
            strip_name = self.strip_var.get()
            strip_id = self.strip_name_to_id.get(strip_name, 'ALL')
            
            response = self.client.set_strip_color(strip_id, r, g, b)
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
            
            # Convert display name to strip ID
            strip_name = self.strip_var.get()
            strip_id = self.strip_name_to_id.get(strip_name, 'ALL')
            
            response = self.client.set_strip_brightness(strip_id, str(brightness))
            print(f"Brightness command response: {response}")
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

    def update_strip_dropdown(self):
        """Update strip dropdown with available strips from config."""
        if self.client.config:
            # Create a mapping of display names to strip IDs
            self.strip_name_to_id = {'All Strips': 'ALL'}
            for strip in self.client.config['strips']:
                self.strip_name_to_id[strip['name']] = str(strip['id'])
            
            # Update dropdown with display names
            strip_names = ['All Strips'] + [strip['name'] for strip in self.client.config['strips']]
            self.strip_dropdown['values'] = strip_names
            
            # Set initial value
            current_id = self.strip_var.get()
            if current_id == 'ALL':
                self.strip_var.set('All Strips')
            else:
                # Find name for current ID
                for strip in self.client.config['strips']:
                    if str(strip['id']) == current_id:
                        self.strip_var.set(strip['name'])
                        break
                else:
                    self.strip_var.set('All Strips')

    def update_grouping_dropdown(self):
        """Update grouping dropdown based on selected strip."""
        strip_name = self.strip_var.get()
        if strip_name == 'All Strips':
            return
        
        strip_id = self.strip_name_to_id.get(strip_name)
        
        if strip_id and self.client.config:
            groups = self.client.get_available_groups(strip_id)
            if groups:
                self.grouping_dropdown['values'] = [g['name'] for g in groups]
                self.grouping_var.set(groups[0]['name'])
                self.update_group_dropdown()
            else:
                print(f"No groups found for strip {strip_name}")
                self.grouping_dropdown['values'] = []
                self.group_dropdown['values'] = []
                self.group_var.set('')

    def update_group_dropdown(self, event=None):
        """Update group dropdown based on selected grouping."""
        strip_name = self.strip_var.get()
        strip_id = self.strip_name_to_id.get(strip_name)
        grouping_name = self.grouping_var.get()
        
        if strip_id and grouping_name and self.client.config:
            groups = self.client.get_available_groups(strip_id)
            grouping = next((g for g in groups if g['name'] == grouping_name), None)
            if grouping:
                self.group_dropdown['values'] = [f"{g['id']}: {g['name']}" for g in grouping['groups']]
                if grouping['groups']:
                    self.group_var.set(f"{grouping['groups'][0]['id']}: {grouping['groups'][0]['name']}")

    def enable_group_controls(self):
        """Enable group control widgets."""
        for widget in [self.grouping_dropdown, self.group_dropdown, 
                      self.group_r_entry, self.group_g_entry, self.group_b_entry,
                      self.group_color_btn]:
            if widget in [self.grouping_dropdown, self.group_dropdown]:
                widget['state'] = 'readonly'
            else:
                widget['state'] = 'normal'

    def disable_group_controls(self):
        """Disable group control widgets."""
        for widget in [self.grouping_dropdown, self.group_dropdown, 
                      self.group_r_entry, self.group_g_entry, self.group_b_entry,
                      self.group_color_btn]:
            widget['state'] = 'disabled'

    def set_group_color(self):
        """Set color for selected group."""
        try:
            strip_name = self.strip_var.get()
            strip_id = self.strip_name_to_id.get(strip_name)
            group_selection = self.group_var.get()
            
            if not group_selection:
                return
                
            group_id = group_selection.split(':')[0]
            grouping_name = self.grouping_var.get()
            
            # Get the LED list for this group
            groups = self.client.get_available_groups(strip_id)
            grouping = next((g for g in groups if g['name'] == grouping_name), None)
            if not grouping:
                return
                
            group = next((g for g in grouping['groups'] if str(g['id']) == group_id), None)
            if not group:
                return
            
            try:
                r = int(self.group_r_var.get())
                g = int(self.group_g_var.get())
                b = int(self.group_b_var.get())
                
                if not all(0 <= x <= 255 for x in (r, g, b)):
                    print("Color values must be between 0-255")
                    return
                    
                response = self.client.set_group_color(strip_id, group['leds'], r, g, b)
                print(f"Group color command response: {response}")
                
            except ValueError:
                print("Invalid color values - must be integers between 0-255")
                
        except Exception as e:
            print(f"Error setting group color: {e}")

    def on_strip_selected(self, event=None):
        """Handle strip selection."""
        if self.strip_var.get() == 'All Strips':
            self.disable_group_controls()
            self.start_group_set_effect_btn['state'] = 'disabled'
            self.start_group_effect_btn['state'] = 'disabled'
        else:
            self.enable_group_controls()
            self.update_grouping_dropdown()
            self.start_group_set_effect_btn['state'] = 'normal'
            self.start_group_effect_btn['state'] = 'normal'

    def open_config_editor(self):
        """Open the configuration editor window."""
        from config_manager import ConfigEditorWindow, LEDConfigManager
        config_manager = LEDConfigManager(self.client)
        editor = ConfigEditorWindow(self.root, config_manager)

    def start_strip_effect(self):
        """Start effect on entire strip."""
        try:
            strip_name = self.strip_var.get()
            strip_id = self.strip_name_to_id.get(strip_name, 'ALL')
            effect = self.strip_effect_var.get()
            wait_ms = int(self.animation_speed_var.get())
            
            if not effect:
                print("Please select an effect")
                return
            
            if wait_ms <= 0:
                print("Animation speed must be greater than 0")
                return
            
            if effect == 'Rainbow Wave':
                response = self.client.start_rainbow_wave(strip_id, wait_ms)
                print(f"Strip effect response: {response}")
                if "ERROR" in response:
                    print(f"Error starting strip effect: {response}")
                elif "OK" in response:
                    print("Effect started successfully")
                    self.update_active_effects_list()
            else:
                print(f"Unknown effect: {effect}")
        except ValueError:
            print("Invalid animation speed - must be a positive integer")
        except Exception as e:
            print(f"Error starting strip effect: {e}")

    def start_group_set_effect(self):
        """Start effect on group set."""
        try:
            strip_name = self.strip_var.get()
            if strip_name == 'All Strips':
                print("Please select a specific strip for group effects")
                return
                
            strip_id = self.strip_name_to_id.get(strip_name)
            grouping_name = self.grouping_var.get()
            effect = self.group_set_effect_var.get()
            
            if not grouping_name:
                print("Please select a grouping")
                return
                
            # Find grouping ID
            groups = self.client.get_available_groups(strip_id)
            grouping = next((g for g in groups if g['name'] == grouping_name), None)
            if not grouping:
                print("Selected grouping not found")
                return
                
            wait_ms = int(self.animation_speed_var.get())
            
            if effect == 'Rainbow Wave':
                response = self.client.start_group_rainbow_wave(strip_id, grouping['id'], wait_ms)
                print(f"Group set effect response: {response}")
                if "ERROR" in response:
                    print(f"Error starting group set effect: {response}")
                elif "OK" in response:
                    print("Effect started successfully")
                    self.update_active_effects_list()
            else:
                print(f"Unknown effect: {effect}")
        except ValueError:
            print("Invalid animation speed - must be a positive integer")
        except Exception as e:
            print(f"Error starting group set effect: {e}")

    def start_group_effect(self):
        """Start effect on individual group."""
        try:
            strip_name = self.strip_var.get()
            if strip_name == 'All Strips':
                print("Please select a specific strip for group effects")
                return
                
            strip_id = self.strip_name_to_id.get(strip_name)
            grouping_name = self.grouping_var.get()
            group_selection = self.group_var.get()
            effect = self.group_effect_var.get()
            
            if not grouping_name or not group_selection:
                print("Please select a grouping and group")
                return
                
            # Find grouping ID and group ID
            groups = self.client.get_available_groups(strip_id)
            grouping = next((g for g in groups if g['name'] == grouping_name), None)
            if not grouping:
                print("Selected grouping not found")
                return
                
            group_id = group_selection.split(':')[0]
            wait_ms = int(self.animation_speed_var.get())
            
            if effect == 'Rainbow Wave':
                response = self.client.start_individual_group_rainbow_wave(
                    strip_id, grouping['id'], int(group_id), wait_ms)
                print(f"Individual group effect response: {response}")
                if "ERROR" in response:
                    print(f"Error starting individual group effect: {response}")
                elif "OK" in response:
                    print("Effect started successfully")
                    self.update_active_effects_list()
            else:
                print(f"Unknown effect: {effect}")
        except ValueError:
            print("Invalid animation speed - must be a positive integer")
        except Exception as e:
            print(f"Error starting individual group effect: {e}")

    def update_active_effects_list(self):
        """Update the active effects listbox."""
        self.active_effects_listbox.delete(0, tk.END)
        active_effects = self.client.get_active_effects()
        
        if not active_effects:
            self.active_effects_listbox.insert(tk.END, "No active effects")
            self.stop_all_effects_btn['state'] = 'disabled'
            return
            
        for strip_id, effect in active_effects.items():
            # Find strip name
            strip = next((s for s in self.client.config['strips'] if str(s['id']) == strip_id), None)
            strip_name = strip['name'] if strip else f"Strip {strip_id}"
            
            # Format effect info
            effect_type = effect['type'].replace('_', ' ').title()
            params = effect['params']
            if effect_type == 'Rainbow Wave':
                effect_str = f"{strip_name}: {effect_type} ({params['wait_ms']}ms)"
            elif effect_type == 'Group Rainbow Wave':
                effect_str = f"{strip_name}: {effect_type} - Group Set {params['grouping_id']} ({params['wait_ms']}ms)"
            elif effect_type == 'Individual Group Rainbow Wave':
                effect_str = f"{strip_name}: {effect_type} - Group {params['group_id']} ({params['wait_ms']}ms)"
            else:
                effect_str = f"{strip_name}: {effect_type}"
                
            self.active_effects_listbox.insert(tk.END, effect_str)
            
        self.stop_all_effects_btn['state'] = 'normal'

    def stop_all_effects(self):
        """Stop all active effects."""
        response = self.client.stop_effect()
        print(f"Stop all effects response: {response}")
        if "ERROR" in response:
            print(f"Error stopping effects: {response}")
        self.update_active_effects_list()

    def open_color_chooser(self):
        """Open color chooser dialog and update RGB fields."""
        # Askcolor returns a tuple ((r, g, b), hex_color_string) or (None, None)
        color_code = colorchooser.askcolor(title="Choose color")
        if color_code and color_code[0]:  # Check if a color was chosen
            r, g, b = color_code[0]  # Get the (r, g, b) tuple
            self.r_var.set(str(int(r)))
            self.g_var.set(str(int(g)))
            self.b_var.set(str(int(b)))

def main():
    root = tk.Tk()
    app = LEDGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()