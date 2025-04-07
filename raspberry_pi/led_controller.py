import time
import serial
import json
import os
import threading
from rpi_ws281x import ws, Color, Adafruit_NeoPixel
from effects.rainbow_wave import rainbow_wave
from effects.grouped_rainbow_wave import rainbow_wave_group, rainbow_wave_individual_group

class LEDServer:
    def __init__(self):
        # Load LED configuration
        self.config = self.load_config()
        
        # Initialize LED strips based on config
        self.strips = {}
        for strip_config in self.config['strips']:
            strip_id = str(strip_config['id'])
            # Get strip type from ws module
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
            self.strips[strip_id] = strip
        
        # Initialize serial connection
        self.serial = None
        self.running = False
        
        # Add effect tracking
        self.active_effects = {}  # Format: {strip_id: {'type': str, 'params': dict}}
        self.effect_thread = None
        self.effects_running = False

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
        if strip_id in self.active_effects:
            del self.active_effects[strip_id]
            # Turn off the strip
            self.update_strip(self.strips[strip_id], color=Color(0, 0, 0))
            # If no more effects, stop the effect thread
            if not self.active_effects:
                self.effects_running = False
                if self.effect_thread and self.effect_thread.is_alive():
                    self.effect_thread.join()
                    self.effect_thread = None

    def stop_all_effects(self):
        """Stop all running effects."""
        self.effects_running = False
        if self.effect_thread and self.effect_thread.is_alive():
            self.effect_thread.join()
            self.effect_thread = None
        # Turn off all strips that had effects
        for strip_id in list(self.active_effects.keys()):
            self.update_strip(self.strips[strip_id], color=Color(0, 0, 0))
        self.active_effects.clear()

    def run_effects(self):
        """Main effect loop that handles all active effects."""
        while self.effects_running and self.active_effects:
            try:
                for strip_id, effect in list(self.active_effects.items()):
                    strip = self.strips[strip_id]
                    if effect['type'] == 'RAINBOW_WAVE':
                        rainbow_wave(strip, effect['params']['wait_ms'], iterations=1)
                    elif effect['type'] == 'GROUP_RAINBOW_WAVE':
                        rainbow_wave_group(strip, effect['params']['groups'], 
                                        effect['params']['wait_ms'], iterations=1)
                    elif effect['type'] == 'INDIVIDUAL_GROUP_RAINBOW_WAVE':
                        rainbow_wave_individual_group(strip, effect['params']['leds'], 
                                                   effect['params']['wait_ms'], iterations=1)
                time.sleep(0.001)  # Small delay between updates
            except Exception as e:
                print(f"Error in effect loop: {e}")
                self.stop_all_effects()
                break

    def start_effect(self, strip_id, effect_type, params):
        """Start a new effect."""
        # Add effect to active effects
        self.active_effects[strip_id] = {
            'type': effect_type,
            'params': params
        }
        
        # Start effect thread if not running
        if not self.effect_thread or not self.effect_thread.is_alive():
            self.effects_running = True
            self.effect_thread = threading.Thread(target=self.run_effects)
            self.effect_thread.start()

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
                    print(f"Update config error: {e}")  # Debug print
                    return f"ERROR:UPDATE_CONFIG_FAILED:{str(e)}"
            
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