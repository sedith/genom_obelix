# src/genomstack/rosutils/convert.py

import time
import numpy as np
from genomstack.utils import quat2euler, quat2rot


def lower_tri(mat):
    return list(np.asarray(mat)[np.tril_indices(mat.shape[0])])


def ros_cov3_to_lower(cov9):
    return lower_tri(np.asarray(cov9).reshape(3, 3))


def lower_cov3_to_ros(cov6):
    return [
        cov6[0], cov6[1], cov6[3],
        cov6[1], cov6[2], cov6[4],
        cov6[3], cov6[4], cov6[5],
    ]


def jacobian_euler2quat(roll, pitch, yaw):
    cr, sr = np.cos(roll * 0.5), np.sin(roll * 0.5)
    cp, sp = np.cos(pitch * 0.5), np.sin(pitch * 0.5)
    cy, sy = np.cos(yaw * 0.5), np.sin(yaw * 0.5)

    J = np.zeros((4, 3))

    J[0, 0] = 0.5 * (-sr * cp * cy + cr * sp * sy)
    J[1, 0] = 0.5 * ( cr * cp * cy + sr * sp * sy)
    J[2, 0] = 0.5 * (-sr * sp * cy + cr * cp * sy)
    J[3, 0] = 0.5 * (-sr * cp * sy - cr * sp * cy)

    J[0, 1] = 0.5 * (-cr * sp * cy + sr * cp * sy)
    J[1, 1] = 0.5 * (-sr * sp * cy - cr * cp * sy)
    J[2, 1] = 0.5 * ( cr * cp * cy - sr * sp * sy)
    J[3, 1] = 0.5 * (-cr * sp * sy - sr * cp * cy)

    J[0, 2] = 0.5 * (-cr * cp * sy + sr * sp * cy)
    J[1, 2] = 0.5 * (-sr * cp * sy - cr * sp * cy)
    J[2, 2] = 0.5 * (-cr * sp * sy + sr * cp * cy)
    J[3, 2] = 0.5 * ( cr * cp * cy + sr * sp * sy)

    return J


class Cov:
    def __init__(self):
        self.pq = [0] * 12

    def from_stds(self, std_p, std_eul, std_v, std_w):
        self.p =  lower_tri(np.eye(3) * std_p ** 2)
        self.eul = np.eye(3) * std_eul ** 2
        self.v = lower_tri(np.eye(3) * std_v ** 2)
        self.w = lower_tri(np.eye(3) * std_w ** 2)

        return self

    def from_ros(self, data):
        pose_cov = np.asarray(data.pose.covariance).reshape(6, 6)
        twist_cov = np.asarray(data.twist.covariance).reshape(6, 6)

        self.p = lower_tri(pose_cov[:3, :3])
        self.eul = pose_cov[3:, 3:]
        self.v = lower_tri(twist_cov[:3, :3])
        self.w = lower_tri(twist_cov[3:, 3:])

        return self

    def get_cov_q(self, q):
        J = jacobian_euler2quat(*quat2euler(q))
        self.q = lower_tri(J @ self.eul @ J.T)

def odom_to_pose_estimator(data, ts=None, cov=None, repub_vel=False):
    cov = cov or Cov().from_ros(data) 

    p = [data.pose.pose.position.x, data.pose.pose.position.y, data.pose.pose.position.z]
    q = [data.pose.pose.orientation.w, data.pose.pose.orientation.x, data.pose.pose.orientation.y, data.pose.pose.orientation.z]
    v_b = [data.twist.twist.linear.x, data.twist.twist.linear.y, data.twist.twist.linear.z]
    w_b = [data.twist.twist.angular.x, data.twist.twist.angular.y, data.twist.twist.angular.z]

    ## twist in world frame
    r_wb = quat2rot(q)
    v_w = list(r_wb @ v_b)
    w_w = list(r_wb @ w_b)

    ## covariance
    cov.get_cov_q(q)

    if ts is None:
        sec = data.header.stamp.sec
        nsec = data.header.stamp.nanosec
    else:
        sec, nsec = ts

    return {
        'measure': {
            'ts': {'sec': sec, 'nsec': nsec},
            'intrinsic': 0,

            'pos': {'x': p[0], 'y': p[1], 'z': p[2]},
            'att': {'qw': q[0], 'qx': q[1], 'qy': q[2], 'qz': q[3]},

            'vel': {'vx': v_w[0], 'vy': v_w[1], 'vz': v_w[2]} if repub_vel else None,
            'avel': {'wx': w_w[0], 'wy': w_w[1], 'wz': w_w[2]} if repub_vel else None,

            'acc': None,
            'aacc': None,

            'pos_cov': {'cov': cov.p},
            'att_cov': {'cov': cov.q},
            'att_pos_cov': {'cov': cov.pq},

            'vel_cov': {'cov': cov.v} if repub_vel else None,
            'avel_cov': {'cov': cov.w} if repub_vel else None,
            'acc_cov': None,
            'aacc_cov': None,
        }
    }


