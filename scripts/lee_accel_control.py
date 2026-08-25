#!/usr/bin/env python3
import sys
import time
import numpy as np
import rclpy
from geometry_msgs.msg import AccelStamped
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from genomstack import RobotIO
from genomstack.rosutils.convert import pose_estimator_to_odometry
from genomstack.utils import allocation_from_config, euler2quat, hamilton_prod, invert, quat2euler, quat2rot, vee


def yaw_rate_to_body_rate(euler, yaw_rate):
    """Convert a world yaw-rate command to body angular velocity."""
    roll, pitch, _ = euler
    sr, cr = np.sin(roll), np.cos(roll)
    sp, cp = np.sin(pitch), np.cos(pitch)
    return yaw_rate * np.array([-sp, sr * cp, cr * cp])


def desired_orientation(force, yaw):
    pitch = np.arctan2(force[0], force[2])
    roll = np.arctan2(-force[1], np.hypot(force[2], force[0]))
    return euler2quat([roll, pitch, yaw])


class LeeAccelerationControl(Node):
    def __init__(self, config_arg: str):
        super().__init__('lee_accel_control')

        self.io = RobotIO(config_arg, silent=True)
        self.cfg = self.io.cfg

        ## arguments
        self.topic = '/genom/accel_ref'
        self.publisher_name = 'lee_ctrl'
        self.rate_hz = 500
        self.k_r = np.array([5.0, 5.0, 0.8])
        self.k_w = np.array([0.5, 0.5, 0.25])
        self.max_yawrate = 3.0
        self.min_rotor_speed = 16.0
        self.max_rotor_speed = 110.0
        self.timeout = 0.2

        self.gravity = np.array([0.0, 0.0, -9.81])
        self.mass = float(self.cfg.inertial.mass)
        self.inertia = np.array(self.cfg.inertial.J, dtype=float).reshape(3, 3)
        self.mixer = np.linalg.pinv(allocation_from_config(self.cfg.geom) * float(self.cfg.geom.cf))

        self.accel_ref = np.zeros(3)
        self.yaw_rate_ref = 0.0
        self.last_ref_time = None
        self.last_warn_time = 0.0

        self.create_subscription(AccelStamped, self.topic, self.reference_callback, 10)
        self.timer = self.create_timer(1.0 / self.rate_hz, self.update)
        self.get_logger().info(f'listening to {self.topic}, running at {self.rate_hz:.1f} Hz')

    def reference_callback(self, msg):
        self.accel_ref[:] = [msg.accel.linear.x, msg.accel.linear.y, msg.accel.linear.z]
        self.yaw_rate_ref = float(msg.accel.angular.z)
        self.last_ref_time = time.monotonic()

    def reference(self):
        if self.last_ref_time is None or time.monotonic() - self.last_ref_time > self.timeout:
            return np.zeros(3), 0.0
        return self.accel_ref, self.yaw_rate_ref

    def read_state(self):
        frame = self.io.read('pom', 'frame/robot')['frame']
        att = frame['att']
        q = np.array([att['qw'], att['qx'], att['qy'], att['qz']], dtype=float)
        avel = frame.get('avel') or {'wx': 0.0, 'wy': 0.0, 'wz': 0.0}
        omega_world = np.array([avel['wx'], avel['wy'], avel['wz']], dtype=float)
        return frame, q, quat2rot(q).T @ omega_world

    def compute_ctrl(self, q, omega, accel_ref, yaw_rate_ref):
        rot = quat2rot(q)
        euler = quat2euler(q)

        force = self.mass * (accel_ref - self.gravity)
        thrust = float(force @ rot[:, 2])

        q_des = desired_orientation(force, euler[2])
        yaw_rate = np.clip(yaw_rate_ref, -self.max_yawrate, self.max_yawrate)
        # omega_des = yaw_rate_to_body_rate(euler, yaw_rate)
        omega_des = [0, 0, yaw_rate]

        q_err = hamilton_prod(invert(q), q_des)
        r_err_mat = quat2rot(q_err)
        rot_error = 0.5 * vee(r_err_mat.T - r_err_mat)
        angvel_error = omega - quat2rot(q_err) @ omega_des
        coriolis = np.cross(omega, self.inertia @ omega)
        torque = -self.k_r * rot_error - self.k_w * angvel_error + coriolis

        omega_sq = self.mixer @ np.r_[0.0, 0.0, thrust, torque]
        omega_sq = np.clip(omega_sq, self.min_rotor_speed ** 2, self.max_rotor_speed ** 2)
        return np.sqrt(omega_sq)

    def publish_rotors(self, rotor_speeds):
        sec, nsec = divmod(time.time_ns(), 1_000_000_000)
        desired = np.zeros(8)
        desired[:len(rotor_speeds)] = rotor_speeds
        msg = {
            'rotor_input': {
                'ts': {'sec': sec, 'nsec': nsec},
                'control': '::or_rotorcraft::velocity',
                'desired': desired.tolist(),
            }
        }
        self.io.publish(self.publisher_name, msg)

    def update(self):
        try:
            frame, q, omega = self.read_state()
        except Exception as e:
            return
        accel_ref, yaw_rate_ref = self.reference()
        rotor_speeds = self.compute_ctrl(q, omega, accel_ref, yaw_rate_ref)
        self.publish_rotors(rotor_speeds)


def main():
    if len(sys.argv) != 2:
        print('usage: python3 scripts/lee_accel_control.py <config name>.yaml')
        return 1
    config_arg = sys.argv[1]

    rclpy.init()
    node = LeeAccelerationControl(config_arg)

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
