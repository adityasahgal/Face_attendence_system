from fastapi import FastAPI, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime, date, time
import cv2
import shutil
import os
import io
import uuid

from database import get_db, create_tables
from models import Student, Attendance

# Initialize FastAPI
app = FastAPI(title="Face Detection Attendance System")

# IP Camera configuration
IP_CAMERA_URL = "rtsp://admin:Admin%40123@192.168.1.250:554/cam/realmonitor?channel=1&subtype=0"

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create DB tables
create_tables()

# Mount images folder for serving static content
if not os.path.exists("images"):
    os.makedirs("images")

app.mount("/images", StaticFiles(directory="images"), name="images")

def capture_from_ip_camera():
    """Capture frame from IP camera with proper error handling"""
    cap = None
    try:
        # Try with FFMPEG backend first
        cap = cv2.VideoCapture(IP_CAMERA_URL, cv2.CAP_FFMPEG)
        
        if not cap.isOpened():
            print("FFMPEG backend failed, trying default backend...")
            cap = cv2.VideoCapture(IP_CAMERA_URL)
        
        if not cap.isOpened():
            return None, "Cannot connect to IP camera"
        
        # Set timeout and read multiple frames to clear buffer
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        for _ in range(5):  # Read multiple frames to get latest
            ret, frame = cap.read()
            if not ret:
                continue
        
        if not ret or frame is None:
            return None, "Failed to capture frame from camera"
            
        return frame, "Success"
        
    except Exception as e:
        return None, f"Camera error: {str(e)}"
    finally:
        if cap is not None:
            cap.release()

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <title>Face Attendance</title>
            <style>
                body {{
                    text-align: center;
                    font-family: Arial;
                    margin: 0;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .video-container {{
                    margin: 20px 0;
                }}
                #video {{
                    border: 2px solid #ddd;
                    border-radius: 5px;
                    max-width: 100%;
                }}
                #message {{
                    font-size: 18px;
                    margin: 20px 0;
                    padding: 10px;
                    border-radius: 5px;
                    min-height: 24px;
                }}
                .success {{ color: green; }}
                .error {{ color: red; }}
                .info {{ color: blue; }}
                .controls {{
                    margin: 20px 0;
                }}
                button {{
                    padding: 10px 20px;
                    margin: 5px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                }}
                .start-btn {{ background: #28a745; color: white; }}
                .stop-btn {{ background: #dc3545; color: white; }}
                .status-btn {{ background: #17a2b8; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 Face Attendance System (IP Camera Mode)</h1>
                <p>Camera URL: {IP_CAMERA_URL}</p>
                
                <div class="controls">
                    <button class="start-btn" onclick="startAutoCapture()">▶ Start Auto Capture</button>
                    <button class="stop-btn" onclick="stopAutoCapture()">⏹ Stop Auto Capture</button>
                    <button class="status-btn" onclick="checkCameraStatus()">📷 Check Camera Status</button>
                </div>
                
                <div class="video-container">
                    <img id="video" width="640" height="480" alt="Live Camera Feed"/>
                </div>
                
                <div id="status" style="margin: 10px 0; padding: 10px; background: #e9ecef; border-radius: 5px;">
                    <strong>Status:</strong> <span id="statusText">Ready</span>
                </div>
                
                <div id="message"></div>
                
                <div id="results" style="text-align: left; margin: 20px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; max-height: 200px; overflow-y: auto;">
                    <h3>📊 Recent Results:</h3>
                    <div id="resultsList"></div>
                </div>
            </div>
            <script>
                let captureInterval;
                const video = document.getElementById("video");
                const message = document.getElementById("message");
                const statusText = document.getElementById("statusText");
                const resultsList = document.getElementById("resultsList");

                // Start streaming IP Camera feed
                function startStream() {
                    video.src = "/video_feed?" + Date.now();
                    statusText.textContent = "Streaming...";
                    statusText.style.color = "green";
                }

                // Check camera status
                async function checkCameraStatus() {
                    try {
                        const res = await fetch("/camera_status");
                        const data = await res.json();

                        message.innerHTML = `<span class="info">${data.message}</span>`;
                        statusText.textContent = data.status;
                        statusText.style.color =
                            data.status === "Connected" ? "green" : "red";

                    } catch (error) {
                        message.innerHTML = `<span class="error">Error: ${error.message}</span>`;
                    }
                }

                // Auto capture every 3 seconds
                function startAutoCapture() {
                    message.innerHTML = `<span class="info">🔄 Auto Capture Started</span>`;
                    startStream();

                    if (captureInterval) clearInterval(captureInterval);

                    captureInterval = setInterval(async () => {
                        const res = await fetch("/frame");
                        const blob = await res.blob();

                        const form = new FormData();
                        form.append("file", blob, "frame.jpg");

                        const r = await fetch("/mark_attendance/", {
                            method: "POST",
                            body: form,
                        });

                        const data = await r.json();

                        let row = document.createElement("div");
                        row.style.padding = "5px";
                        row.style.borderBottom = "1px solid #ddd";
                        row.innerHTML = `<span style="color: green;">🟢 ${data.message}</span>`;

                        resultsList.prepend(row);
                    }, 400);
                }

                // Stop auto capture
                function stopAutoCapture() {
                    if (captureInterval) {
                        clearInterval(captureInterval);
                        captureInterval = null;
                    }
                    message.innerHTML = `<span class="info">⏹ Auto Capture Stopped</span>`;
                    statusText.textContent = "Stopped";
                    statusText.style.color = "orange";
                }

                // On load
                window.addEventListener("load", () => {
                    startStream();
                    checkCameraStatus();
                });

                video.onerror = () => {
                    statusText.textContent = "Stream Error";
                    statusText.style.color = "red";
                    message.innerHTML = `<span class="error">❌ Failed to load stream</span>`;
                };

                video.onload = () => {
                    statusText.textContent = "Streaming";
                    statusText.style.color = "green";
                };
            </script>

            
        </body>
    </html>
    """

@app.get("/video_feed")
def video_feed():
    def generate_frames():
        cap = cv2.VideoCapture(IP_CAMERA_URL)

        while True:
            success, frame = cap.read()
            if not success:
                continue   # retry instead of breaking

            # Resize (optional)
            frame = cv2.resize(frame, (640, 480))

            ret, buffer = cv2.imencode(".jpg", frame)
            if not ret:
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" +
                buffer.tobytes() +
                b"\r\n"
            )

    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/frame")
def get_frame():
    """Fetch a single frame from the IP camera"""
    frame, status = capture_from_ip_camera()
    if frame is None:
        return JSONResponse({"message": status}, status_code=500)
        
    # Encode frame as JPEG
    _, jpeg = cv2.imencode('.jpg', frame)
    return StreamingResponse(io.BytesIO(jpeg.tobytes()), media_type="image/jpeg")

@app.get("/camera_status")
def camera_status():
    """Check camera connection status"""
    frame, status = capture_from_ip_camera()
    if frame is not None:
        return {
            "status": "Connected", 
            "message": f"Camera is working. Frame shape: {frame.shape}",
            "frame_size": f"{frame.shape[1]}x{frame.shape[0]}"
        }
    else:
        return {
            "status": "Disconnected", 
            "message": status,
            "frame_size": "N/A"
        }

@app.post("/mark_attendance/")
async def mark_attendance(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        # Create temp directory if not exists
        os.makedirs("temp", exist_ok=True)
        
        # Save temp image with unique name
        temp_path = f"temp/temp_{uuid.uuid4().hex}_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # DeepFace Recognition
        from deepface import DeepFace
        result = DeepFace.find(
            img_path=temp_path, 
            db_path="images", 
            enforce_detection=False,
            silent=True
        )

        marked_names = []
        current_time = datetime.now().time()
        today = date.today()

        # Handle multiple faces
        if isinstance(result, list) and len(result) > 0:
            for df in result:
                if not df.empty and 'identity' in df.columns:
                    try:
                        detected_file = os.path.basename(df.iloc[0]["identity"])
                        recognized_name = detected_file.split(".")[0]

                        student = db.query(Student).filter(Student.name == recognized_name).first()

                        if not student:
                            marked_names.append(f"{recognized_name} (not registered)")
                            continue

                        # Check existing attendance
                        already = db.query(Attendance).filter(
                            Attendance.student_id == student.id,
                            Attendance.date == today
                        ).first()

                        if already:
                            marked_names.append(f"{recognized_name} (Already Marked)")
                        else:
                            attendance = Attendance(
                                student_id=student.id,
                                time=current_time,
                                date=today
                            )
                            db.add(attendance)
                            db.commit()
                            marked_names.append(recognized_name)
                            
                    except Exception as e:
                        print(f"Error processing face: {e}")
                        continue

        if not marked_names:
            if isinstance(result, list) and len(result) > 0:
                return JSONResponse({"message": "😕 Faces detected but not recognized"})
            else:
                return JSONResponse({"message": "😕 No faces detected"})

        if any("(not registered)" in name for name in marked_names):
            return JSONResponse({"message": "⚠ Some faces not registered: " + ", ".join(marked_names)})
        elif any("(Already Marked)" in name for name in marked_names):
            return JSONResponse({"message": "ℹ Attendance already marked for: " + ", ".join(marked_names)})
        else:
            return JSONResponse({"message": "✅ Attendance marked for: " + ", ".join(marked_names)})

    except Exception as e:
        return JSONResponse({"message": f"⚠ Error: {str(e)}"})

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass

@app.post("/add_student/")
async def add_student(
    name: str = Form(...),
    roll_no: str = Form(...),
    course: str = Form(...),
    batch: str = Form(...),
    lecture: str = Form(...),  # Fixed spelling: lacture -> lecture
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # Create folder if missing
        os.makedirs("images", exist_ok=True)

        # Validate image
        if not image.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            return JSONResponse({"message": "❌ Only JPG, JPEG, and PNG files are allowed"})

        # Save with student name
        ext = image.filename.split(".")[-1]
        file_path = os.path.join("images", f"{name}.{ext}")

        # Check if student already exists
        existing_student = db.query(Student).filter(
            (Student.name == name) | (Student.roll_no == roll_no)
        ).first()
        
        if existing_student:
            return JSONResponse({"message": "❌ Student with same name or roll number already exists"})

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        # Save student record
        student = Student(
            name=name,
            roll_no=roll_no,
            course=course,
            batch=batch,
            lecture=lecture,  # Fixed spelling
            image=file_path,
        )

        db.add(student)
        db.commit()
        return JSONResponse({"message": "✅ Student Added Successfully"})
    
    except Exception as e:
        return JSONResponse({"message": f"❌ Error adding student: {str(e)}"})

@app.get("/students/")
def get_students(db: Session = Depends(get_db)):
    try:
        students = db.query(Student).all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "roll_no": s.roll_no,
                "course": s.course,
                "batch": s.batch,
                "lecture": s.lecture,  # Fixed spelling
                "image_url": f"/images/{os.path.basename(s.image)}"
            }
            for s in students
        ]
    except Exception as e:
        return JSONResponse({"message": f"Error fetching students: {str(e)}"})

@app.get("/attendances/")
def get_attendance(db: Session = Depends(get_db)):
    try:
        records = (
            db.query(Attendance, Student)
            .join(Student, Attendance.student_id == Student.id)
            .order_by(Attendance.date.desc(), Attendance.time.desc())
            .all()
        )

        return [
            {
                "id": a.id,
                "name": s.name,
                "roll_no": s.roll_no,
                "batch": s.batch,
                "course": s.course,
                "lecture": s.lecture,  # Fixed spelling
                "date": str(a.date),
                "time": str(a.time) if a.time else "N/A"
            }
            for a, s in records
        ]
    except Exception as e:
        return JSONResponse({"message": f"Error fetching attendance: {str(e)}"})

@app.get("/system_status/")
def system_status():
    """Get complete system status"""
    try:
        # Check camera
        camera_frame, camera_msg = capture_from_ip_camera()
        
        # Check database
        db = next(get_db())
        students_count = db.query(Student).count()
        attendance_count = db.query(Attendance).count()
        
        # Check images
        images_count = len([f for f in os.listdir("images") if f.lower().endswith(('.jpg', '.jpeg', '.png'))]) if os.path.exists("images") else 0
        
        return {
            "system": "online",
            "camera_connected": camera_frame is not None,
            "camera_message": camera_msg,
            "registered_students": students_count,
            "face_images": images_count,
            "total_attendance_records": attendance_count,
            "ip_camera_url": IP_CAMERA_URL
        }
    except Exception as e:
        return {"system": "error", "message": str(e)}

if __name__ == "_main_":
    import uvicorn
    
    print("🚀 Starting Face Attendance System...")
    print(f"📷 IP Camera: {IP_CAMERA_URL}")
    print("🌐 Web Interface: http://192.168.1.250:25001")
    print("📊 System Status: http://192.168.1.250:25001/system_status/")
    
    uvicorn.run(
        app, 
        host="192.168.1.250", 
        port=25001,
        reload=True
    )