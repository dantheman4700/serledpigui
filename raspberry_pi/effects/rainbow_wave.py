import time
from rpi_ws281x import Color

def wheel(pos):
    """Generate rainbow colors across 0-255 positions."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def rainbow_wave(strip, wait_ms=20, iterations=None):
    """Apply rainbow wave effect to the entire strip.
    
    Args:
        strip: The LED strip object
        wait_ms: Time to wait between updates (in milliseconds)
        iterations: Number of complete cycles to run, or None for infinite
    """
    j = 0
    iteration_count = 0
    
    while True:
        try:
            # Calculate and set colors for each pixel
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))
            strip.show()
            
            # Wait for specified time
            time.sleep(wait_ms / 1000.0)
            
            # Increment position in color wheel
            j = (j + 1) % 256
            
            # Check if we've completed a full cycle
            if j == 0:
                iteration_count += 1
                if iterations is not None and iteration_count >= iterations:
                    break
                    
        except KeyboardInterrupt:
            break
            
    # Turn off all LEDs when done
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()