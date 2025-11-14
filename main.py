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
from deepface import DeepFace

# === Initialize FastAPI ===
app = FastAPI(title="Face Attendance System")

# === Setup DB and static ===
create_tables()
os.makedirs("images", exist_ok=True)
app.mount("/images", StaticFiles(directory="images"), name="images")


# =================== FRONTEND UI ===================

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <title>Face Attendance Dashboard</title>
            <style>
                body { font-family: Arial; text-align: center; margin: 40px; }
                .section { margin: 20px auto; padding: 20px; width: 80%; border: 1px solid #ccc; border-radius: 10px; }
                h2 { color: #2c3e50; }
                input, button { padding: 8px; margin: 5px; }
                img { width: 100px; height: 100px; border-radius: 10px; object-fit: cover; margin: 5px; }
                table { margin: 20px auto; border-collapse: collapse; }
                td, th { border: 1px solid #ddd; padding: 8px; }
                th { background: #2c3e50; color: white; }
                button { background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; }
                button:hover { background: #2980b9; }
                video { border: 2px solid #333; border-radius: 10px; margin-top: 15px; }
            </style>
        </head>
        <body>
            <h1>📸 Face Attendance System</h1>

            <!-- Add Student Section -->
            <div class="section">
                <h2>Add Student</h2>
                <form id="addStudentForm">
                    <input type="text" name="name" placeholder="Enter student name" required>
                    <input type="text" name="roll_no" placeholder="Enter roll number" required>
                    <input type="text" name="course" placeholder="Enter course" required>
                    <input type="text" name="batch" placeholder="Enter batch" required>
                    <input type="file" name="file" accept="image/*" required>
                    <button type="submit">Add Student</button>
                </form>
                <p id="addMessage"></p>
            </div>

            <!-- Webcam Section -->
            <div class="section">
                <h2>Mark Attendance</h2>
                <video id="video" width="480" height="360" autoplay></video><br>
                <button id="markBtn">Mark Attendance</button>
                <p id="markMessage" style="font-size:18px;color:#27ae60;"></p>
            </div>

            <!-- Student List -->
            <div class="section">
                <h2>Registered Students</h2>   
                <table id="studentTable">
                    <thead>
                        <tr>
                            <th>Photo</th>
                            <th>Name</th>
                            <th>Roll No</th>
                            <th>Course</th>
                            <th>Batch</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>

            <!-- Attendance List -->
            <div class="section">
                <h2>Attendance Marked Today</h2>
                <table id="attendanceTable">
                    <thead>
                        <tr>
                            <th>Student Name</th>
                            <th>Roll No</th>
                            <th>Course</th>
                            <th>Batch</th>
                            <th>Time</th>
                            <th>Date</th>

                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>

            <script>
                const addForm = document.getElementById("addStudentForm");
                const msg = document.getElementById("addMessage");
                const markMsg = document.getElementById("markMessage");
                const studentTable = document.getElementById("studentTable").querySelector("tbody");
                const attendanceTable = document.getElementById("attendanceTable").querySelector("tbody");
                const video = document.getElementById("video");
                const markBtn = document.getElementById("markBtn");

                // === START WEBCAM ===
                navigator.mediaDevices.getUserMedia({ video: true })
                    .then(stream => video.srcObject = stream)
                    .catch(err => alert("Cannot access camera: " + err));

                // === Add Student ===
                addForm.addEventListener("submit", async (e) => {
                    e.preventDefault();
                    const formData = new FormData(addForm);
                    const res = await fetch('/add_student/', { method: 'POST', body: formData });
                    const data = await res.json();
                    msg.textContent = data.message;
                    loadStudents();
                });

                // === Mark Attendance on Button Click ===
                markBtn.addEventListener("click", async () => {
                    markMsg.textContent = "⏳ Detecting face, please wait...";
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    canvas.getContext('2d').drawImage(video, 0, 0);
                    const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg'));
                    
                    const formData = new FormData();
                    formData.append('file', blob, 'capture.jpg');

                    const res = await fetch('/mark_attendance/', { method: 'POST', body: formData });
                    const data = await res.json();
                    markMsg.textContent = data.message;
                    loadAttendances();
                });

                // === Load Students ===
                async function loadStudents() {
                    const res = await fetch('/students');
                    const data = await res.json();
                    studentTable.innerHTML = "";
                    data.forEach(s => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td><img src="/images/${s.name}.jpg" alt="${s.name}"></td>
                            <td>${s.name}</td>
                            <td>${s.roll_no}</td>
                            <td>${s.course}</td>
                            <td>${s.batch}</td>
                        `;
                        studentTable.appendChild(row);
                    });
                }

                // === Load Attendance ===
                async function loadAttendances() {
                    const res = await fetch('/attendances');
                    const data = await res.json();
                    attendanceTable.innerHTML = "";
                    data.forEach(a => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                                            <td>${a.student_name}</td>
                                            <td>${a.roll_no}</td>
                                            <td>${a.course}</td>
                                            <td>${a.batch}</td>
                                            <td>${a.time}</td>
                                            <td>${a.date}</td>
                                        `;
                        attendanceTable.appendChild(row);
                    });
                }

                // Auto refresh every 5 seconds
                loadStudents();
                loadAttendances();
                setInterval(() => {
                    loadAttendances();
                    loadStudents();
                }, 5000);
            </script>
        </body>
    </html>
    """


# =================== API ROUTES ===================

@app.post("/add_student/")
async def add_student(
    name: str = Form(...),
    roll_no: str = Form(...),
    course: str = Form(...),
    batch: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    path = os.path.join("images", f"{name}.jpg")
    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    student = Student(name=name, roll_no=roll_no, course=course, batch=batch, image_path=path)
    db.add(student)
    db.commit()
    db.refresh(student)

    return {"message": f"✅ Student '{name}' added successfully!"}


@app.post("/mark_attendance/")
async def mark_attendance(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Face recognition
        result = DeepFace.find(img_path=temp_path, db_path="images", enforce_detection=False)
        marked_names = []

        if len(result) > 0:
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
        return JSONResponse({"message": f"⚠️ Error: {str(e)}"})

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.get("/students")
def get_students(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    return [{"id": s.id, "name": s.name} for s in students]


@app.get("/attendances")
def get_attendances(db: Session = Depends(get_db)):
    attendances = (
        db.query(Attendance, Student)
        .join(Student, Attendance.student_id == Student.id)
        .order_by(Attendance.date.desc())
        .all()
    )
    return [{"student_name": s.name, "date": str(a.date)} for a, s in attendances]


# =================== MAIN ===================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
