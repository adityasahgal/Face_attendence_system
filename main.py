from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2
import datetime
from detect import recognize_face
from database import get_db, create_tables
from models import Student, Attendance

app = FastAPI(title="Face Detection Attendance System")

# CORS setup (optional — frontend connect karne ke liye)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import date
import shutil
import os

from detect import recognize_face
from database import get_db, create_tables
from models import Student, Attendance

# Initialize FastAPI
app = FastAPI(title="Face Attendance System")

# Create DB tables
create_tables()

# Mount images folder for serving static content
if not os.path.exists("images"):
    os.makedirs("images")

app.mount("/images", StaticFiles(directory="images"), name="images")


# @app.get("/", response_class=HTMLResponse)
# def home():
#     return """
#     <html>
#         <head>
#             <title>Face Attendance</title>
#         </head>
#         <body style="text-align:center; font-family:Arial;">
#             <h1>🎓 Face Attendance System</h1>
#             <video id="video" width="640" height="480" autoplay></video><br><br>
#             <button id="capture">Mark Attendance</button>
#             <p id="message"></p>

#             <script>
#                 const video = document.getElementById('video');
#                 const captureBtn = document.getElementById('capture');
#                 const message = document.getElementById('message');

#                 navigator.mediaDevices.getUserMedia({ video: true })
#                     .then(stream => {
#                         video.srcObject = stream;
#                     });

#                 captureBtn.onclick = async () => {
#                     const canvas = document.createElement('canvas');
#                     canvas.width = video.videoWidth;
#                     canvas.height = video.videoHeight;
#                     canvas.getContext('2d').drawImage(video, 0, 0);
#                     const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg'));
#                     const formData = new FormData();
#                     formData.append('file', blob, 'capture.jpg');
#                     message.innerText = "⏳ Processing...";

#                     const res = await fetch('/mark_attendance/', { method: 'POST', body: formData });
#                     const data = await res.json();
#                     message.innerText = data.message;
#                 };
#             </script>
#         </body>
#     </html>
# """

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <title>Face Attendance</title>
        </head>
        <body style="text-align:center; font-family:Arial;">
            <h1>🎓 Face Attendance System (Auto Mode)</h1>
            <video id="video" width="640" height="480" autoplay></video>
            <p id="message" style="font-size:18px;"></p>

            <script>
                const video = document.getElementById('video');
                const message = document.getElementById('message');

                // Start webcam stream
                navigator.mediaDevices.getUserMedia({ video: true })
                    .then(stream => {
                        video.srcObject = stream;
                        startAutoCapture();
                    })
                    .catch(err => {
                        message.innerText = "⚠️ Cannot access camera: " + err;
                    });

                // Function to automatically capture frame every 0.5 seconds
                async function startAutoCapture() {
                    while (true) {
                        await new Promise(r => setTimeout(r, 100)); // every .5 sec

                        const canvas = document.createElement('canvas');
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        canvas.getContext('2d').drawImage(video, 0, 0);
                        const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg'));
                        
                        const formData = new FormData();
                        formData.append('file', blob, 'capture.jpg');

                        const res = await fetch('/mark_attendance/', { method: 'POST', body: formData });
                        const data = await res.json();
                        console.log(data.message);
                        message.innerText = data.message;
                    }
                }
            </script>
        </body>
    </html>
    """



# @app.post("/mark_attendance/")
# async def mark_attendance(file: UploadFile = File(...), db: Session = Depends(get_db)):
#     try:
#         temp_path = f"temp_{file.filename}"
#         with open(temp_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)

#         recognized_name = recognize_face(temp_path)

#         if recognized_name:
#             student = db.query(Student).filter(Student.name == recognized_name).first()
#             if student:
#                 already_marked = db.query(Attendance).filter(
#                     Attendance.student_id == student.id,
#                     Attendance.date == date.today()
#                 ).first()

#                 if not already_marked:
#                     attendance = Attendance(student_id=student.id, date=date.today())
#                     db.add(attendance)
#                     db.commit()
#                     message = f"✅ Attendance marked for {recognized_name}"
#                 else:
#                     message = f"🕒 {recognized_name} already marked present today"
#             else:
#                 message = f"❌ No student named {recognized_name} found in DB"
#         else:
#             message = "😕 No known face detected"

#         return JSONResponse({"message": message})

#     except Exception as e:
#         print("Error during attendance:", e)
#         return JSONResponse({"message": f"⚠️ Error: {str(e)}"})

#     finally:
#         if os.path.exists(temp_path):
#             os.remove(temp_path)

@app.post("/mark_attendance/")
async def mark_attendance(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # ✅ Detect multiple faces
        from deepface import DeepFace
        result = DeepFace.find(img_path=temp_path, db_path="images", enforce_detection=False)

        marked_names = []

        if len(result) > 0:
            # DeepFace may return a list of DataFrames (for multiple faces)
            for df in result:
                if not df.empty:
                    recognized_name = os.path.basename(df.iloc[0]['identity']).split(".")[0]
                    student = db.query(Student).filter(Student.name == recognized_name).first()

                    if student:
                        already_marked = db.query(Attendance).filter(
                            Attendance.student_id == student.id,
                            Attendance.date == date.today()
                        ).first()

                        if not already_marked:
                            attendance = Attendance(student_id=student.id, date=date.today())
                            db.add(attendance)
                            db.commit()
                            marked_names.append(recognized_name)
                        else:
                            marked_names.append(f"{recognized_name} (already marked)")
                    else:
                        marked_names.append(f"{recognized_name} (not in DB)")
        else:
            return JSONResponse({"message": "😕 No known faces detected"})

        msg = "✅ Attendance marked: " + ", ".join(marked_names)
        return JSONResponse({"message": msg})

    except Exception as e:
        print("Error:", e)
        return JSONResponse({"message": f"⚠️ Error: {str(e)}"})

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/add_student/")
async def add_student(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Save student's reference image
    os.makedirs("images", exist_ok=True)
    path = os.path.join("images", f"{name}.jpg")

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    student = Student(name=name)
    db.add(student)
    db.commit()
    db.refresh(student)

    return {"message": f"Student {name} added successfully!"}


# Database tables create karna
create_tables()

@app.get("/")
def root():
    return {"message": "Face Attendance API running successfully!"}


@app.get("/mark-attendance")
def mark_attendance():
    """Webcam open karega aur face detect karke attendance mark karega."""
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        return JSONResponse(content={"error": "Camera not accessible"}, status_code=500)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        return JSONResponse(content={"error": "Failed to capture frame"}, status_code=500)

    name = recognize_face(frame)

    if not name:
        return {"status": "unrecognized", "message": "Face not matched"}

    # Attendance mark karna
    db = next(get_db())
    student = db.query(Student).filter(Student.name == name).first()

    if not student:
        # Agar student database me nahi mila, to create kar lo
        student = Student(name=name)
        db.add(student)
        db.commit()
        db.refresh(student)

    # Check if already marked today
    today = datetime.date.today()
    already = db.query(Attendance).filter(
        Attendance.student_id == student.id,
        Attendance.date == today
    ).first()

    if already:
        return {"status": "already", "message": f"{name} already marked today"}

    # Add new attendance
    attendance = Attendance(student_id=student.id, date=today)
    db.add(attendance)
    db.commit()

    return {"status": "success", "message": f"Attendance marked for {name}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
