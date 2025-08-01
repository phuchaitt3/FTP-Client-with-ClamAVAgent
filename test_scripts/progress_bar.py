import sys
import time

def run_test():
    """
    Demonstrates a simple, real-time progress bar in the terminal.
    """
    total_items = 10  # We will use 10 dots to represent 100%

    print("Starting a slow process...")
    
    # Print the initial part of the progress bar.
    # The `end=''` prevents the print function from adding a newline character,
    # so the cursor stays on the same line.
    sys.stdout.write(f"Progress: [")
    sys.stdout.flush() # Ensure the starting bracket is shown immediately

    # Loop through the items, printing one dot for each
    for i in range(total_items):
        # Simulate a piece of work being done
        time.sleep(0.2)  # Pause for 200 milliseconds to make it visible

        # Print a dot for this step
        sys.stdout.write(".")
        
        # Flush the output buffer. This is the CRITICAL step.
        # It forces the dot to be written to the terminal immediately
        # instead of waiting for a newline or for the buffer to fill up.
        sys.stdout.flush()

    # Once the loop is done, print the closing part of the bar
    sys.stdout.write("] 100%\n") # The \n moves the cursor to the next line
    sys.stdout.flush()

    print("\nProcess finished!")

if __name__ == "__main__":
    run_test()