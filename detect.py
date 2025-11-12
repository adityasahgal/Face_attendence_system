from deepface import DeepFace
import cv2, os

def recognize_face(image_path):
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
            enforce_detection=False
        )

        # DeepFace result handling
        if len(result) > 0 and not result[0].empty:
            matched_name = os.path.basename(result[0].iloc[0]['identity']).split(".")[0]
            print(f"✅ Recognized as: {matched_name}")
            return matched_name
        else:
            print("😕 No face match found.")
            return None

    except Exception as e:
        print("Face recognition error:", e)
        return None
