import os
import time
import random
import multiprocessing as mp

TARGET_CPU = 90  # percent, 0-100

def worker(percent):
    period = 0.1  # seconds

    while True:
        # Small random variation around the target
        p = max(0, min(100, percent + random.uniform(-5, 5)))

        busy_time = period * p / 100
        start = time.perf_counter()

        # Hog CPU
        while time.perf_counter() - start < busy_time:
            pass

        # Sleep for the rest of the period
        time.sleep(max(0, period - busy_time))


if __name__ == "__main__":
    cores = os.cpu_count() or 1
    print(f"Using {cores} cores, targeting ~{TARGET_CPU}% CPU")
    print("Ctrl+C to stop")

    processes = [
        mp.Process(target=worker, args=(TARGET_CPU,))
        for _ in range(cores)
    ]

    try:
        for p in processes:
            p.start()
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        for p in processes:
            p.terminate()
