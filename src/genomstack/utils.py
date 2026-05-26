import socket
import numpy as np


## rotations (quat, euler, mat, ~angle-axis~)
def quat2rot(q):
    """Compute the rotation matrix associated to a quaternion.
    q       -- quaternion with scalar as first element [qw qx qy qz]
    """
    r11 = q[0] ** 2 + q[1] ** 2 - q[2] ** 2 - q[3] ** 2
    r21 = 2 * (q[1] * q[2] + q[0] * q[3])
    r31 = 2 * (q[1] * q[3] - q[0] * q[2])
    r12 = 2 * (q[1] * q[2] - q[0] * q[3])
    r22 = q[0] ** 2 - q[1] ** 2 + q[2] ** 2 - q[3] ** 2
    r32 = 2 * (q[2] * q[3] + q[0] * q[1])
    r13 = 2 * (q[1] * q[3] + q[0] * q[2])
    r23 = 2 * (q[2] * q[3] - q[0] * q[1])
    r33 = q[0] ** 2 - q[1] ** 2 - q[2] ** 2 + q[3] ** 2
    return np.array([[r11, r12, r13], [r21, r22, r23], [r31, r32, r33]])


def euler2rot(euler):
    """Compute the rotation matrix associated to euler angles.
    euler   -- euler angles [roll pitch yaw] (Z1Y2X3 convention, see https://en.wikipedia.org/wiki/Euler_angles#Rotation_matrix)
    """
    roll = euler[0]
    pitch = euler[1]
    yaw = euler[2]
    r11 = np.cos(pitch) * np.cos(yaw)
    r21 = np.cos(pitch) * np.sin(yaw)
    r31 = -np.sin(pitch)
    r12 = np.sin(roll) * np.sin(pitch) * np.cos(yaw) - np.cos(roll) * np.sin(yaw)
    r22 = np.sin(roll) * np.sin(pitch) * np.sin(yaw) + np.cos(roll) * np.cos(yaw)
    r32 = np.sin(roll) * np.cos(pitch)
    r13 = np.cos(roll) * np.sin(pitch) * np.cos(yaw) + np.sin(roll) * np.sin(yaw)
    r23 = np.cos(roll) * np.sin(pitch) * np.sin(yaw) - np.sin(roll) * np.cos(yaw)
    r33 = np.cos(roll) * np.cos(pitch)
    return np.array([[r11, r12, r13], [r21, r22, r23], [r31, r32, r33]])


def quat2euler(q):
    """Compute the euler angles associated to a quaternion.
    q       -- quaternion with scalar as first element [qw qx qy qz]
    """
    roll = np.arctan2(2 * (q[0]*q[1] + q[2]*q[3]), 1 - 2 * (q[1]*q[1] + q[2]*q[2]))
    pitch = np.arcsin(2 * (q[0]*q[2] - q[3]*q[1]))
    yaw = np.arctan2(2 * (q[0]*q[3] + q[1]*q[2]), 1 - 2 * (q[2]*q[2] + q[3]*q[3]))
    return np.array([roll, pitch, yaw])


def quat2yaw(q):
    """Compute the yaw angle associated to a quaternion.
    q       -- quaternion with scalar as first element [qw qx qy qz]
    """
    return np.arctan2(2 * (q[0]*q[3] + q[1]*q[2]), 1 - 2 * (q[2]*q[2] + q[3]*q[3]))


def rot2euler(R):
    """Compute the euler angles associated to a rotation matrix.
    R       -- rotation matrix
    """
    roll = np.arctan2(R[2,1], R[2,2])
    pitch = np.arcsin(-R[2,0])
    yaw = np.arctan2(R[1,0], R[0,0])
    return np.array([roll, pitch, yaw])


def rot2quat(R):
    """Compute the euler angles associated to a rotation matrix.
    This is disgusting, clean implementation TODO using https://math.stackexchange.com/questions/893984/conversion-of-rotation-matrix-to-quaternion
    see https://d3cw3dd2w32x2b.cloudfront.net/wp-content/uploads/2015/01/matrix-to-quat.pdf for reference
    R       -- rotation matrix
    """
    return euler2quat(rot2euler(R))


def euler2quat(euler):
    """Compute the quaternion associated to euler angles.
    euler   -- euler angles [roll pitch yaw] (Z1Y2X3 convention, see https://en.wikipedia.org/wiki/Euler_angles#Rotation_matrix)
    """
    cr = np.cos(euler[0] * 0.5)
    sr = np.sin(euler[0] * 0.5)
    cp = np.cos(euler[1] * 0.5)
    sp = np.sin(euler[1] * 0.5)
    cy = np.cos(euler[2] * 0.5)
    sy = np.sin(euler[2] * 0.5)
    return np.array([
        cr * cp * cy + sr * sp * sy,
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy
    ])


def yaw2quat(yaw):
    """Compute the quaternion associated to a yaw angle.
    yaw     -- yaw (Z1Y2X3 convention, see https://en.wikipedia.org/wiki/Euler_angles#Rotation_matrix)
    """
    cr = cp = 1
    sr = sp = 0
    hyaw = yaw * 0.5
    cy = np.cos(hyaw)
    sy = np.sin(hyaw)
    return np.array([
        cr * cp * cy + sr * sp * sy,
        sr * cp * cy - cr * sp * sy,
        cr * sp * cy + sr * cp * sy,
        cr * cp * sy - sr * sp * cy
    ])


def invert(q):
    """Rerturn the inverse quaternion of q."""
    return np.array([q[0], -q[1], -q[2], -q[3]]) / np.linalg.norm(q, 2)


def hamilton_prod(q1, q2):
    """Return the Hamilton product of 2 quaternions q1*q2."""
    return np.array([
        q1[0]*q2[0] - q1[1]*q2[1] - q1[2]*q2[2] - q1[3]*q2[3],
        q1[0]*q2[1] + q1[1]*q2[0] + q1[2]*q2[3] - q1[3]*q2[2],
        q1[0]*q2[2] - q1[1]*q2[3] + q1[2]*q2[0] + q1[3]*q2[1],
        q1[0]*q2[3] + q1[1]*q2[2] - q1[2]*q2[1] + q1[3]*q2[0]
    ])


def skew(v):
    """Return the skew symmetric matrix of a vector v."""
    return np.array([
        [0.0, -v[2], v[1]],
        [v[2], 0.0, -v[0]],
        [-v[1], v[0], 0.0],
    ])

## host helper
def is_localhost(host: str) -> bool:
    return host in ('localhost', '127.0.0.1', '::1', socket.gethostname())
