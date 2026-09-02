#!/usr/bin/env python3

import rosbag2_py
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message


# ============================================================
# CHANGE THESE
# ============================================================

BAG = "../tmp/bag_260828_115930/bag_260828_115930_0.db3"
IMU_TOPIC = "/livox/imu"
LIDAR_TOPIC = "/livox/lidar"

# Timestamp from your crash
FAIL_TS = 1787911260.027041

# sqlite3 for normal rosbag2 .db3 bags
# mcap for MCAP bags
STORAGE_ID = "sqlite3"

# ============================================================


NS = 1_000_000_000


def header_time_ns(msg):
    s = msg.header.stamp
    return s.sec * NS + s.nanosec


reader = rosbag2_py.SequentialReader()

reader.open(
    rosbag2_py.StorageOptions(
        uri=BAG,
        storage_id=STORAGE_ID,
    ),
    rosbag2_py.ConverterOptions("", ""),
)

# Get message types
topic_types = {
    x.name: x.type
    for x in reader.get_all_topics_and_types()
}

imu_type = get_message(topic_types[IMU_TOPIC])
lidar_type = get_message(topic_types[LIDAR_TOPIC])

# Only read the two topics we care about
reader.set_filter(
    rosbag2_py.StorageFilter(
        topics=[IMU_TOPIC, LIDAR_TOPIC]
    )
)


latest_imu_ts = None
previous_imu_ts = None
previous_imu_bag_ts = None

num_imu = 0
num_lidar = 0
coverage_failures = 0

# Print anything within +/- this amount around the crash
CRASH_WINDOW_MS = 200.0


print()
print("Scanning bag...")
print()


while reader.has_next():

    topic, data, bag_ts = reader.read_next()

    # --------------------------------------------------------
    # IMU
    # --------------------------------------------------------

    if topic == IMU_TOPIC:

        msg = deserialize_message(data, imu_type)
        ts = header_time_ns(msg)

        num_imu += 1

        delay_ms = (bag_ts - ts) / 1e6

        # Check IMU sampling intervals
        if previous_imu_ts is not None:

            msg_dt_ms = (ts - previous_imu_ts) / 1e6
            bag_dt_ms = (bag_ts - previous_imu_bag_ts) / 1e6

            # Adjust this threshold for your IMU rate.
            # Example:
            # 200 Hz -> expected 5 ms
            # 100 Hz -> expected 10 ms
            if msg_dt_ms > 15:
                print(
                    f"[IMU GAP] "
                    f"t={ts / NS:.9f} "
                    f"header_dt={msg_dt_ms:.3f} ms "
                    f"bag_dt={bag_dt_ms:.3f} ms"
                )

            if msg_dt_ms <= 0:
                print(
                    f"[IMU BAD TS] "
                    f"t={ts / NS:.9f} "
                    f"dt={msg_dt_ms:.6f} ms"
                )

        previous_imu_ts = ts
        previous_imu_bag_ts = bag_ts

        # "latest IMU available so far"
        latest_imu_ts = ts


    # --------------------------------------------------------
    # LIDAR
    # --------------------------------------------------------

    elif topic == LIDAR_TOPIC:

        msg = deserialize_message(data, lidar_type)
        ts = header_time_ns(msg)

        num_lidar += 1

        delay_ms = (bag_ts - ts) / 1e6

        if latest_imu_ts is not None:

            #
            # THIS IS THE MOST INTERESTING NUMBER.
            #
            # Positive:
            # lidar timestamp is newer than latest IMU timestamp
            # seen so far in bag order.
            #
            coverage_ms = (ts - latest_imu_ts) / 1e6

            if coverage_ms > 0:

                coverage_failures += 1

                print(
                    f"[LIDAR AHEAD OF IMU] "
                    f"lidar={ts / NS:.9f} "
                    f"latest_imu={latest_imu_ts / NS:.9f} "
                    f"ahead={coverage_ms:.3f} ms "
                    f"lidar_bag_delay={delay_ms:.3f} ms"
                )


    # --------------------------------------------------------
    # Show everything close to the actual crash timestamp
    # --------------------------------------------------------

    msg_ts = ts / NS

    if abs(msg_ts - FAIL_TS) * 1000 < CRASH_WINDOW_MS:

        print(
            f"  [NEAR CRASH] "
            f"{topic:30s} "
            f"msg={msg_ts:.9f} "
            f"bag={bag_ts / NS:.9f} "
            f"bag-msg={(bag_ts - ts) / 1e6:+.3f} ms"
        )


print()
print("===================================================")
print("SUMMARY")
print("===================================================")
print(f"IMU messages:              {num_imu}")
print(f"Lidar messages:            {num_lidar}")
print(f"Lidar ahead of latest IMU: {coverage_failures}")
