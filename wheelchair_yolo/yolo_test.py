from ultralytics import YOLOWorld
import cv2

model_path = "/Users/prn/Documents/Code/ENGR100/wheelchair_yolo/yolo26n.pt"
model = YOLOWorld(model_path)

image_path = "/Users/prn/Documents/Code/ENGR100/wheelchair_yolo/wheelchair.v1i.yolo26/test/images/chair_10011_jpg.rf.55d4a8569c68dd1ea17e4ffbdc56e587.jpg"

image = cv2.imread(image_path)

results = model.predict(image, conf=0.3)
results[0].show()