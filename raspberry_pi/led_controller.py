import time
import serial
import json
import os
from rpi_ws281x import ws, Color, Adafruit_NeoPixel

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

    def handle_led_command(self, command, params=None):
        """Handle LED control commands."""
        try:
            if command == "WHOAMI":
                return "LED"
            
            elif command == "GET_CONFIG":
                return f"CONFIG:{json.dumps(self.config)}"
            
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