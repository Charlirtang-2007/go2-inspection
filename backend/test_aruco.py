import cv2
import cv2.aruco as aruco
import os

# 与后端保持一致的字典
aruco_dict = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)

markers = {
    0: "start",   # 起点
    1: "area_A",  # A区（正常区）
    2: "area_B",  # B区（异常触发区）
    3: "end"      # 终点
}

os.makedirs("aruco_print", exist_ok=True)

for marker_id, name in markers.items():
    # 生成 600x600 的原始码
    marker_img = aruco.generateImageMarker(aruco_dict, marker_id, 600)
    
    # 【关键】加 150 像素的宽白边，极大地提升摄像头识别率
    img_with_border = cv2.copyMakeBorder(
        marker_img, 150, 150, 150, 150,
        cv2.BORDER_CONSTANT, value=[255, 255, 255]
    )
    
    filename = f"aruco_print/{marker_id}_{name}.png"
    cv2.imwrite(filename, img_with_border)
    print(f"✅ 已生成: {filename}")

print("🎉 搞定！去 aruco_print 文件夹里拿图片。")
