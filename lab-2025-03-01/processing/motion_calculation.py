import cv2
import numpy as np

from preprocessing.plane import get_sparse_planes_from_dense_optical_flow
from processing.algorithm_icp import icp
from processing.matrix_operations import get_principals_from_transformation_matrix


def infer_dense_rotation_translation(optical_flow_motion_field: np.ndarray, percentile=80):
    from_field, to_field = get_sparse_planes_from_dense_optical_flow(
            optical_flow_motion_field,
            1.0,
            percentile
        )
    affine_transformation_matrix, inliers = cv2.estimateAffinePartial2D(
        from_field,
        to_field
    )

    theta, translation_vector = get_principals_from_transformation_matrix(affine_transformation_matrix)
    return theta, translation_vector


def estimate_sparse_principals_affine2D(from_points_cartesian, to_points_cartesian):
    """
    Estimates rotation angle and translation vector from two sets of corresponding points.
    """
    if len(from_points_cartesian) < 3 or len(to_points_cartesian) < 3:
        return 0.0, np.array([0.0, 0.0])  # Return default values if not enough points

    affine_transformation_matrix = cv2.estimateAffine2D(
        from_points_cartesian,
        to_points_cartesian,
        method=cv2.RANSAC
    )[0]

    if affine_transformation_matrix is None:
        return 0.0, np.array([0.0, 0.0])  # Return default values if transformation failed

    theta, translation_vector = get_principals_from_transformation_matrix(affine_transformation_matrix)
    return theta, translation_vector


def estimate_sparse_principals_icp(from_field: np.ndarray, to_field: np.ndarray):
    # Use the ICP algorithm to estimate the affine transformation matrix
    if len(from_field.shape) > len(to_field.shape):
        from_field = from_field.reshape(-1, 2)

    _, theta_rad, translation_vector, _, _ = icp(
        from_field,
        to_field,
        initial_pose=None,
    )

    return np.degrees(theta_rad), translation_vector
