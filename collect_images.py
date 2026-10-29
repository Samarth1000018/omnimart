"""Capture labelled training images from a webcam. SPACE saves, Q quits."""
import argparse
from datetime import datetime
from pathlib import Path
import cv2

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("label",help="Class label, e.g. milk_carton")
    parser.add_argument("--output",default="training-images",help="Output dataset directory")
    parser.add_argument("--camera",type=int,default=0)
    args=parser.parse_args();target=Path(args.output)/args.label;target.mkdir(parents=True,exist_ok=True)
    cap=cv2.VideoCapture(args.camera)
    if not cap.isOpened():raise SystemExit("Could not open webcam. Check --camera and camera permissions.")
    count=len(list(target.glob("*.jpg")));print("SPACE captures an image; Q quits.")
    try:
        while True:
            ok,frame=cap.read()
            if not ok:break
            display=frame.copy();cv2.putText(display,f"{args.label} | saved {count} | SPACE capture / Q quit",(14,30),cv2.FONT_HERSHEY_SIMPLEX,.65,(30,230,150),2)
            cv2.imshow("OmniMart training image capture",display);key=cv2.waitKey(1)&0xff
            if key==ord("q"):break
            if key==ord(" "):
                name=datetime.now().strftime("%Y%m%d_%H%M%S_%f")+".jpg";cv2.imwrite(str(target/name),frame);count+=1;print(f"Saved {target/name}")
    finally:cap.release();cv2.destroyAllWindows()
if __name__=="__main__":main()
