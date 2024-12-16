import serial
import time
import paramiko
import json

class LEDClient:
    def __init__(self, port='COM6', baudrate=115200):
        """Initialize LED client."""
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.ssh = None
        self.connected = False
        self.config = None
        self.last_mode = None
        
    def get_config(self):
        """Get LED strip configuration from the server."""
        try:
            response = self.send_command("GET_CONFIG")
            if response.startswith("CONFIG:"):
                config_json = response[7:]  # Remove "CONFIG:" prefix
                self.config = json.loads(config_json)
                return self.config
            return None
        except Exception as e:
            print(f"Error getting config: {e}")
            return None
            
    def connect(self):
        """Establish connection to LED server."""
        try:
            # First close any existing connection
            if self.serial and self.serial.is_open:
                self.serial.close()
                time.sleep(1)
            
            print(f"\nAttempting to connect to {self.port} at {self.baudrate} baud...")
            
            # List available ports
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            print("\nAvailable COM ports:")
            for p in ports:
                print(f"  {p.device} - {p.description}")

            # Try to connect
            try:
                print("\nTrying connection settings...")
                self.serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1,
                    write_timeout=1,
                    xonxoff=False,
                    rtscts=False,
                    dsrdtr=False,
                    exclusive=None
                )
                
                if self.serial.is_open:
                    print("Port opened successfully!")
                    time.sleep(0.5)
                    
                    # Clear any pending data
                    self.serial.reset_input_buffer()
                    self.serial.reset_output_buffer()
                    
                    # Test the connection and get mode
                    connected, mode = self.test_connection()
                    if connected:
                        print(f"Connected successfully in {mode} mode!")
                        self.connected = True
                        self.last_mode = mode  # Make sure mode is stored here too
                        
                        # If in LED mode, get the configuration
                        if mode == "LED":
                            if self.get_config():
                                print("Configuration received successfully!")
                                print(f"Found {len(self.config['strips'])} LED strips:")
                                for strip in self.config['strips']:
                                    print(f"  {strip['name']}: {strip['count']} LEDs")
                            else:
                                print("Warning: Failed to get LED configuration")
                                return False
                        return True
                    
                    print("Connection test failed")
                    if self.serial and self.serial.is_open:
                        self.serial.close()
                    return False
                    
            except Exception as e:
                print(f"Connection attempt failed: {e}")
                if self.serial and self.serial.is_open:
                    self.serial.close()
                return False
            
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            if self.serial and self.serial.is_open:
                self.serial.close()
            return False

    def disconnect(self):
        """Safely disconnect from LED server."""
        if self.serial and self.serial.is_open:
            try:
                self.send_command("EXIT")
                time.sleep(0.1)
                self.serial.close()
                print("Disconnected successfully!")
            except:
                print("Error during disconnect!")
        self.connected = False

    def set_strip_color(self, strip_id, r, g, b):
        """Set color for specific strip."""
        if not all(0 <= x <= 255 for x in (r, g, b)):
            return "ERROR: Color values must be between 0-255"
        if strip_id.upper() != "ALL" and not any(str(s['id']) == str(strip_id) for s in self.config['strips']):
            return "ERROR: Invalid strip ID"
        return self.send_command(f"COLOR:{strip_id}:{r},{g},{b}")

    def set_strip_brightness(self, strip_id, brightness):
        """Set brightness for specific strip."""
        if not 0 <= int(brightness) <= 255:
            return "ERROR: Brightness must be between 0-255"
        if strip_id.upper() != "ALL" and not any(str(s['id']) == str(strip_id) for s in self.config['strips']):
            return "ERROR: Invalid strip ID"
        return self.send_command(f"BRIGHTNESS:{strip_id}:{brightness}")

    def set_color(self, r, g, b):
        """Set color for all strips (legacy method)."""
        return self.set_strip_color("ALL", r, g, b)

    def set_brightness(self, brightness):
        """Set brightness for all strips (legacy method)."""
        return self.set_strip_brightness("ALL", brightness)

    def test_pattern(self):
        """Run test pattern."""
        return self.send_command("TEST")

    def turn_off(self):
        """Turn off LEDs."""
        return self.send_command("OFF")

    def test_connection(self):
        """Test if serial connection is working and determine mode."""
        try:
            if not self.serial or not self.serial.is_open:
                return False, "Not Connected"
            
            # Clear buffers
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            # Send test command and wait for response
            print("Sending test command...")
            self.serial.write(b"whoami\n")
            self.serial.flush()
            
            # Wait for response with timeout
            start_time = time.time()
            response = ''
            while (time.time() - start_time) < 2:  # 2 second timeout
                if self.serial.in_waiting:
                    char = self.serial.read().decode('utf-8', errors='ignore')
                    response += char
            
            response = response.strip()
            print(f"Raw response: {response!r}")  # Print raw response for debugging
            
            # Clean the response by removing control sequences and splitting on newlines
            cleaned_response = ''.join(c for c in response if c.isprintable() or c.isspace())
            lines = [line.strip() for line in cleaned_response.split('\n') if line.strip()]
            print(f"Cleaned lines: {lines}")  # Print cleaned lines for debugging
            
            # Check each line for our expected responses
            for line in lines:
                if line == "LED":
                    self.last_mode = "LED"
                    return True, "LED"
                elif "dan" in line or "root" in line:  # Check for terminal user
                    self.last_mode = "Terminal"
                    return True, "Terminal"
            
            self.last_mode = "Unknown"
            return True, "Unknown"
            
        except Exception as e:
            print(f"Connection test error: {e}")
            self.last_mode = "Error"
            return False, "Error"

    def start_led_service(self):
        """Start the LED service when in terminal mode."""
        try:
            # First verify we're in terminal mode
            if not self.test_led_mode():
                with serial.Serial(self.port, 115200, timeout=1) as ser:
                    cmd = "sudo systemctl start led-controller.service\n"
                    ser.write(cmd.encode())
                    ser.flush()
                    time.sleep(2)  # Wait for service to start
                    
                    # Verify service started
                    return self.test_led_mode()
            return False
        except Exception as e:
            print(f"Start LED service error: {e}")
            return False

    def stop_led_service(self):
        """Stop the LED service."""
        try:
            # First verify we're in LED mode
            if self.test_led_mode():
                with serial.Serial(self.port, 115200, timeout=1) as ser:
                    cmd = "sudo systemctl stop led-controller.service\n"
                    ser.write(cmd.encode())
                    ser.flush()
                    time.sleep(2)  # Wait for service to stop
                    
                    # Verify service stopped
                    return not self.test_led_mode()
            return False
        except Exception as e:
            print(f"Stop LED service error: {e}")
            return False

    def send_command(self, command):
        """Send a command and get response."""
        if not self.serial or not self.serial.is_open:
            return "Error: Not connected"
            
        # Validate command format
        if ':' in command:
            parts = command.split(':')
            cmd = parts[0]
            if cmd == 'COLOR':
                try:
                    if len(parts) != 3:  # Should be COLOR:strip_id:r,g,b
                        return "Error: Invalid color format. Use COLOR:strip_id:r,g,b"
                    strip_id = parts[1]
                    r, g, b = map(int, parts[2].split(','))
                    if not all(0 <= x <= 255 for x in (r, g, b)):
                        return "Error: Color values must be between 0-255"
                except:
                    return "Error: Invalid color format. Use COLOR:strip_id:r,g,b"
            elif cmd == 'BRIGHTNESS':
                try:
                    if len(parts) != 3: # Should be BRIGHTNESS:strip_id:value
                        return "Error: Invalid brightness format. Use BRIGHTNESS:strip_id:value"
                    brightness = int(parts[2])
                    if not 0 <= brightness <= 255:
                        return "Error: Brightness must be between 0-255"
                except:
                    return "Error: Invalid brightness format. Use BRIGHTNESS:strip_id:value"
            
        try:
            print(f"Sending command: {command}")
            # First clear any pending input
            self.serial.reset_input_buffer()
            # Send command with clear delimiter
            command_bytes = f"{command}\n".encode('utf-8')
            print(f"Raw bytes being sent: {command_bytes!r}")
            self.serial.write(command_bytes)
            self.serial.flush()  # Ensure all data is sent
            
            print("Waiting for response...")
            response = ''
            while True:
                if self.serial.in_waiting:
                    char = self.serial.read().decode('utf-8', errors='ignore')
                    if char == '\n' or char == '':
                        break
                    response += char
            
            response = response.strip()
            print(f"Raw response received: {response!r}")
            return response
        except Exception as e:
            return f"Error: {str(e)}"
            
    def release_serial(self):
        """Release serial control by sending escape sequence."""
        if self.serial and self.serial.is_open:
            print("Sending escape sequence...")
            for _ in range(3):
                self.serial.write(b'\x1b')
                time.sleep(0.1)
            self.serial.close()
            print("Serial control released!")

    def start_server(self):
        """Start the LED server on the Raspberry Pi via SSH."""
        try:
            # SSH connection details (you might want to make these configurable)
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect('ledpi', username='dan')  # Adjust hostname/username as needed
            
            # Start the LED controller script in the background
            cmd = 'cd ~/led_env && python led_controller.py'
            stdin, stdout, stderr = self.ssh.exec_command(cmd)
            
            # Give the server a moment to start
            time.sleep(2)
            return True
            
        except Exception as e:
            print(f"SSH Error: {e}")
            if self.ssh:
                self.ssh.close()
            return False
    
    def disconnect(self):
        """Clean up connections."""
        if self.serial and self.serial.is_open:
            self.serial.close()
        if self.ssh:
            self.ssh.close()

