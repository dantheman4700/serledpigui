import time
import threading # Although Event is passed in, good practice to import
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

def rainbow_wave_group(strip, group_set, stop_event, wait_ms=20):
    """Apply rainbow wave effect to groups of LEDs until stopped.

    Args:
        strip: The LED strip object
        group_set: List of LED groups, where each group is a list of LED indices
        stop_event: A threading.Event() to signal stopping.
        wait_ms: Time to wait between updates (in milliseconds)
    """
    j = 0

    while not stop_event.is_set():
        try:
            # Update each group with its own color in the rainbow
            for group_index, group in enumerate(group_set):
                # Check stop_event frequently
                if stop_event.is_set():
                    break
                # Calculate color for this group based on its position
                color = wheel((int(group_index * 256 / len(group_set)) + j) & 255)

                # Apply the color to all LEDs in this group
                for led in group:
                     # Check stop_event even more frequently if groups are large
                     if stop_event.is_set():
                         break
                     strip.setPixelColor(led, color)
                if stop_event.is_set(): # Break outer loop if needed
                     break

            if stop_event.is_set(): # Check again before showing and sleeping
                break

            strip.show()

            # Wait for specified time, checking event periodically
            step_wait_ms = 10 # Check every 10ms
            total_wait_ms = wait_ms
            while total_wait_ms > 0 and not stop_event.is_set():
                 sleep_chunk = min(step_wait_ms, total_wait_ms)
                 time.sleep(sleep_chunk / 1000.0)
                 total_wait_ms -= sleep_chunk

            if stop_event.is_set():
                 break

            # Increment position in color wheel
            j = (j + 1) % 256

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error in rainbow_wave_group: {e}")
            break # Exit on other errors

    # Cleanup handled by led_controller.py
    print("Rainbow wave group effect loop finished.")

def rainbow_wave_individual_group(strip, group, stop_event, wait_ms=20):
    """Apply rainbow wave effect to a single group of LEDs until stopped.

    Args:
        strip: The LED strip object
        group: List of LED indices in the group
        stop_event: A threading.Event() to signal stopping.
        wait_ms: Time to wait between updates (in milliseconds)
    """
    j = 0

    while not stop_event.is_set():
        try:
            # Calculate and set colors for each LED in the group
            for i, led in enumerate(group):
                if stop_event.is_set():
                    break
                strip.setPixelColor(led, wheel((int(i * 256 / len(group)) + j) & 255))

            if stop_event.is_set(): # Check again before showing and sleeping
                break

            strip.show()

            # Wait for specified time, checking event periodically
            step_wait_ms = 10 # Check every 10ms
            total_wait_ms = wait_ms
            while total_wait_ms > 0 and not stop_event.is_set():
                 sleep_chunk = min(step_wait_ms, total_wait_ms)
                 time.sleep(sleep_chunk / 1000.0)
                 total_wait_ms -= sleep_chunk

            if stop_event.is_set():
                 break

            # Increment position in color wheel
            j = (j + 1) % 256

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error in rainbow_wave_individual_group: {e}")
            break # Exit on other errors

    # Cleanup handled by led_controller.py
    print("Rainbow wave individual group effect loop finished.")