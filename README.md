# Serial LED Controller

A Python-based LED controller system using USB serial communication between a PC and Raspberry Pi.

## Project Structure

- `pc/`: Contains the PC-side controller and GUI
- `raspberry_pi/`: Contains the Raspberry Pi LED controller service

## Setup Instructions

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
1. Connect the Raspberry Pi to the PC via USB
2. Start the PC controller GUI
3. Select the correct COM port
4. Click Connect
5. Use the GUI controls to manage the LED strip 