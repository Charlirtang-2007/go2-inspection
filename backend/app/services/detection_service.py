# ArUco 检测和颜色检测函数。
# app/services/detection_service.py

import cv2
import cv2.aruco as aruco
import numpy as np

# ========== ArUco 检测 ==========

def detect_aruco_markers(frame):
    """检测画面中的 ArUco 标记"""
    if frame is None:
        return []

    try:
        # OpenCV 5.x 新版 API
        aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
        parameters = aruco.DetectorParameters()
        detector = aruco.ArucoDetector(aruco_dict, parameters)
        corners, ids, _ = detector.detectMarkers(frame)
    except AttributeError:
        # OpenCV 旧版 API
        aruco_dict = aruco.Dictionary_get(aruco.DICT_4X4_50)
        params = aruco.DetectorParameters_create()
        corners, ids, _ = aruco.detectMarkers(frame, aruco_dict, parameters=params)

    results = []
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            corner = corners[i][0]
            center_x = int((corner[0][0] + corner[2][0]) / 2)
            center_y = int((corner[0][1] + corner[2][1]) / 2)
            size = np.linalg.norm(corner[0] - corner[1])
            results.append({
                "id": int(marker_id),
                "center": {"x": center_x, "y": center_y},
                "size": float(size)
            })
    return results

# ========== 颜色检测（火焰/烟雾/漏油） ==========

def detect_fire_by_color(frame, threshold=0.01):
    """基于颜色检测火焰（红色区域）"""
    if frame is None:
        return False
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    lower_red1 = np.array([0, 50, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 50, 50])
    upper_red2 = np.array([180, 255, 255])
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)
    red_ratio = np.sum(mask > 0) / (frame.shape[0] * frame.shape[1])
    return red_ratio > threshold

def detect_smoke_by_color(frame, threshold=0.02):
    """基于颜色检测烟雾（灰白区域）"""
    if frame is None:
        return False
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    smoke_mask = cv2.inRange(gray, 150, 255)
    smoke_ratio = np.sum(smoke_mask > 0) / (frame.shape[0] * frame.shape[1])
    return smoke_ratio > threshold

def detect_oil_by_color(frame, threshold=0.01):
    """基于颜色检测漏油（深色区域）"""
    if frame is None:
        return False
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    oil_mask = cv2.inRange(gray, 0, 60)
    oil_ratio = np.sum(oil_mask > 0) / (frame.shape[0] * frame.shape[1])
    return oil_ratio > threshold