def pose_estimator_to_odometry(data, ts=None, frame_id='map', child_frame_id='body'):
    from nav_msgs.msg import Odometry
    msg = Odometry()

    if ts is None:
        msg.header.stamp.sec = data['ts']['sec']
        msg.header.stamp.nanosec = data['ts']['nsec']
    else:
        msg.header.stamp.sec = ts[0]
        msg.header.stamp.nanosec = ts[1]

    msg.header.frame_id = frame_id
    msg.child_frame_id = child_frame_id

    msg.pose.pose.position.x = float(data['pos']['x'])
    msg.pose.pose.position.y = float(data['pos']['y'])
    msg.pose.pose.position.z = float(data['pos']['z'])

    msg.pose.pose.orientation.w = float(data['att']['qw'])
    msg.pose.pose.orientation.x = float(data['att']['qx'])
    msg.pose.pose.orientation.y = float(data['att']['qy'])
    msg.pose.pose.orientation.z = float(data['att']['qz'])

    if data['vel'] is not None:
        msg.twist.twist.linear.x = float(data['vel']['vx'])
        msg.twist.twist.linear.y = float(data['vel']['vy'])
        msg.twist.twist.linear.z = float(data['vel']['vz'])

    if data['avel'] is not None:
        msg.twist.twist.angular.x = float(data['avel']['wx'])
        msg.twist.twist.angular.y = float(data['avel']['wy'])
        msg.twist.twist.angular.z = float(data['avel']['wz'])

    if data['pos_cov'] is not None:
        pos_cov = lower_cov3_to_ros(data['pos_cov']['cov'])
        for r in range(3):
            for c in range(3):
                msg.pose.covariance[6 * r + c] = pos_cov[3 * r + c]

    if data['att_cov'] is not None:
        att_cov = lower_cov3_to_ros(data['att_cov']['cov'])
        for r in range(3):
            for c in range(3):
                msg.pose.covariance[6 * (r + 3) + (c + 3)] = att_cov[3 * r + c]

    if data['vel_cov'] is not None:
        vel_cov = lower_cov3_to_ros(data['vel_cov']['cov'])
        for r in range(3):
            for c in range(3):
                msg.twist.covariance[6 * r + c] = vel_cov[3 * r + c]

    if data['avel_cov'] is not None:
        avel_cov = lower_cov3_to_ros(data['avel_cov']['cov'])
        for r in range(3):
            for c in range(3):
                msg.twist.covariance[6 * (r + 3) + (c + 3)] = avel_cov[3 * r + c]

    return msg


def pose_estimator_to_pose_stamped(data, ts=None, frame_id='map'):
    from geometry_msgs.msg import PoseStamped
    msg = PoseStamped()

    if ts is None:
        msg.header.stamp.sec = data['ts']['sec']
        msg.header.stamp.nanosec = data['ts']['nsec']
    else:
        msg.header.stamp.sec = ts[0]
        msg.header.stamp.nanosec = ts[1]

    msg.header.frame_id = frame_id

    msg.pose.position.x = float(data['pos']['x'])
    msg.pose.position.y = float(data['pos']['y'])
    msg.pose.position.z = float(data['pos']['z'])

    msg.pose.orientation.w = float(data['att']['qw'])
    msg.pose.orientation.x = float(data['att']['qx'])
    msg.pose.orientation.y = float(data['att']['qy'])
    msg.pose.orientation.z = float(data['att']['qz'])

    return msg


def rigid_body_to_pose_stamped(data, ts=None, frame_id='map'):
    from geometry_msgs.msg import PoseStamped
    msg = PoseStamped()

    if ts is None:
        msg.header.stamp.sec = data['ts']['sec']
        msg.header.stamp.nanosec = data['ts']['nsec']
    else:
        msg.header.stamp.sec = ts[0]
        msg.header.stamp.nanosec = ts[1]

    msg.header.frame_id = frame_id
    if data['pos'] is not None:
        msg.pose.position.x = float(data['pos']['x'])
        msg.pose.position.y = float(data['pos']['y'])
        msg.pose.position.z = float(data['pos']['z'])
    if data['att'] is not None:
        msg.pose.orientation.w = float(data['att']['qw'])
        msg.pose.orientation.x = float(data['att']['qx'])
        msg.pose.orientation.y = float(data['att']['qy'])
        msg.pose.orientation.z = float(data['att']['qz'])
    else:
        msg.pose.orientation.w = 1.0

    return msg


# def rotorcraft_imu_to_imu(imu, ts=None, frame_id='body'):
#     from sensor_msgs.msg import Imu
#     msg = Imu()

#     msg.header.stamp = stamp
#     msg.header.frame_id = frame_id

#     if imu.get('att') is not None:
#         att = imu['att']
#         msg.orientation.w = att['qw']
#         msg.orientation.x = att['qx']
#         msg.orientation.y = att['qy']
#         msg.orientation.z = att['qz']
#     else:
#         msg.orientation_covariance[0] = -1.0

#     if imu.get('avel') is not None:
#         avel = imu['avel']
#         msg.angular_velocity.x = avel['wx']
#         msg.angular_velocity.y = avel['wy']
#         msg.angular_velocity.z = avel['wz']

#     if imu.get('acc') is not None:
#         acc = imu['acc']
#         msg.linear_acceleration.x = acc['ax']
#         msg.linear_acceleration.y = acc['ay']
#         msg.linear_acceleration.z = acc['az']

#     return msg
