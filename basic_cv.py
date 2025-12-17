import cv2

img = cv2.imread(r"D:\AI_VoiceChat\API\robot_camera\family_images\mtp.png")
print(img.shape)
cv2.imshow("khai_handsome",img)

#blur image
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
cv2.imshow("khai_handsome_gray", gray)
blur_avg = cv2.blur(img,(7,7))
cv2.imshow("khai_handsome_blur_avg", blur_avg)
blur_gaussian = cv2.GaussianBlur(img,(7,7),0)
cv2.imshow("khai_handsome_blur_gaussian", blur_gaussian)
blur_median = cv2.medianBlur(img,7)
cv2.imshow("khai_handsome_blur_median", blur_median)

#cut or crop image
crop = img[50:250,100:300]
cv2.imshow("khai_handsome_crop", crop)
cv2.imwrite("khai_handsome_crop.png", crop)
# Giả sử đã có hàm detect_face trả về tọa độ mặt

#resize image
resize_img = cv2.resize(img,(300,300))
cv2.imshow("khai_handsome_resize", resize_img)

#draw line
cv2.line(img,(0,0),(200,200),(0,255,0),30)
cv2.imshow("khai_handsome_line", img)
#draw rectangle
cv2.rectangle(img,(50,50),(250,250),(255,0,0),15)
cv2.imshow("khai_handsome_rectangle", img)
#draw circle
cv2.circle(img,(400,400),150,(0,0,255),10)
cv2.imshow("khai_handsome_circle", img)

#putting text
font = cv2.FONT_HERSHEY_SIMPLEX
cv2.putText(img,'KHAI HANDSOME',(50,250),font,2,(255,255,0),5,cv2.LINE_AA)
cv2.imshow("khai_handsome_text", img)

#edge detection
edges = cv2.Canny(gray,150,250)
cv2.imshow("khai_handsome_edges", edges)

#countours
_,thresh = cv2.threshold(gray,120,255,cv2.THRESH_BINARY)
countours,_ = cv2.findContours(thresh,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
cv2.drawContours(img,countours,-1,(0,255,0),3)
cv2.imshow("khai_handsome_thresh", thresh)
cv2.imshow("khai_handsome_countours",img)

cv2.waitKey(0)
cv2.destroyAllWindows()