def main():
    client = LEDClient()
    
    try:
        if not client.connect():
            print("Failed to connect!")
            return
            
        while True:
            print("\nLED Control Menu:")
            print("1. Set Strip Color")
            print("2. Set Strip Brightness")
            print("3. Set All Colors")
            print("4. Set All Brightness")
            print("5. Run Test Pattern")
            print("6. Turn Off LEDs")
            print("7. Show LED Configuration")
            print("8. Test Connection")
            print("9. Exit")
            
            try:
                choice = input("\nEnter choice (1-9): ")
                
                if choice == '1':
                    if not client.config:
                        print("No LED configuration available!")
                        continue
                    print("\nAvailable strips:")
                    for strip in client.config['strips']:
                        print(f"{strip['id']}: {strip['name']}")
                    strip_id = input("Enter strip ID (or ALL): ")
                    r = int(input("Enter red (0-255): "))
                    g = int(input("Enter green (0-255): "))
                    b = int(input("Enter blue (0-255): "))
                    response = client.set_strip_color(strip_id, r, g, b)
                    print(f"Response: {response}")
                    
                elif choice == '2':
                    if not client.config:
                        print("No LED configuration available!")
                        continue
                    print("\nAvailable strips:")
                    for strip in client.config['strips']:
                        print(f"{strip['id']}: {strip['name']}")
                    strip_id = input("Enter strip ID (or ALL): ")
                    brightness = int(input("Enter brightness (0-255): "))
                    response = client.set_strip_brightness(strip_id, brightness)
                    print(f"Response: {response}")
                    
                elif choice == '3':
                    r = int(input("Enter red (0-255): "))
                    g = int(input("Enter green (0-255): "))
                    b = int(input("Enter blue (0-255): "))
                    response = client.set_color(r, g, b)
                    print(f"Response: {response}")
                    
                elif choice == '4':
                    brightness = int(input("Enter brightness (0-255): "))
                    response = client.set_brightness(brightness)
                    print(f"Response: {response}")
                    
                elif choice == '5':
                    response = client.test_pattern()
                    print(f"Response: {response}")
                    
                elif choice == '6':
                    response = client.turn_off()
                    print(f"Response: {response}")
                    
                elif choice == '7':
                    if client.config:
                        print("\nLED Configuration:")
                        for strip in client.config['strips']:
                            print(f"\nStrip {strip['id']}: {strip['name']}")
                            print(f"  LED Count: {strip['count']}")
                            print(f"  Type: {strip['type']}")
                            print(f"  Channel: {strip['channel']}")
                    else:
                        print("No configuration available!")
                        
                elif choice == '8':
                    connected, mode = client.test_connection()
                    if connected:
                        print(f"Connection test successful - {mode} mode")
                        if mode == "LED":
                            # Refresh config
                            if client.get_config():
                                print("Configuration refreshed successfully!")
                            else:
                                print("Warning: Failed to refresh LED configuration")
                    else:
                        print(f"Connection test failed - {mode}")
                    
                elif choice == '9':
                    print("Exiting...")
                    client.disconnect()
                    break
                    
                else:
                    print("Invalid choice!")
                    
            except ValueError as e:
                print(f"Invalid input: Please enter numbers in the correct range")
            except Exception as e:
                print(f"Error: {e}")
                
    except KeyboardInterrupt:
        print("\nInterrupted by user!")
        
    except Exception as e:
        print(f"\nError: {e}")
        
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()