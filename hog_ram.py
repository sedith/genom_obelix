import time
import psutil

TARGET_RAM = 75  # percent of total system RAM

total = psutil.virtual_memory().total
target = int(total * TARGET_RAM / 100)

print(f"Allocating ~{target / 1024**3:.1f} GB ({TARGET_RAM}% of RAM)")
print("Ctrl+C to stop")

# Allocate in chunks so you can see usage increase
chunks = []
chunk_size = 100 * 1024 * 1024  # 100 MB

try:
    while sum(map(len, chunks)) < target:
        size = min(chunk_size, target - sum(map(len, chunks)))
        chunk = bytearray(size)

        # Touch the memory so the OS actually commits it
        for i in range(0, size, 4096):
            chunk[i] = 1

        chunks.append(chunk)
        time.sleep(0.05)

    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("Releasing memory...")
