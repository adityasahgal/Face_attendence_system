
from deepface import DeepFace
import cv2
import os

def recognize_face_from_image(image_path):
    """Recognize face from image file path"""
    try:
        # Check if file exists
        if not os.path.exists(image_path):
            print(f"❌ File not found: {image_path}")
            return None

        # Try reading the image
        img = cv2.imread(image_path)
        if img is None:
            print(f"❌ OpenCV failed to read image: {image_path}")
            return None

        # Run DeepFace recognition
        result = DeepFace.find(
            img_path=image_path,
            db_path="images",
            enforce_detection=False,
            silent=True
        )

        # DeepFace result handling
        if isinstance(result, list) and len(result) > 0 and not result[0].empty:
            matched_name = os.path.basename(result[0].iloc[0]['identity']).split(".")[0]
            print(f"✅ Recognized as: {matched_name}")
            return matched_name
        else:
            print("😕 No face match found.")
            return None

    except Exception as e:
        print("Face recognition error:", e)
        return None

def recognize_face_from_frame(frame):
    """Recognize face from OpenCV frame"""
    try:
        # Save frame temporarily
        temp_path = "temp_frame.jpg"
        cv2.imwrite(temp_path, frame)
        
        # Use existing function
        result = recognize_face_from_image(temp_path)
        
        # Clean up
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return result
        
    except Exception as e:
        print("Frame recognition error:", e)
        return None