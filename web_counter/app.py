import cv2
from flask import Flask, render_template, Response, jsonify
from sqlalchemy import create_engine, Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import threading

app = Flask(__name__)

engine = create_engine('sqlite:///counter.db')
Base = declarative_base()

class Counter(Base):
    __tablename__ = 'counter'
    id = Column(Integer, primary_key=True, autoincrement=True)
    count = Column(Integer, default=0)

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db_session = Session()

if not db_session.query(Counter).first():
    new_counter = Counter(count=0)
    db_session.add(new_counter)
    db_session.commit()

lock = threading.Lock()

def video_stream():
    global count
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(0)

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    zone_x1 = frame_width // 2 - 50
    zone_y1 = frame_height // 2 - 50
    zone_x2 = frame_width // 2 + 50
    zone_y2 = frame_height // 2 + 50

    previous_position = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        for (x, y, w, h) in faces:
            face_center_x = x + w // 2

            with lock:
                counter = db_session.query(Counter).first()
                if zone_x1 < face_center_x < zone_x2:
                    if previous_position == "right" and face_center_x < frame_width // 2:
                        counter.count += 1
                        previous_position = "left"
                    elif previous_position == "left" and face_center_x > frame_width // 2:
                        if counter.count > 0:
                            counter.count -= 1
                        previous_position = "right"
                else:
                    previous_position = "left" if face_center_x < frame_width // 2 else "right"
                
                db_session.commit()

        cv2.rectangle(frame, (zone_x1, zone_y1), (zone_x2, zone_y2), (0, 255, 0), 2)
        cv2.putText(frame, f"Passagens: {counter.count}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        _, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/count')
def get_count():
    with lock:
        counter = db_session.query(Counter).first()
        return jsonify({'count': counter.count})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)