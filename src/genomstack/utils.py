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


def vee(mat):
    """Return the vee map of a 3x3 skew-symmetric matrix."""
    return np.array([
        mat[2, 1] - mat[1, 2],
        mat[0, 2] - mat[2, 0],
        mat[1, 0] - mat[0, 1],
    ])


## allocation matrix
def axis_rot(axis, angle):
    """Compute the rotation matrix around a given axis, angle in radians."""
    c = np.cos(angle)
    s = np.sin(angle)
    if axis == 'x':
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == 'y':
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    if axis == 'z':
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    raise ValueError(f'unknown rotation axis {axis!r}')


def gtmrp_props(n, l, alpha, beta, com=None, alpha0=-1, s0=1):
    """Return propeller positions, orientations and spin signs for a GTMR platform. alpha and beta are given in degrees."""
    com = np.zeros(3) if com is None else np.asarray(com, dtype=float)
    alpha = np.deg2rad(alpha)
    beta = np.deg2rad(beta)

    positions = []
    rotations = []
    signs = []
    for i in range(n):
        yaw = i * (np.pi / (n / 2))
        rz = axis_rot('z', yaw)
        rotations.append(rz @ axis_rot('y', beta) @ axis_rot('x', alpha0 * (-1) ** i * alpha))
        positions.append(l * rz @ np.array([1.0, 0.0, 0.0]) + com)
        signs.append(s0 * (-1) ** i)

    return positions, rotations, signs


def gtmrp_matrix(rotations, positions, signs, cf, ct):
    """Compute force and torque allocation matrices for GTMR propellers."""
    n = len(rotations)
    cf = [cf] * n if np.isscalar(cf) else list(cf)
    ct = [ct] * n if np.isscalar(ct) else list(ct)

    thrust_axes = [np.asarray(r, dtype=float) @ np.array([0.0, 0.0, 1.0]) for r in rotations]
    gf = np.column_stack(thrust_axes)
    gt = np.column_stack([
        np.cross(np.asarray(positions[i], dtype=float), thrust_axes[i])
        + ct[i] / cf[i] * signs[i] * thrust_axes[i]
        for i in range(n)
    ])
    return gf, gt


def allocation_matrix(n, l, alpha, beta=0.0, cf=1.0, ct=0.0, com=None, alpha0=-1, s0=1):
    """Compute a 6xn wrench allocation matrix mapping rotor thrusts to body wrench."""
    positions, rotations, signs = gtmrp_props(n, l, alpha, beta, com=com, alpha0=alpha0, s0=s0)
    gf, gt = gtmrp_matrix(rotations, positions, signs, cf, ct)
    return np.vstack((gf, gt))


def allocation_from_config(geom):
    """Compute the config-driven allocation matrix used by the rotor speed mixer."""
    return allocation_matrix(
        n=int(geom.rotors),
        l=float(geom.armlen),
        alpha=float(getattr(geom, 'rx', 0.0)),
        beta=float(getattr(geom, 'ry', 0.0)),
        cf=float(geom.cf),
        ct=float(geom.ct),
        com=getattr(geom, 'com', None),
        alpha0=int(getattr(geom, 'alpha0', -1)),
        s0=int(getattr(geom, 's0', 1)),
    )

## host helper
def is_localhost(host: str) -> bool:
    return host in ('localhost', '127.0.0.1', '::1', socket.gethostname())
