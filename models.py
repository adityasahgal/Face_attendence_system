from sqlalchemy import Column, Integer, String, Time, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    roll_no = Column(String, unique=True, nullable=False)
    course = Column(String, nullable=False)
    batch = Column(String, nullable=False)
    image_path = Column(String, nullable=False)

    attendances = relationship("Attendance", back_populates="student")


class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    roll_no = Column(String, nullable=False)
    course = Column(String, nullable=False)
    batch = Column(String, nullable=False)
    # time = Column(Time)

    date = Column(Date)

    student = relationship("Student", back_populates="attendances")
