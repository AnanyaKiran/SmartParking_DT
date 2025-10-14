from fastapi import FastAPI
from models import create_tables
from routes import slots, vehicles
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from database import get_slot_by_id, free_slot  # example functions


# Initialize app
app = FastAPI(title="Smart Parking Management System")

# Create database tables if they don't exist
create_tables()

# Mount your static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html when someone visits the root URL
@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# Include your routers
app.include_router(slots.router)
app.include_router(vehicles.router)

# Landing page (user view)
@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.get("/slot/{slot_id}", response_class=HTMLResponse)
def show_slot_details(slot_id: int):
    slot = get_slot_by_id(slot_id)
    if not slot:
        return "<h3>Invalid Slot ID</h3>"
    
    html = f"""
    <html>
    <head>
        <title>Slot {slot_id} Details</title>
    </head>
    <body>
        <h2>Parking Slot {slot_id}</h2>
        <p>Status: {slot['status']}</p>
        <p>Vehicle Type: {slot['vehicle_type']}</p>
        <form action="/free/{slot_id}" method="post">
            <button type="submit">Leave Slot</button>
        </form>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
