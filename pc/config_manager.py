# config_manager.py

import json
import tkinter as tk
from tkinter import ttk, messagebox

class LEDConfigManager:
    def __init__(self, client):
        self.client = client
        self.config = None
        # Load current config from client if connected
        if client and client.config:
            self.config = client.config.copy()

    def load_config_from_file(self, filepath):
        """Load LED configuration from a local file."""
        try:
            with open(filepath, 'r') as f:
                self.config = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading config: {e}")
            return False

    def save_config_to_file(self, filepath):
        """Save current configuration to a local file."""
        if not self.config:
            return False
        try:
            with open(filepath, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def send_config_to_led(self):
        """Send configuration to LED controller and verify it was received correctly."""
        if not self.config:
            return False, "No configuration loaded"

        try:
            # Send the config
            response = self.client.send_command(f"UPDATE_CONFIG:{json.dumps(self.config)}")
            if "ERROR" in response:
                return False, response

            # Verify the config was received correctly
            verify_response = self.client.send_command("GET_CONFIG")
            if not verify_response.startswith("CONFIG:"):
                return False, "Failed to verify configuration"

            received_config = json.loads(verify_response[7:])  # Remove "CONFIG:" prefix
            if received_config == self.config:
                return True, "Configuration updated successfully"
            else:
                return False, "Configuration verification failed"
                
        except Exception as e:
            return False, f"Error sending config: {str(e)}"

class StripConfigDialog:
    def __init__(self, parent, strip_data=None):
        self.window = tk.Toplevel(parent)
        self.window.title("Strip Configuration")
        self.result = None
        
        # If strip_data is provided, we're editing an existing strip
        self.editing = strip_data is not None
        if self.editing:
            self.strip_data = strip_data.copy()
        else:
            self.strip_data = {
                'id': 1,
                'name': 'New Strip',
                'count': 30,
                'pin': 18,
                'freq_hz': 800000,
                'dma': 10,
                'brightness': 128,
                'invert': False,
                'channel': 0,
                'type': 'WS2811_STRIP_GRB',
                'group_sets': []
            }
        
        self.create_widgets()
        
    def create_widgets(self):
        # Create and pack widgets for each field
        fields = [
            ('ID', 'id', 'int'),
            ('Name', 'name', 'str'),
            ('LED Count', 'count', 'int'),
            ('GPIO Pin', 'pin', 'int'),
            ('Frequency (Hz)', 'freq_hz', 'int'),
            ('DMA Channel', 'dma', 'int'),
            ('Brightness', 'brightness', 'int'),
            ('Channel', 'channel', 'int')
        ]
        
        for i, (label, key, type_) in enumerate(fields):
            ttk.Label(self.window, text=label + ":").grid(row=i, column=0, padx=5, pady=2)
            var = tk.StringVar(value=str(self.strip_data[key]))
            entry = ttk.Entry(self.window, textvariable=var)
            entry.grid(row=i, column=1, padx=5, pady=2)
            setattr(self, f"{key}_var", var)
        
        # Invert checkbox
        self.invert_var = tk.BooleanVar(value=self.strip_data['invert'])
        ttk.Checkbutton(self.window, text="Invert Signal", 
                       variable=self.invert_var).grid(row=len(fields), column=0, 
                                                    columnspan=2, pady=2)
        
        # Strip type dropdown
        ttk.Label(self.window, text="Strip Type:").grid(row=len(fields)+1, column=0, pady=2)
        self.type_var = tk.StringVar(value=self.strip_data['type'])
        strip_types = ['WS2811_STRIP_RGB', 'WS2811_STRIP_GRB', 'WS2811_STRIP_BRG']
        type_combo = ttk.Combobox(self.window, textvariable=self.type_var, 
                                values=strip_types, state='readonly')
        type_combo.grid(row=len(fields)+1, column=1, pady=2)
        
        # Buttons
        btn_frame = ttk.Frame(self.window)
        btn_frame.grid(row=len(fields)+2, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
    def ok(self):
        try:
            # Validate and update strip_data
            self.strip_data.update({
                'id': int(self.id_var.get()),
                'name': self.name_var.get(),
                'count': int(self.count_var.get()),
                'pin': int(self.pin_var.get()),
                'freq_hz': int(self.freq_hz_var.get()),
                'dma': int(self.dma_var.get()),
                'brightness': int(self.brightness_var.get()),
                'channel': int(self.channel_var.get()),
                'invert': self.invert_var.get(),
                'type': self.type_var.get()
            })
            
            # Basic validation
            if not (0 <= self.strip_data['brightness'] <= 255):
                raise ValueError("Brightness must be between 0 and 255")
            if not (0 <= self.strip_data['channel'] <= 1):
                raise ValueError("Channel must be 0 or 1")
            if self.strip_data['count'] <= 0:
                raise ValueError("LED count must be greater than 0")
            
            self.result = self.strip_data
            self.window.destroy()
            
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
    
    def cancel(self):
        self.window.destroy()

class GroupDialog:
    def __init__(self, parent, group_data=None, led_count=30):
        self.window = tk.Toplevel(parent)
        self.window.title("Group Configuration")
        self.result = None
        self.led_count = led_count
        
        # If group_data is provided, we're editing an existing group
        self.editing = group_data is not None
        if self.editing:
            self.group_data = group_data.copy()
        else:
            self.group_data = {
                'id': 1,
                'name': 'New Group',
                'leds': []
            }
        
        self.create_widgets()
        
    def create_widgets(self):
        # Group ID and Name
        ttk.Label(self.window, text="ID:").grid(row=0, column=0, padx=5, pady=2)
        self.id_var = tk.StringVar(value=str(self.group_data['id']))
        ttk.Entry(self.window, textvariable=self.id_var).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(self.window, text="Name:").grid(row=1, column=0, padx=5, pady=2)
        self.name_var = tk.StringVar(value=self.group_data['name'])
        ttk.Entry(self.window, textvariable=self.name_var).grid(row=1, column=1, padx=5, pady=2)
        
        # LED Selection
        ttk.Label(self.window, text="LEDs:").grid(row=2, column=0, padx=5, pady=2)
        self.led_frame = ttk.Frame(self.window)
        self.led_frame.grid(row=2, column=1, padx=5, pady=2)
        
        # LED Checkboxes (in a scrollable frame)
        self.canvas = tk.Canvas(self.led_frame, width=200, height=150)
        scrollbar = ttk.Scrollbar(self.led_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create LED checkboxes
        self.led_vars = []
        for i in range(self.led_count):
            var = tk.BooleanVar(value=i in self.group_data['leds'])
            self.led_vars.append(var)
            ttk.Checkbutton(self.scrollable_frame, text=f"LED {i}", 
                          variable=var).grid(row=i//2, column=i%2, padx=5, pady=2)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons
        btn_frame = ttk.Frame(self.window)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="OK", command=self.ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel).pack(side=tk.LEFT, padx=5)
        
    def ok(self):
        try:
            # Update group data
            self.group_data.update({
                'id': int(self.id_var.get()),
                'name': self.name_var.get(),
                'leds': [i for i, var in enumerate(self.led_vars) if var.get()]
            })
            
            # Basic validation
            if not self.group_data['name'].strip():
                raise ValueError("Group name cannot be empty")
            if not self.group_data['leds']:
                raise ValueError("Group must contain at least one LED")
            
            self.result = self.group_data
            self.window.destroy()
            
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
    
    def cancel(self):
        self.window.destroy()

class ConfigEditorWindow:
    def __init__(self, parent, config_manager):
        self.window = tk.Toplevel(parent)
        self.window.title("LED Configuration Editor")
        self.config_manager = config_manager
        
        # Create the UI
        self.create_widgets()
        
        # Load current configuration
        self.load_current_config()

    def create_widgets(self):
        # Strip list
        self.strip_frame = ttk.LabelFrame(self.window, text="LED Strips", padding="5")
        self.strip_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.strip_list = tk.Listbox(self.strip_frame, width=30)
        self.strip_list.grid(row=0, column=0, sticky="nsew")
        self.strip_list.bind('<<ListboxSelect>>', self.on_strip_selected)

        # Strip buttons
        self.strip_btn_frame = ttk.Frame(self.strip_frame)
        self.strip_btn_frame.grid(row=1, column=0, pady=5)
        ttk.Button(self.strip_btn_frame, text="Add Strip", 
                  command=self.add_strip).grid(row=0, column=0, padx=2)
        ttk.Button(self.strip_btn_frame, text="Edit Strip", 
                  command=self.edit_strip).grid(row=0, column=1, padx=2)
        ttk.Button(self.strip_btn_frame, text="Remove Strip", 
                  command=self.remove_strip).grid(row=0, column=2, padx=2)

        # Group management
        self.group_frame = ttk.LabelFrame(self.window, text="Groups", padding="5")
        self.group_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Group set list
        ttk.Label(self.group_frame, text="Group Sets:").grid(row=0, column=0)
        self.group_set_list = tk.Listbox(self.group_frame, width=30, height=5, exportselection=False)
        self.group_set_list.grid(row=1, column=0, sticky="nsew", padx=5)
        self.group_set_list.bind('<<ListboxSelect>>', self.on_group_set_selected)

        # Group list
        ttk.Label(self.group_frame, text="Groups:").grid(row=2, column=0)
        self.group_list = tk.Listbox(self.group_frame, width=30, height=10, exportselection=False)
        self.group_list.grid(row=3, column=0, sticky="nsew", padx=5)
        self.group_list.bind('<<ListboxSelect>>', self.on_group_selected)

        # Group set buttons
        self.group_set_btn_frame = ttk.Frame(self.group_frame)
        self.group_set_btn_frame.grid(row=4, column=0, pady=5)
        ttk.Button(self.group_set_btn_frame, text="Add Group Set", 
                  command=self.add_group_set).grid(row=0, column=0, padx=2)
        ttk.Button(self.group_set_btn_frame, text="Edit Group Set", 
                  command=self.edit_group_set).grid(row=0, column=1, padx=2)
        ttk.Button(self.group_set_btn_frame, text="Remove Group Set", 
                  command=self.remove_group_set).grid(row=0, column=2, padx=2)

        # Group buttons
        self.group_btn_frame = ttk.Frame(self.group_frame)
        self.group_btn_frame.grid(row=5, column=0, pady=5)
        ttk.Button(self.group_btn_frame, text="Add Group", 
                  command=self.add_group).grid(row=0, column=0, padx=2)
        ttk.Button(self.group_btn_frame, text="Edit Group", 
                  command=self.edit_group).grid(row=0, column=1, padx=2)
        ttk.Button(self.group_btn_frame, text="Remove Group", 
                  command=self.remove_group).grid(row=0, column=2, padx=2)

        # Action buttons
        self.action_frame = ttk.Frame(self.window, padding="5")
        self.action_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Button(self.action_frame, text="Save", 
                  command=self.save_config).grid(row=0, column=0, padx=5)
        ttk.Button(self.action_frame, text="Send to LED Controller", 
                  command=self.send_to_led).grid(row=0, column=1, padx=5)

    def load_current_config(self):
        """Load and display current configuration."""
        if self.config_manager.config:
            self.update_strip_list()
            
    def update_strip_list(self):
        """Update the strip listbox with current strips."""
        self.strip_list.delete(0, tk.END)
        if self.config_manager.config:
            for strip in self.config_manager.config['strips']:
                self.strip_list.insert(tk.END, f"{strip['id']}: {strip['name']}")

    def add_strip(self):
        """Add a new LED strip."""
        dialog = StripConfigDialog(self.window)
        self.window.wait_window(dialog.window)
        if dialog.result:
            if not self.config_manager.config:
                self.config_manager.config = {'strips': []}
            self.config_manager.config['strips'].append(dialog.result)
            self.update_strip_list()

    def edit_strip(self):
        """Edit selected LED strip."""
        selection = self.strip_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a strip to edit")
            return
            
        strip_idx = selection[0]
        strip_data = self.config_manager.config['strips'][strip_idx]
        
        dialog = StripConfigDialog(self.window, strip_data)
        self.window.wait_window(dialog.window)
        if dialog.result:
            self.config_manager.config['strips'][strip_idx] = dialog.result
            self.update_strip_list()

    def remove_strip(self):
        """Remove selected LED strip."""
        selection = self.strip_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a strip to remove")
            return
            
        if messagebox.askyesno("Confirm Remove", "Are you sure you want to remove this strip?"):
            strip_idx = selection[0]
            del self.config_manager.config['strips'][strip_idx]
            self.update_strip_list()

    def on_strip_selected(self, event):
        """Handle strip selection."""
        selection = self.strip_list.curselection()
        if selection:
            strip_text = self.strip_list.get(selection[0])
            strip_id = int(strip_text.split(':')[0])
            strip = next((s for s in self.config_manager.config['strips'] if s['id'] == strip_id), None)
            if strip:
                self.current_strip_id = strip_id
                self.update_group_sets(strip)
                self.group_list.delete(0, tk.END)

    def on_group_set_selected(self, event):
        """Handle group set selection."""
        # Restore strip selection if needed
        if hasattr(self, 'current_strip_id') and not self.strip_list.curselection():
            for i in range(self.strip_list.size()):
                strip_text = self.strip_list.get(i)
                if int(strip_text.split(':')[0]) == self.current_strip_id:
                    self.strip_list.selection_set(i)
                    break

        strip, group_set = self.get_selected_group_set()
        if strip and group_set:
            self.update_groups(group_set)

    def update_group_sets(self, strip):
        """Update group set list for selected strip."""
        current_selection = None
        if self.group_set_list.curselection():
            current_selection = self.group_set_list.get(self.group_set_list.curselection()[0])
        
        self.group_set_list.delete(0, tk.END)
        self.group_list.delete(0, tk.END)
        
        if 'group_sets' in strip:
            for i, group_set in enumerate(strip['group_sets']):
                display_text = f"{group_set['id']}: {group_set['name']}"
                self.group_set_list.insert(tk.END, display_text)
                if current_selection == display_text:
                    self.group_set_list.selection_set(i)
                    self.on_group_set_selected(None)

    def get_selected_group_set(self):
        """Helper method to get the currently selected group set."""
        strip_sel = self.strip_list.curselection()
        group_set_sel = self.group_set_list.curselection()
        
        # Try to get strip either from selection or stored ID
        strip = None
        if strip_sel:
            strip_text = self.strip_list.get(strip_sel[0])
            strip_id = int(strip_text.split(':')[0])
            strip = next((s for s in self.config_manager.config['strips'] if s['id'] == strip_id), None)
        elif hasattr(self, 'current_strip_id'):
            strip = next((s for s in self.config_manager.config['strips'] 
                        if s['id'] == self.current_strip_id), None)
        
        if not strip or not group_set_sel:
            return None, None
            
        # Get group set by ID
        group_set_text = self.group_set_list.get(group_set_sel[0])
        group_set_id = int(group_set_text.split(':')[0])
        group_set = next((gs for gs in strip['group_sets'] if gs['id'] == group_set_id), None)
        
        return strip, group_set

    def update_groups(self, group_set):
        """Update group list for selected group set."""
        self.group_list.delete(0, tk.END)
        if 'groups' in group_set:
            for group in group_set['groups']:
                self.group_list.insert(tk.END, f"{group['id']}: {group['name']}")

    def add_group_set(self):
        """Add a new group set to selected strip."""
        selection = self.strip_list.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a strip first")
            return
            
        name = self.prompt_name("New Group Set")
        if name:
            strip = self.config_manager.config['strips'][selection[0]]
            if 'group_sets' not in strip:
                strip['group_sets'] = []
            
            new_id = max([gs['id'] for gs in strip['group_sets']], default=0) + 1
            strip['group_sets'].append({
                'id': new_id,
                'name': name,
                'groups': []
            })
            self.update_group_sets(strip)

    def edit_group_set(self):
        """Edit selected group set."""
        strip, group_set = self.get_selected_group_set()
        if not (strip and group_set):
            messagebox.showwarning("No Selection", "Please select a group set to edit")
            return
            
        name = self.prompt_name("Edit Group Set", group_set['name'])
        if name:
            group_set['name'] = name
            self.update_group_sets(strip)

    def remove_group_set(self):
        """Remove selected group set."""
        strip, group_set = self.get_selected_group_set()
        if not (strip and group_set):
            messagebox.showwarning("No Selection", "Please select a group set to remove")
            return
            
        if messagebox.askyesno("Confirm Remove", "Are you sure you want to remove this group set?"):
            strip['group_sets'].remove(group_set)
            self.update_group_sets(strip)

    def prompt_name(self, title, default=""):
        """Prompt user for a name."""
        dialog = tk.Toplevel(self.window)
        dialog.title(title)
        
        name_var = tk.StringVar(value=default)
        ttk.Entry(dialog, textvariable=name_var).pack(padx=5, pady=5)
        
        result = [None]
        
        def ok():
            result[0] = name_var.get()
            dialog.destroy()
            
        def cancel():
            dialog.destroy()
            
        ttk.Button(dialog, text="OK", command=ok).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(dialog, text="Cancel", command=cancel).pack(side=tk.LEFT, padx=5, pady=5)
        
        dialog.wait_window()
        return result[0]

    def save_config(self):
        """Save current config to file."""
        success = self.config_manager.save_config_to_file("led_config.json")
        if success:
            messagebox.showinfo("Success", "Configuration saved successfully")
        else:
            messagebox.showerror("Error", "Failed to save configuration")

    def send_to_led(self):
        """Send config to LED controller."""
        success, message = self.config_manager.send_config_to_led()
        if success:
            messagebox.showinfo("Success", message)
        else:
            messagebox.showerror("Error", message)

    def add_group(self):
        """Add a new group to selected group set."""
        strip, group_set = self.get_selected_group_set()
        if not (strip and group_set):
            messagebox.showwarning("No Selection", "Please select a strip and group set first")
            return
        
        dialog = GroupDialog(self.window, led_count=strip['count'])
        self.window.wait_window(dialog.window)
        if dialog.result:
            # Set new group ID
            if group_set['groups']:
                dialog.result['id'] = max(g['id'] for g in group_set['groups']) + 1
            else:
                dialog.result['id'] = 1
            group_set['groups'].append(dialog.result)
            self.update_groups(group_set)

    def edit_group(self):
        """Edit selected group."""
        strip, group_set = self.get_selected_group_set()
        group_sel = self.group_list.curselection()
        
        if not (strip and group_set and group_sel):
            messagebox.showwarning("No Selection", "Please select a group to edit")
            return
            
        # Get group by ID from the selected item
        group_text = self.group_list.get(group_sel[0])
        group_id = int(group_text.split(':')[0])
        group = next((g for g in group_set['groups'] if g['id'] == group_id), None)
        
        if not group:
            messagebox.showerror("Error", "Selected group not found")
            return
        
        dialog = GroupDialog(self.window, group, strip['count'])
        self.window.wait_window(dialog.window)
        if dialog.result:
            # Replace the group in the list
            idx = next(i for i, g in enumerate(group_set['groups']) if g['id'] == group_id)
            group_set['groups'][idx] = dialog.result
            self.update_groups(group_set)

    def remove_group(self):
        """Remove selected group."""
        strip, group_set = self.get_selected_group_set()
        group_sel = self.group_list.curselection()
        
        if not (strip and group_set and group_sel):
            messagebox.showwarning("No Selection", "Please select a group to remove")
            return
            
        # Get group by ID from the selected item
        group_text = self.group_list.get(group_sel[0])
        group_id = int(group_text.split(':')[0])
        
        if messagebox.askyesno("Confirm Remove", "Are you sure you want to remove this group?"):
            # Remove the group with matching ID
            group_set['groups'] = [g for g in group_set['groups'] if g['id'] != group_id]
            self.update_groups(group_set)

    def on_group_selected(self, event):
        """Handle group selection."""
        # This can be used to show group details if needed
        pass
