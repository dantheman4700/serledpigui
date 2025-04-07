# NeoPixel library static color example
import time
from rpi_ws281x import ws, Color, Adafruit_NeoPixel

# LED strip configuration:
LED_1_COUNT = 96       # Number of LED pixels.
LED_1_PIN = 18          # GPIO pin connected to the pixels (must support PWM! GPIO 13 and 18 on RPi 3).
LED_1_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_1_DMA = 10          # DMA channel to use for generating signal (Between 1 and 14)
LED_1_BRIGHTNESS = 128  # Set to 0 for darkest and 255 for brightest
LED_1_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_1_CHANNEL = 0       # 0 or 1
LED_1_STRIP = ws.WS2811_STRIP_GRB

LED_2_COUNT = 50        # Number of LED pixels.
LED_2_PIN = 13          # GPIO pin connected to the pixels (must support PWM! GPIO 13 or 18 on RPi 3).
LED_2_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_2_DMA = 11          # DMA channel to use for generating signal (Between 1 and 14)
LED_2_BRIGHTNESS = 128  # Set to 0 for darkest and 255 for brightest
LED_2_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_2_CHANNEL = 1       # 0 or 1
LED_2_STRIP = ws.WS2811_STRIP_GRB

def setStaticColor(r, g, b):
    """Set all LEDs to a static color."""
    global strip1
    global strip2
    
    # Create color value
    color = Color(r, g, b)
    
    try:
        # Update strip 1
        for i in range(strip1.numPixels()):
            strip1.setPixelColor(i, color)
        strip1.show()
        time.sleep(0.001)  # Small delay between strips
        
        # Update strip 2
        for i in range(strip2.numPixels()):
            strip2.setPixelColor(i, color)
        strip2.show()
            
    except KeyboardInterrupt:
        return

def setGroupColors(r, g, b):
    """Set all groups to different shades of the same color."""
    global strip2
    
    try:
        # Calculate different shades for each group
        for group_index, group in enumerate(hiveList):
            # Create slightly different shade for each group
            shade = 0.5 + (group_index * 0.05)  # 50% to 95% brightness
            color = Color(
                int(r * shade),
                int(g * shade),
                int(b * shade)
            )
            
            # Set all LEDs in the group to this color
            for pixel in group:
                strip2.setPixelColor(pixel, color)
        
        strip2.show()
            
    except KeyboardInterrupt:
        return

def blackout(strip):
    """Turn off all LEDs."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    time.sleep(0.001)  # Small delay between strip updates

# Main program logic follows:
if __name__ == '__main__':
    # Create NeoPixel objects with appropriate configuration for each strip.
    global strip1
    global strip2
    
    strip1 = Adafruit_NeoPixel(LED_1_COUNT, LED_1_PIN, LED_1_FREQ_HZ,
                               LED_1_DMA, LED_1_INVERT, LED_1_BRIGHTNESS,
                               LED_1_CHANNEL, LED_1_STRIP)

    strip2 = Adafruit_NeoPixel(LED_2_COUNT, LED_2_PIN, LED_2_FREQ_HZ,
                               LED_2_DMA, LED_2_INVERT, LED_2_BRIGHTNESS,
                               LED_2_CHANNEL, LED_2_STRIP)
    
    # groupings for front (same as groupedRainbowWave.py)
    cell1 = [0, 1, 2]
    cell2 = [3, 4, 5, 6, 7, 8, 9]
    cell3 = [10, 11, 12, 13, 14, 15, 16]
    cell4 = [17, 18, 19, 20, 21, 22]
    cell5 = [23, 24]
    cell6 = [25, 26, 27, 28, 29, 30]
    cell7 = [31, 32, 33, 34, 35, 36, 37]
    cell9 = [38, 39, 40, 41]
    cell8 = [42, 43, 44, 45]
    cell10 = [46, 47, 48, 49]
    hiveList = [cell1, cell2, cell3, cell4,
                cell5, cell6, cell7, cell8, cell9, cell10]
    
    # Initialize the library (must be called once before other functions).
    strip1.begin()
    strip2.begin()

    print('Press Ctrl-C to quit.')

    # Black out any LEDs that may be still on for the last run
    blackout(strip1)
    blackout(strip2)

    try:
        # Example: Set both strips to purple
        print('Setting color to purple...')
        setStaticColor(128, 0, 128)  # Purple (R=128, G=0, B=128)
        
        time.sleep(2)  # Wait 2 seconds
        
        # Example: Set strip 2 groups to shades of blue
        print('Setting groups to shades of blue...')
        setGroupColors(0, 0, 255)  # Blue (R=0, G=0, B=255)
        
        # Keep the program running
        print('Press Ctrl-C to quit...')
        while True:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print('\nStopping and clearing the strips...')
        blackout(strip1)
        blackout(strip2)
        print('Done.') 