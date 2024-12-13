# Serial LED Controller

A Python-based LED controller system using USB serial communication between a PC and Raspberry Pi.

## Project Structure

- `pc/`: Contains the PC-side controller and GUI
- `raspberry_pi/`: Contains the Raspberry Pi LED controller service

## Setup Instructions

### Raspberry Pi Zero W USB Serial Setup
1. Edit `/boot/config.txt` and add these lines at the end:
   ```bash
   # Enable USB gadget mode
   dtoverlay=dwc2
   enable_uart=1
   ```

2. Edit `/boot/cmdline.txt` and add after `rootwait` (make sure it's all on one line):
   ```
   modules-load=dwc2,g_serial
   ```

3. Load the required modules immediately (or reboot):
   ```bash
   sudo modprobe dwc2
   sudo modprobe g_serial
   ```

4. Add modules to load at boot:
   ```bash
   echo "dwc2" | sudo tee -a /etc/modules
   echo "g_serial" | sudo tee -a /etc/modules
   ```

5. Give permissions to the serial device:
   ```bash
   sudo chmod 666 /dev/ttyGS0
   ```

6. Make permissions persistent by creating a udev rule:
   ```bash
   echo 'KERNEL=="ttyGS0", MODE="0666"' | sudo tee /etc/udev/rules.d/99-serial.rules
   ```

7. Reboot the Raspberry Pi:
   ```bash
   sudo reboot
   ```

8. After reboot, verify the USB serial device is created:
   ```bash
   ls -l /dev/ttyGS0
   ```

### PC Setup
1. Navigate to the `pc/` directory
2. Create a virtual environment: `python -m venv venv`
3. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Install requirements: `pip install -r requirements.txt`
5. Run the GUI: `python pc_controller_gui.py`

### Raspberry Pi Setup
1. Copy the `raspberry_pi/` directory to your Raspberry Pi
2. Create a virtual environment: `python -m venv led_env`
3. Activate: `source led_env/bin/activate`
4. Install requirements: `pip install -r requirements.txt`
5. Copy the systemd service file:
   ```bash
   sudo cp systemd/led-controller.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable led-controller
   sudo systemctl start led-controller
   ```

## Usage
1. Connect the Raspberry Pi to the PC via USB (use the USB port marked "USB" not "PWR")
2. The Pi should appear as a USB serial device (COM port on Windows)
3. Start the PC controller GUI
4. Select the correct COM port
5. Click Connect
6. Use the GUI controls to manage the LED strip

## Troubleshooting
1. If the serial device isn't showing up:
   - Make sure you're using the correct USB port on the Pi Zero W
   - Check if modules are loaded: `lsmod | grep dwc2`
   - Check dmesg for USB errors: `dmesg | grep -i usb`
2. If you get permission errors:
   - Verify the udev rule is in place
   - Check the permissions: `ls -l /dev/ttyGS0`
   - Try running: `sudo chmod 666 /dev/ttyGS0`