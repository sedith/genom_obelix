import time
import random
import torch

TARGET_GPU = 70  # approximate %, 0-100

device = "cuda"

# Bigger matrix = more GPU work
size = 4096

a = torch.randn(size, size, device=device)
b = torch.randn(size, size, device=device)

period = 0.1

print(f"Targeting roughly {TARGET_GPU}% GPU")
print("Ctrl+C to stop")

try:
    while True:
        target = max(0, min(100, TARGET_GPU + random.uniform(-5, 5)))
        busy_time = period * target / 100

        start = time.perf_counter()

        while time.perf_counter() - start < busy_time:
            c = a @ b

        torch.cuda.synchronize()

        elapsed = time.perf_counter() - start
        time.sleep(max(0, period - elapsed))

except KeyboardInterrupt:
    pass
