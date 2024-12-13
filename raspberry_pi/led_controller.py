import time
import serial
from rpi_ws281x import ws, Color, Adafruit_NeoPixel

# LED strip configuration
LED_1_COUNT = 96
LED_1_PIN = 18
LED_1_FREQ_HZ = 800000
LED_1_DMA = 10
LED_1_BRIGHTNESS = 128
LED_1_INVERT = False
LED_1_CHANNEL = 0
LED_1_STRIP = ws.WS2811_STRIP_GRB

LED_2_COUNT = 50
LED_2_PIN = 13
LED_2_FREQ_HZ = 800000
LED_2_DMA = 5
LED_2_BRIGHTNESS = 128
LED_2_INVERT = False
LED_2_CHANNEL = 1
LED_2_STRIP = ws.WS2811_STRIP_GRB

class LEDServer:
    def __init__(self):
        # Initialize LED strips
        self.strip1 = Adafruit_NeoPixel(LED_1_COUNT, LED_1_PIN, LED_1_FREQ_HZ,
                                      LED_1_DMA, LED_1_INVERT, LED_1_BRIGHTNESS,
                                      LED_1_CHANNEL, LED_1_STRIP)
        
        self.strip2 = Adafruit_NeoPixel(LED_2_COUNT, LED_2_PIN, LED_2_FREQ_HZ,
                                      LED_2_DMA, LED_2_INVERT, LED_2_BRIGHTNESS,
                                      LED_2_CHANNEL, LED_2_STRIP)
        
        # Initialize serial connection
        self.serial = None
        self.running = False
        
    def update_strip(self, strip, color=None, brightness=None):
        """Update a single strip with new color or brightness."""
        if brightness is not None:
            strip.setBrightness(brightness)
            
        if color is not None:
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, color)
                
        strip.show()
        
    def update_both_strips(self, color=None, brightness=None):
        """Update both strips atomically."""
        if brightness is not None:
            self.strip1.setBrightness(brightness)
            self.strip2.setBrightness(brightness)
            
        if color is not None:
            for i in range(max(self.strip1.numPixels(), self.strip2.numPixels())):
                if i < self.strip1.numPixels():
                    self.strip1.setPixelColor(i, color)
                if i < self.strip2.numPixels():
                    self.strip2.setPixelColor(i, color)
                    
        # Update both strips as close together as possible
        self.strip1.show()
        self.strip2.show()
        
    def handle_led_command(self, command, params=None):
        """Handle LED control commands."""
        try:
            if command == "WHOAMI":
                return "LED"  # Special identifier for LED mode
            
            elif command == "EXIT":
                print("Exit command received, shutting down...")
                self.running = False
                return "OK:EXITING"
            
            elif command == "COLOR":
                if len(params) != 3:
                    return "ERROR:COLOR_REQUIRES_3_VALUES"
                try:
                    r, g, b = map(int, params)
                    if not all(0 <= x <= 255 for x in (r, g, b)):
                        return "ERROR:COLOR_VALUES_MUST_BE_0_TO_255"
                    
                    self.update_both_strips(color=Color(r, g, b))
                    return "OK:COLOR_SET"
                except ValueError:
                    return "ERROR:COLOR_VALUES_MUST_BE_INTEGERS"
                
            elif command == "BRIGHTNESS":
                if len(params) != 1:
                    return "ERROR:BRIGHTNESS_REQUIRES_1_VALUE"
                try:
                    brightness = int(params[0])
                    if not 0 <= brightness <= 255:
                        return "ERROR:BRIGHTNESS_MUST_BE_0_TO_255"
                    
                    self.update_both_strips(brightness=brightness)
                    return "OK:BRIGHTNESS_SET"
                except ValueError:
                    return "ERROR:BRIGHTNESS_MUST_BE_INTEGER"
                
            elif command == "OFF":
                self.update_both_strips(color=Color(0, 0, 0))
                return "OK:LEDS_OFF"
                
            elif command == "TEST":
                # Simple test pattern - white flash
                self.update_both_strips(color=Color(0, 0, 0))
                self.update_both_strips(color=Color(255, 255, 255))
                time.sleep(0.5)
                self.update_both_strips(color=Color(0, 0, 0))
                return "OK:TEST_COMPLETE"
                
            return "ERROR:UNKNOWN_COMMAND"
            
        except Exception as e:
            return f"ERROR:{str(e)}"
        
    def start(self):
        """Initialize and start the LED server."""
        try:
            # Initialize LED strips
            print("Initializing LED strips...")
            self.strip1.begin()
            self.strip2.begin()
            self.update_both_strips(color=Color(0, 0, 0))
            
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
                            self.update_both_strips(color=Color(0, 0, 0))
                            break
                            
                        # Parse command and parameters
                        parts = command_line.split(':')
                        command = parts[0].upper()
                        params = parts[1].split(',') if len(parts) > 1 else []
                        
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
        self.update_both_strips(color=Color(0, 0, 0))
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