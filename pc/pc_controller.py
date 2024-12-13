import serial
import time
import paramiko

class LEDClient:
    def __init__(self, port='COM6', baudrate=115200):
        """Initialize LED client."""
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.ssh = None
        self.connected = False
        
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

            # Try to connect with PuTTY-like settings
            try:
                print("\nTrying PuTTY-like connection settings...")
                self.serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1,
                    write_timeout=1,
                    xonxoff=False,     # Disable software flow control
                    rtscts=False,      # Disable hardware (RTS/CTS) flow control
                    dsrdtr=False,      # Disable hardware (DSR/DTR) flow control
                    exclusive=None     # Let Windows handle exclusivity
                )
                
                if self.serial.is_open:
                    print("Port opened successfully!")
                    time.sleep(0.5)  # Short delay
                    
                    # Clear any pending data
                    self.serial.reset_input_buffer()
                    self.serial.reset_output_buffer()
                    
                    # Test the connection and get mode
                    connected, mode = self.test_connection()
                    if connected:
                        print(f"Connected successfully in {mode} mode!")
                        self.connected = True
                        return True
                    
                    print("Connection test failed")
                    if self.serial and self.serial.is_open:
                        self.serial.close()
                    
            except Exception as e:
                print(f"Connection attempt failed: {str(e)}")
                if self.serial and self.serial.is_open:
                    self.serial.close()
            
            return False
            
        except Exception as e:
            print(f"Connection failed: {str(e)}")
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

    def set_color(self, r, g, b):
        """Set LED color."""
        if not all(0 <= x <= 255 for x in (r, g, b)):
            return "ERROR: Color values must be between 0-255"
        return self.send_command(f"COLOR:{r},{g},{b}")

    def set_brightness(self, brightness):
        """Set LED brightness."""
        if not 0 <= brightness <= 255:
            return "ERROR: Brightness must be between 0-255"
        return self.send_command(f"BRIGHTNESS:{brightness}")

    def test_pattern(self):
        """Run test pattern."""
        return self.send_command("TEST")

    def turn_off(self):
        """Turn off LEDs."""
        return self.send_command("OFF")

    def test_connection(self):
        """Test if serial connection is working."""
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
                    return True, "LED"
                elif line in ["dan", "root"]:
                    return True, "Terminal"
                elif "dan" in line or "root" in line:  # Fallback check
                    return True, "Terminal"
            
            return True, "Unknown"
            
        except Exception as e:
            print(f"Connection test error: {e}")
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
            cmd, params = command.split(':', 1)
            if cmd == 'COLOR':
                try:
                    r, g, b = map(int, params.split(','))
                    if not all(0 <= x <= 255 for x in (r, g, b)):
                        return "Error: Color values must be between 0-255"
                except:
                    return "Error: Invalid color format. Use COLOR:r,g,b"
            elif cmd == 'BRIGHTNESS':
                try:
                    brightness = int(params)
                    if not 0 <= brightness <= 255:
                        return "Error: Brightness must be between 0-255"
                except:
                    return "Error: Invalid brightness format. Use BRIGHTNESS:value"
            
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
            return
            
        while True:
            print("\nLED Control Menu:")
            print("1. Send LED command")
            print("2. Switch to terminal mode")
            print("3. Release serial (ESC sequence)")
            print("4. Exit")
            print("\nValid commands:")
            print("- TEST")
            print("- COLOR:r,g,b (e.g., COLOR:255,0,0 for red)")
            print("- BRIGHTNESS:value (e.g., BRIGHTNESS:128)")
            print("- OFF")
            
            try:
                choice = input("\nEnter choice (1-4): ")
                
                if choice == '1':
                    command = input("Enter command: ")
                    response = client.send_command(command)
                    print(f"Response: {response}")
                    
                elif choice == '2':
                    print("Switching to terminal mode...")
                    response = client.send_command("TERMINAL")
                    print("Terminal mode active. Press ESC 3 times quickly to return to LED control.")
                    # Now just forward all input/output until escape sequence
                    import msvcrt
                    esc_count = 0
                    last_esc_time = 0
                    
                    while True:
                        if msvcrt.kbhit():
                            c = msvcrt.getch()
                            if c == b'\x1b':  # ESC
                                current_time = time.time()
                                if current_time - last_esc_time < 0.5:  # Within 500ms
                                    esc_count += 1
                                else:
                                    esc_count = 1
                                last_esc_time = current_time
                                
                                if esc_count >= 3:
                                    print("\nReturning to LED control...")
                                    break
                                    
                            client.serial.write(c)
                            
                        if client.serial.in_waiting:
                            data = client.serial.read()
                            print(data.decode('utf-8', errors='ignore'), end='', flush=True)
                    
                elif choice == '3':
                    client.release_serial()
                    break
                    
                elif choice == '4':
                    client.disconnect()
                    break
                    
                else:
                    print("Invalid choice!")
                    
            except Exception as e:
                print(f"Error processing choice: {str(e)}")
                
    except KeyboardInterrupt:
        print("\nInterrupted by user!")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        
    finally:
        client.disconnect()

if __name__ == "__main__":
    main()