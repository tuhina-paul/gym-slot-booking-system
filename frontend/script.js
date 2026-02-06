const BASE_URL = "http://127.0.0.1:5000";

/* ---------------------------
   DATE HELPER
---------------------------- */
function getTodayDate() {
    return new Date().toISOString().split("T")[0];
}

/* ---------------------------
   AUTH CHECK
---------------------------- */
function checkAuth() {
    const token = localStorage.getItem("token");
    const page = window.location.pathname;

    if (!token && !page.includes("login") && !page.includes("register")) {
        window.location.href = "login.html";
    }
}

/* ---------------------------
   LOGOUT
---------------------------- */
function logout() {
    localStorage.removeItem("token");
    window.location.href = "login.html";
}

/* ---------------------------
   DASHBOARD
---------------------------- */
async function loadDashboard() {
    checkAuth();
    const today = getTodayDate();
    const token = localStorage.getItem("token");

    try {
        // Total slots
        const slotsRes = await fetch(`${BASE_URL}/slots?date=${today}`);
        const slots = await slotsRes.json();
        document.getElementById("totalSlots").innerText = slots.length;

        // My bookings
        const myRes = await fetch(`${BASE_URL}/my-bookings`, {
            headers: { Authorization: token }
        });
        const myData = await myRes.json();
        document.getElementById("userBookingsCount").innerText =
            myData.bookings.length;
    } catch (err) {
        console.error("Dashboard error", err);
    }
}

/* ---------------------------
   LOAD SLOTS
---------------------------- */
async function loadSlots() {
    checkAuth();
    const today = getTodayDate();
    const container = document.getElementById("slotList");

    try {
        const res = await fetch(`${BASE_URL}/slots?date=${today}`);
        const slots = await res.json();

        container.innerHTML = slots.map(slot => `
            <div class="slot-card">
                <h3>${slot.start_time} - ${slot.end_time}</h3>
                <p>Status: <b>${slot.booked ? "Booked" : "Available"}</b></p>
                <button 
                    onclick="bookSlot(${slot.id})"
                    ${slot.booked ? "disabled" : ""}
                >
                    ${slot.booked ? "Already Booked" : "Book Slot"}
                </button>
            </div>
        `).join("");
    } catch (err) {
        container.innerHTML = "<p>Error loading slots</p>";
    }
}

/* ---------------------------
   BOOK SLOT
---------------------------- */
async function bookSlot(slotId) {
    const token = localStorage.getItem("token");
    const today = getTodayDate();

    const res = await fetch(`${BASE_URL}/book-slot`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: token
        },
        body: JSON.stringify({
            slot_id: slotId,
            date: today
        })
    });

    const data = await res.json();
    alert(data.message || data.error);
    loadSlots();
}

/* ---------------------------
   MY BOOKINGS
---------------------------- */
async function loadMyBookings() {
    checkAuth();

    const container = document.getElementById("myBookingList");
    const token = localStorage.getItem("token");

    const res = await fetch(`${BASE_URL}/my-bookings`, {
        headers: { Authorization: token }
    });

    const data = await res.json();

    if (!data.bookings || data.bookings.length === 0) {
        container.innerHTML = "<p>No bookings found.</p>";
        return;
    }

    container.innerHTML = data.bookings.map(b => `
        <div class="slot-card">
            <h3>${b.start_time} - ${b.end_time}</h3>
            <p>Date: ${b.booking_date}</p>
            <button onclick="cancelSlot(${b.slot_id}, '${b.booking_date}')">
                Cancel
            </button>
        </div>
    `).join("");
}


/* ---------------------------
   CANCEL SLOT
---------------------------- */
async function cancelSlot(slotId, date) {
    const token = localStorage.getItem("token");

    console.log("Cancelling:", slotId, date); // DEBUG LINE

    const res = await fetch(`${BASE_URL}/cancel-slot`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: token
        },
        body: JSON.stringify({
            slot_id: slotId,
            date: date
        })
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.error);
    } else {
        alert("Slot cancelled successfully");
        loadMyBookings();
    }
}



/* ---------------------------
   LOGIN
---------------------------- */
async function loginUser() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    const res = await fetch("http://127.0.0.1:5000/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.error);
        return;
    }

    localStorage.setItem("token", data.token);
    alert("Login successful!");
    window.location.href = "index.html";
}


/* ---------------------------
   REGISTER
---------------------------- */
async function registerUser() {

    const name = document.getElementById("name").value;
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    const res = await fetch("http://127.0.0.1:5000/register", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ name, email, password })
    });

    const data = await res.json();

    if (res.ok) {
        alert("Registered!");
    } else {
        alert(data.error);
    }
}
