from flask import Flask, jsonify, request
import sqlite3
import jwt
import datetime
from flask_cors import CORS
import bcrypt
from database import get_connection, init_db

app = Flask(__name__)
CORS(app)

SECRET_KEY = "mysecretkey123"

# -------------------------------------------------------
# INITIALIZE DATABASE
# -------------------------------------------------------
init_db()


# -------------------------------------------------------
# TOKEN DECODER (Reusable)
# -------------------------------------------------------
def decode_token():
    token = request.headers.get("Authorization")

    if not token:
        return None, "Token missing"

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded["email"], None
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except:
        return None, "Invalid token"


# -------------------------------------------------------
# SLOT INITIALIZATION (RUNS ONLY ONCE)
# -------------------------------------------------------
def generate_slots():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM slots")
    count = cur.fetchone()[0]

    if count == 0:
        times = [
            ("06:00", "07:00"),
            ("07:00", "08:00"),
            ("08:00", "09:00"),
            ("09:00", "10:00"),
            ("17:00", "18:00"),
            ("18:00", "19:00"),
            ("19:00", "20:00")
        ]

        for start, end in times:
            cur.execute(
                "INSERT INTO slots (start_time, end_time) VALUES (?, ?)",
                (start, end)
            )

    conn.commit()
    conn.close()


generate_slots()


# -------------------------------------------------------
# TEST ROUTES
# -------------------------------------------------------
@app.route('/hello')
def hello():
    return jsonify({"message": "Gym Slot Backend Running Successfully!"})


# -------------------------------------------------------
# REGISTER USER
# -------------------------------------------------------
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    # Validation
    if len(name) < 3:
        return jsonify({"error": "Name must be at least 3 characters"}), 400
    if "@" not in email:
        return jsonify({"error": "Invalid email address"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400

    # 🔐 HASH PASSWORD
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, hashed_password)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400
    finally:
        conn.close()

    return jsonify({"message": "User registered successfully"}), 201



# -------------------------------------------------------
# LOGIN USER
# -------------------------------------------------------
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    email = data.get("email", "").strip()
    password = data.get("password", "")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()

    if user is None:
        return jsonify({"error": "User not found"}), 404

    stored_hash = user["password"]

    # SQLite may return string instead of bytes
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode()

    # ✅ Correct bcrypt check
    if not bcrypt.checkpw(password.encode(), stored_hash):
        return jsonify({"error": "Incorrect password"}), 401

    token = jwt.encode(
        {
            "email": email,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        },
        SECRET_KEY,
        algorithm="HS256"
    )

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {"name": user["name"], "email": user["email"]}
    })



# -------------------------------------------------------
# GET SLOTS (DATE-BASED AVAILABILITY)
# -------------------------------------------------------
@app.route('/slots', methods=['GET'])
def get_slots():
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "date query param required (YYYY-MM-DD)"}), 400

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM slots")
    slots = cur.fetchall()

    response = []

    for slot in slots:
        cur.execute("""
            SELECT 1 FROM bookings
            WHERE slot_id = ? AND booking_date = ?
        """, (slot["id"], date))

        is_booked = cur.fetchone() is not None

        response.append({
            "id": slot["id"],
            "start_time": slot["start_time"],
            "end_time": slot["end_time"],
            "booked": is_booked
        })

    conn.close()
    return jsonify(response)


# -------------------------------------------------------
# BOOK SLOT (DATE-BASED)
# -------------------------------------------------------
@app.route('/book-slot', methods=['POST'])
def book_slot():
    user_email, error = decode_token()
    if error:
        return jsonify({"error": error}), 401

    data = request.get_json()
    slot_id = data.get("slot_id")
    booking_date = data.get("date")

    if not slot_id or not booking_date:
        return jsonify({"error": "slot_id and date are required"}), 400

    conn = get_connection()
    cur = conn.cursor()

    # Check slot exists
    cur.execute("SELECT * FROM slots WHERE id = ?", (slot_id,))
    if cur.fetchone() is None:
        conn.close()
        return jsonify({"error": "Slot not found"}), 404

    # Check booking conflict
    cur.execute("""
        SELECT 1 FROM bookings
        WHERE slot_id = ? AND booking_date = ?
    """, (slot_id, booking_date))

    if cur.fetchone():
        conn.close()
        return jsonify({"error": "Slot already booked for this date"}), 400

    # Insert booking
    cur.execute("""
        INSERT INTO bookings (slot_id, user_email, booking_date)
        VALUES (?, ?, ?)
    """, (slot_id, user_email, booking_date))

    conn.commit()
    conn.close()

    return jsonify({"message": "Slot booked successfully"}), 200


# -------------------------------------------------------
# CANCEL SLOT (DATE-BASED)
# -------------------------------------------------------
@app.route('/cancel-slot', methods=['POST'])
def cancel_slot():
    user_email, error = decode_token()
    if error:
        return jsonify({"error": error}), 401

    data = request.get_json()
    slot_id = data.get("slot_id")
    booking_date = data.get("date")

    if not slot_id or not booking_date:
        return jsonify({"error": "slot_id and date required"}), 400

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM bookings
        WHERE slot_id = ? AND booking_date = ? AND user_email = ?
    """, (slot_id, booking_date, user_email))

    if cur.rowcount == 0:
        conn.close()
        return jsonify({"error": "No booking found"}), 404

    conn.commit()
    conn.close()

    return jsonify({"message": "Slot cancelled successfully"}), 200


# -------------------------------------------------------
# MY BOOKINGS
# -------------------------------------------------------
@app.route('/my-bookings', methods=['GET'])
def my_bookings():
    user_email, error = decode_token()
    if error:
        return jsonify({"error": error}), 401

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            b.id AS booking_id,
            b.slot_id,
            b.booking_date,
            s.start_time,
            s.end_time
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        WHERE b.user_email = ?
        ORDER BY b.booking_date, s.start_time
    """, (user_email,))

    bookings = [dict(row) for row in cur.fetchall()]
    conn.close()

    return jsonify({"bookings": bookings})


# -------------------------------------------------------
# ERROR HANDLERS
# -------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Route not found"}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# -------------------------------------------------------
# RUN SERVER
# -------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)
