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

def rainbow_wave_group(strip, group_set, wait_ms=20, iterations=None):
    """Apply rainbow wave effect to groups of LEDs.
    
    Args:
        strip: The LED strip object
        group_set: List of LED groups, where each group is a list of LED indices
        wait_ms: Time to wait between updates (in milliseconds)
        iterations: Number of complete cycles to run, or None for infinite
    """
    j = 0
    iteration_count = 0
    
    while True:
        try:
            # Update each group with its own color in the rainbow
            for group_index, group in enumerate(group_set):
                # Calculate color for this group based on its position
                color = wheel((int(group_index * 256 / len(group_set)) + j) & 255)
                
                # Apply the color to all LEDs in this group
                for led in group:
                    strip.setPixelColor(led, color)
                    
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

def rainbow_wave_individual_group(strip, group, wait_ms=20, iterations=None):
    """Apply rainbow wave effect to a single group of LEDs.
    
    Args:
        strip: The LED strip object
        group: List of LED indices in the group
        wait_ms: Time to wait between updates (in milliseconds)
        iterations: Number of complete cycles to run, or None for infinite
    """
    j = 0
    iteration_count = 0
    
    while True:
        try:
            # Calculate and set colors for each LED in the group
            for i, led in enumerate(group):
                strip.setPixelColor(led, wheel((int(i * 256 / len(group)) + j) & 255))
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
            
    # Turn off group LEDs when done
    for led in group:
        strip.setPixelColor(led, Color(0, 0, 0))
    strip.show()