import time
import serial
import json
import os
import threading
from rpi_ws281x import ws, Color, Adafruit_NeoPixel
from effects.rainbow_wave import rainbow_wave
from effects.grouped_rainbow_wave import rainbow_wave_group, rainbow_wave_individual_group

# Map effect types to functions
EFFECT_MAP = {
    'RAINBOW_WAVE': rainbow_wave,
    'GROUP_RAINBOW_WAVE': rainbow_wave_group,
    'INDIVIDUAL_GROUP_RAINBOW_WAVE': rainbow_wave_individual_group,
    # Add other effects here as needed
}

class LEDServer:
    def __init__(self):
        # Load LED configuration
        self.config = self.load_config()
        
        # Initialize LED strips based on config
        self.strips = {}
        for strip_config in self.config['strips']:
            strip_id = str(strip_config['id'])
            # Get strip type from ws module
            strip_type_name = strip_config.get('type', 'SK6812_STRIP_GRBW') # Default to GRBW
            strip_type = getattr(ws, strip_type_name, ws.SK6812_STRIP_GRBW)
            
            strip = Adafruit_NeoPixel(
                strip_config['count'],
                strip_config['pin'],
                strip_config['freq_hz'],
                strip_config['dma'],
                strip_config['invert'],
                strip_config['brightness'],
                strip_config['channel'],
                strip_type
            )
            # Initialize the library (must be called once before other functions).
            strip.begin()
            self.strips[strip_id] = strip
        
        # Initialize serial connection
        self.serial = None
        self.running = False
        
        # Effect tracking: {strip_id: {'type': str, 'params': dict, 'thread': Thread, 'stop_event': Event}}
        self.active_effects = {}
        self._lock = threading.Lock() # Lock for thread-safe access to active_effects

    def load_config(self):
        """Load LED configuration from file."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'led_config.json')
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            raise  # Re-raise the exception instead of returning a default config

    def update_strip(self, strip, color=None, brightness=None):
        """Update a single strip with new color or brightness."""
        if brightness is not None:
            strip.setBrightness(brightness)
            
        if color is not None:
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, color)
                
        strip.show()
        return True

    def set_group_color(self, strip, leds, color):
        """Set color for a specific group of LEDs.
        
        Args:
            strip: The LED strip object
            leds: List of LED indices to update
            color: Color to set the LEDs to
        """
        for led in leds:
            strip.setPixelColor(led, color)
        strip.show()
        return True

    def validate_config(self, config):
        """Validate LED configuration format and values."""
        try:
            if not isinstance(config, dict) or 'strips' not in config:
                return False, "Invalid config format: missing 'strips' key"
                
            required_strip_fields = ['id', 'name', 'count', 'pin', 'freq_hz', 'dma', 
                                   'brightness', 'invert', 'channel', 'type']
            
            for strip in config['strips']:
                # Check all required fields exist
                missing_fields = [field for field in required_strip_fields if field not in strip]
                if missing_fields:
                    return False, f"Strip missing required fields: {missing_fields}"
                
                # Validate field types and ranges
                if not isinstance(strip['count'], int) or strip['count'] <= 0:
                    return False, "Invalid LED count"
                if not isinstance(strip['pin'], int):
                    return False, "Invalid pin number"
                if not isinstance(strip['brightness'], int) or not 0 <= strip['brightness'] <= 255:
                    return False, "Invalid brightness value"
                if not isinstance(strip['channel'], int) or not 0 <= strip['channel'] <= 1:
                    return False, "Invalid channel number"
                if not hasattr(ws, strip['type']):
                    return False, f"Invalid strip type: {strip['type']}"
                
            return True, "Config validation successful"
            
        except Exception as e:
            return False, f"Config validation error: {str(e)}"

    def save_config_to_file(self, config):
        """Save configuration to file."""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'led_config.json')
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            return True, "Config saved successfully"
        except Exception as e:
            return False, f"Error saving config: {str(e)}"

    def reinitialize_strips(self, new_config):
        """Reinitialize LED strips with new configuration."""
        try:
            # Stop all running effects before reinitializing
            self.stop_all_effects()

            # Turn off all current strips
            for strip in self.strips.values():
                self.update_strip(strip, color=Color(0, 0, 0))
            
            # Clear current strips
            self.strips.clear()
            
            # Initialize new strips
            for strip_config in new_config['strips']:
                strip_id = str(strip_config['id'])
                strip_type = getattr(ws, strip_config['type'])
                
                strip = Adafruit_NeoPixel(
                    strip_config['count'],
                    strip_config['pin'],
                    strip_config['freq_hz'],
                    strip_config['dma'],
                    strip_config['invert'],
                    strip_config['brightness'],
                    strip_config['channel'],
                    strip_type
                )
                strip.begin()
                self.strips[strip_id] = strip
                
            return True, "Strips reinitialized successfully"
        except Exception as e:
            return False, f"Error reinitializing strips: {str(e)}"

    def stop_effect(self, strip_id):
        """Stop effect on a specific strip."""
        with self._lock:
            if strip_id in self.active_effects:
                effect_info = self.active_effects.pop(strip_id)
                stop_event = effect_info.get('stop_event')
                thread = effect_info.get('thread')
            else:
                print(f"No active effect found for strip_id {strip_id} to stop.")
                return # Exit if no effect found

        if stop_event:
            stop_event.set() # Signal the thread to stop

        if thread and thread.is_alive():
            thread.join() # Wait for the thread to finish
            print(f"Effect thread for strip {strip_id} stopped.")

        # Turn off the strip after the effect has stopped
        if strip_id in self.strips:
            print(f"Turning off strip {strip_id} after stopping effect.")
            strip = self.strips[strip_id]
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, Color(0, 0, 0))
            strip.show()
        else:
             print(f"Strip {strip_id} not found for turning off.")

    def stop_all_effects(self):
        """Stop all running effects."""
        print("Stopping all effects...")
        with self._lock:
            strip_ids = list(self.active_effects.keys())
            effects_to_stop = list(self.active_effects.values())
            self.active_effects.clear() # Clear immediately to prevent new effects starting

        stop_events = [info.get('stop_event') for info in effects_to_stop if info.get('stop_event')]
        threads = [info.get('thread') for info in effects_to_stop if info.get('thread')]

        # Signal all threads to stop
        for event in stop_events:
            event.set()

        # Wait for all threads to finish
        for thread in threads:
            if thread.is_alive():
                thread.join()

        print("All effect threads stopped. Turning off strips.")
        # Turn off all strips that had effects
        with self._lock: # Use lock although active_effects is cleared, good practice
             for strip_id in strip_ids:
                 if strip_id in self.strips:
                     strip = self.strips[strip_id]
                     for i in range(strip.numPixels()):
                         strip.setPixelColor(i, Color(0, 0, 0))
                     strip.show()
                 else:
                    print(f"Strip {strip_id} not found during stop_all_effects cleanup.")
        print("All effects stopped and strips turned off.")

    def _run_effect_thread(self, strip_id, effect_type, params, stop_event):
        """Wrapper function to run an effect in a dedicated thread."""
        if strip_id not in self.strips:
            print(f"Error: Strip {strip_id} not found for effect {effect_type}.")
            return

        strip = self.strips[strip_id]
        effect_func = EFFECT_MAP.get(effect_type)

        if not effect_func:
            print(f"Error: Unknown effect type '{effect_type}'.")
            return

        print(f"Starting effect '{effect_type}' on strip {strip_id}.")
        try:
            # Prepare arguments for the effect function
            effect_args = {'strip': strip}
            # Add parameters specific to the effect type
            if effect_type == 'RAINBOW_WAVE':
                effect_args['wait_ms'] = params.get('wait_ms', 20)
            elif effect_type == 'GROUP_RAINBOW_WAVE':
                effect_args['group_set'] = params.get('groups', [])
                effect_args['wait_ms'] = params.get('wait_ms', 20)
            elif effect_type == 'INDIVIDUAL_GROUP_RAINBOW_WAVE':
                effect_args['group'] = params.get('leds', [])
                effect_args['wait_ms'] = params.get('wait_ms', 20)
            # Add other effect params here

            # Add the stop_event
            effect_args['stop_event'] = stop_event

            # Call the effect function
            effect_func(**effect_args)

        except Exception as e:
            print(f"Error running effect {effect_type} on strip {strip_id}: {e}")
            # Ensure the strip is turned off if the effect crashes
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, Color(0, 0, 0))
            strip.show()
        finally:
            print(f"Effect '{effect_type}' on strip {strip_id} finished.")
            # Ensure effect is removed from active_effects if thread ends unexpectedly
            with self._lock:
                if strip_id in self.active_effects:
                    # Check if it's the same effect instance before removing
                    # (Could have been stopped and restarted quickly)
                    current_info = self.active_effects.get(strip_id)
                    if current_info and current_info.get('stop_event') == stop_event:
                         print(f"Cleaning up active_effects entry for strip {strip_id} after thread exit.")
                         del self.active_effects[strip_id]

    def start_effect(self, strip_id, effect_type, params):
        """Start a new effect in its own thread."""
        if strip_id not in self.strips:
            return f"ERROR:Invalid strip ID {strip_id}"
        if effect_type not in EFFECT_MAP:
             return f"ERROR:Unknown effect type {effect_type}"

        # Stop any existing effect on the same strip first
        self.stop_effect(strip_id)

        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._run_effect_thread,
            args=(strip_id, effect_type, params, stop_event),
            daemon=True # Allows program to exit even if threads are running
        )

        with self._lock:
            self.active_effects[strip_id] = {
                'type': effect_type,
                'params': params,
                'thread': thread,
                'stop_event': stop_event
            }

        thread.start()
        return f"OK:Effect {effect_type} started on strip {strip_id}"

    def handle_led_command(self, command, params=None):
        """Handle LED control commands."""
        try:
            if command == "WHOAMI":
                return "LED"
            
            elif command == "GET_CONFIG":
                return f"CONFIG:{json.dumps(self.config)}"
            
            elif command == "UPDATE_CONFIG":
                if not params:
                    return "ERROR:UPDATE_CONFIG_REQUIRES_JSON_DATA"
                    
                try:
                    # Join all parameters back together as they might contain colons
                    config_json = ':'.join(params)
                    new_config = json.loads(config_json)
                    
                    # Validate config format and values
                    valid, message = self.validate_config(new_config)
                    if not valid:
                        return f"ERROR:{message}"
                    
                    # Save config to file
                    saved, message = self.save_config_to_file(new_config)
                    if not saved:
                        return f"ERROR:{message}"
                    
                    # Update current config
                    self.config = new_config
                    
                    # Reinitialize strips with new config
                    success, message = self.reinitialize_strips(new_config)
                    if not success:
                        return f"ERROR:{message}"
                    
                    return "OK:CONFIG_UPDATED"
                    
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")  # Debug print
                    return "ERROR:INVALID_JSON_FORMAT"
                except Exception as e:
                    print(f"Error processing UPDATE_CONFIG: {e}") # Debug print
                    return f"ERROR:Unexpected error processing config update: {e}"
            
            elif command == "EXIT":
                print("Exit command received, shutting down...")
                self.running = False
                return "OK:EXITING"
            
            elif command == "COLOR":
                # Parse COLOR:strip_id:r,g,b format
                if not params or len(params) < 2:
                    return "ERROR:COLOR_REQUIRES_STRIP_AND_RGB"
                try:
                    strip_id = params[0]
                    r, g, b = map(int, params[1].split(','))
                    
                    if not all(0 <= x <= 255 for x in (r, g, b)):
                        return "ERROR:COLOR_VALUES_MUST_BE_0_TO_255"
                    
                    color = Color(r, g, b)
                    if strip_id.upper() == "ALL":
                        # Update all strips
                        for strip in self.strips.values():
                            self.update_strip(strip, color=color)
                    elif strip_id in self.strips:
                        self.update_strip(self.strips[strip_id], color=color)
                    else:
                        return "ERROR:INVALID_STRIP_ID"
                    
                    return "OK:COLOR_SET"
                except ValueError:
                    return "ERROR:COLOR_VALUES_MUST_BE_INTEGERS"
                
            elif command == "BRIGHTNESS":
                # Parse BRIGHTNESS:strip_id:value format
                if not params or len(params) < 2:
                    return "ERROR:BRIGHTNESS_REQUIRES_STRIP_AND_VALUE"
                try:
                    strip_id = params[0]
                    brightness = int(params[1])
                    if not 0 <= brightness <= 255:
                        return "ERROR:BRIGHTNESS_MUST_BE_0_TO_255"
                    
                    if strip_id.upper() == "ALL":
                        # Update all strips
                        for strip in self.strips.values():
                            self.update_strip(strip, brightness=brightness)
                    elif strip_id in self.strips:
                        self.update_strip(self.strips[strip_id], brightness=brightness)
                    else:
                        return "ERROR:INVALID_STRIP_ID"
                    
                    return "OK:BRIGHTNESS_SET"
                except ValueError:
                    return "ERROR:BRIGHTNESS_MUST_BE_INTEGER"
                
            elif command == "OFF":
                # Turn off all strips
                for strip in self.strips.values():
                    self.update_strip(strip, color=Color(0, 0, 0))
                return "OK:LEDS_OFF"
                
            elif command == "TEST":
                # Simple test pattern - white flash
                for strip in self.strips.values():
                    self.update_strip(strip, color=Color(0, 0, 0))
                for strip in self.strips.values():
                    self.update_strip(strip, color=Color(255, 255, 255))
                time.sleep(0.5)
                for strip in self.strips.values():
                    self.update_strip(strip, color=Color(0, 0, 0))
                return "OK:TEST_COMPLETE"
                
            elif command == "GROUP_COLOR":
                # Format: GROUP_COLOR:strip_id:led1,led2,led3...:r,g,b
                if not params or len(params) < 3:
                    return "ERROR:GROUP_COLOR_REQUIRES_STRIP_LEDS_AND_RGB"
                try:
                    strip_id = params[0]
                    leds = [int(x) for x in params[1].split(',')]
                    r, g, b = map(int, params[2].split(','))
                    
                    if not all(0 <= x <= 255 for x in (r, g, b)):
                        return "ERROR:COLOR_VALUES_MUST_BE_0_TO_255"
                    
                    if strip_id not in self.strips:
                        return "ERROR:INVALID_STRIP_ID"
                    
                    color = Color(r, g, b)
                    self.set_group_color(self.strips[strip_id], leds, color)
                    return "OK:GROUP_COLOR_SET"
                        
                except ValueError:
                    return "ERROR:INVALID_PARAMETERS"
                
            elif command == "STOP_EFFECT":
                # Format: STOP_EFFECT:strip_id
                if not params:
                    return "ERROR:STOP_EFFECT_REQUIRES_STRIP_ID"
                strip_id = params[0]
                if strip_id not in self.strips:
                    return "ERROR:INVALID_STRIP_ID"
                self.stop_effect(strip_id)
                return "OK:EFFECT_STOPPED"

            elif command == "RAINBOW_WAVE":
                # Format: RAINBOW_WAVE:strip_id:wait_ms
                if not params or len(params) < 2:
                    return "ERROR:RAINBOW_WAVE_REQUIRES_STRIP_AND_WAIT_MS"
                try:
                    strip_id = params[0]
                    wait_ms = int(params[1])
                    
                    if strip_id not in self.strips:
                        return "ERROR:INVALID_STRIP_ID"
                    
                    # Stop any running effect on this strip
                    if strip_id in self.active_effects:
                        self.stop_effect(strip_id)
                    
                    # Start new effect
                    self.start_effect(strip_id, 'RAINBOW_WAVE', {'wait_ms': wait_ms})
                    return "OK:RAINBOW_WAVE_STARTED"
                except ValueError:
                    return "ERROR:INVALID_PARAMETERS"

            elif command == "GROUP_RAINBOW_WAVE":
                # Format: GROUP_RAINBOW_WAVE:strip_id:grouping_id:wait_ms
                if not params or len(params) < 3:
                    return "ERROR:GROUP_RAINBOW_WAVE_REQUIRES_STRIP_GROUPING_AND_WAIT_MS"
                try:
                    strip_id = params[0]
                    grouping_id = int(params[1])
                    wait_ms = int(params[2])
                    
                    if strip_id not in self.strips:
                        return "ERROR:INVALID_STRIP_ID"
                    
                    # Find the grouping in the config
                    strip_config = next((s for s in self.config['strips'] if str(s['id']) == strip_id), None)
                    if not strip_config:
                        return "ERROR:STRIP_NOT_FOUND"
                        
                    grouping = next((g for g in strip_config['group_sets'] if g['id'] == grouping_id), None)
                    if not grouping:
                        return "ERROR:GROUPING_NOT_FOUND"
                    
                    # Extract LED groups
                    groups = [group['leds'] for group in grouping['groups']]
                    
                    # Stop any running effect on this strip
                    if strip_id in self.active_effects:
                        self.stop_effect(strip_id)
                    
                    # Start new effect
                    self.start_effect(strip_id, 'GROUP_RAINBOW_WAVE', {
                        'groups': groups,
                        'wait_ms': wait_ms
                    })
                    return "OK:GROUP_RAINBOW_WAVE_STARTED"
                except ValueError:
                    return "ERROR:INVALID_PARAMETERS"

            elif command == "INDIVIDUAL_GROUP_RAINBOW_WAVE":
                # Format: INDIVIDUAL_GROUP_RAINBOW_WAVE:strip_id:grouping_id:group_id:wait_ms
                if not params or len(params) < 4:
                    return "ERROR:INDIVIDUAL_GROUP_RAINBOW_WAVE_REQUIRES_STRIP_GROUPING_GROUP_AND_WAIT_MS"
                try:
                    strip_id = params[0]
                    grouping_id = int(params[1])
                    group_id = int(params[2])
                    wait_ms = int(params[3])
                    
                    if strip_id not in self.strips:
                        return "ERROR:INVALID_STRIP_ID"
                    
                    # Find the grouping and group in the config
                    strip_config = next((s for s in self.config['strips'] if str(s['id']) == strip_id), None)
                    if not strip_config:
                        return "ERROR:STRIP_NOT_FOUND"
                        
                    grouping = next((g for g in strip_config['group_sets'] if g['id'] == grouping_id), None)
                    if not grouping:
                        return "ERROR:GROUPING_NOT_FOUND"
                        
                    group = next((g for g in grouping['groups'] if g['id'] == group_id), None)
                    if not group:
                        return "ERROR:GROUP_NOT_FOUND"
                    
                    # Stop any running effect on this strip
                    if strip_id in self.active_effects:
                        self.stop_effect(strip_id)
                    
                    # Start new effect
                    self.start_effect(strip_id, 'INDIVIDUAL_GROUP_RAINBOW_WAVE', {
                        'leds': group['leds'],
                        'wait_ms': wait_ms
                    })
                    return "OK:INDIVIDUAL_GROUP_RAINBOW_WAVE_STARTED"
                except ValueError:
                    return "ERROR:INVALID_PARAMETERS"
                    
            elif command == "START_EFFECT":
                if not params or len(params) < 2:
                    return "ERROR:START_EFFECT_REQUIRES_STRIP_ID_AND_EFFECT_TYPE"

                strip_id = params[0]
                effect_type = params[1]
                effect_params = {}
                if len(params) > 2:
                    try:
                        # Join remaining params and parse as JSON
                        params_json = ':'.join(params[2:])
                        effect_params = json.loads(params_json)
                    except json.JSONDecodeError:
                        return "ERROR:INVALID_JSON_FOR_EFFECT_PARAMS"
                    except Exception as e:
                         return f"ERROR:Could not parse effect params: {e}"

                return self.start_effect(strip_id, effect_type, effect_params)

            elif command == "STOP_ALL_EFFECTS":
                 self.stop_all_effects()
                 return "OK:All effects stopped"

            return "ERROR:UNKNOWN_COMMAND"
            
        except Exception as e:
            return f"ERROR:{str(e)}"
        
    def start(self):
        """Initialize and start the LED server."""
        try:
            # Initialize LED strips
            print("Initializing LED strips...")
            for strip in self.strips.values():
                strip.begin()
            # Turn off all strips
            for strip in self.strips.values():
                self.update_strip(strip, color=Color(0, 0, 0))
            
            # Initialize serial connection
            print("Opening serial port...")
            try:
                # Try to take over the serial port from system console
                import subprocess
                subprocess.run(['systemctl', 'stop', 'serial-getty@ttyGS0.service'], check=False)
                time.sleep(1)  # Give system time to release port
                
                self.serial = serial.Serial('/dev/ttyGS0', 115200, timeout=1)
                self.running = True
                
                print(f"LED Server started successfully on {self.serial.port}!")
                print("Send 'EXIT' to terminate")
                
            except Exception as e:
                print(f"Failed to take control of serial port: {e}")
                print("Make sure you have permission to access the serial port")
                print("You might need to run this script as root")
                return
            
            # Main loop
            while self.running:
                if self.serial.in_waiting:
                    # Read until we get a newline
                    command_line = ''
                    while True:
                        char = self.serial.read().decode('utf-8', errors='ignore')
                        if char == '\n' or char == '':
                            break
                        command_line += char
                    
                    command_line = command_line.strip()
                    if command_line:
                        print(f"Raw command received: {command_line!r}")
                        
                        if command_line.upper() == 'EXIT':
                            print("Exit command received!")
                            for strip in self.strips.values():
                                self.update_strip(strip, color=Color(0, 0, 0))
                            break
                            
                        # Parse command and parameters
                        parts = command_line.split(':')
                        command = parts[0].upper()
                        params = parts[1:] if len(parts) > 1 else []
                        
                        print(f"Received command: {command} with params: {params}")
                        response = self.handle_led_command(command, params)
                        response_bytes = f"{response}\n".encode('utf-8')
                        print(f"Sending response: {response_bytes!r}")
                        self.serial.write(response_bytes)
                        self.serial.flush()
                        
        except Exception as e:
            print(f"Error: {str(e)}")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean shutdown of server."""
        print("\nShutting down LED Server...")
        self.running = False
        # Stop all effects
        self.stop_all_effects()
        # Turn off all strips
        for strip in self.strips.values():
            self.update_strip(strip, color=Color(0, 0, 0))
        if self.serial and self.serial.is_open:
            self.serial.close()
            # Restart system console service
            try:
                import subprocess
                subprocess.run(['systemctl', 'start', 'serial-getty@ttyGS0.service'], check=False)
            except:
                pass
        print("Shutdown complete. Serial console restored.")

def main():
    server = LEDServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received...")
    finally:
        server.cleanup()

if __name__ == "__main__":
    main()