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

def rainbow_wave(strip, stop_event, wait_ms=20):
    """Apply rainbow wave effect to the entire strip until stopped.

    Args:
        strip: The LED strip object
        stop_event: A threading.Event() to signal stopping.
        wait_ms: Time to wait between updates (in milliseconds)
    """
    j = 0

    while not stop_event.is_set():
        try:
            # Calculate and set colors for each pixel
            for i in range(strip.numPixels()):
                # Check stop_event frequently within the inner loop
                if stop_event.is_set():
                    break
                strip.setPixelColor(i, wheel((int(i * 256 / strip.numPixels()) + j) & 255))

            if stop_event.is_set(): # Check again before showing and sleeping
                break

            strip.show()

            # Wait for specified time, checking event periodically
            # Instead of a single long sleep, sleep in smaller chunks
            # to check the stop_event more frequently.
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
            break # Allow Ctrl+C to break the loop if run standalone
        except Exception as e:
            print(f"Error in rainbow_wave: {e}")
            break # Exit on other errors

    # Cleanup (turning off LEDs) is now handled by led_controller.py
    print("Rainbow wave effect loop finished.")