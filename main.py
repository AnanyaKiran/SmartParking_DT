from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from models import create_tables
from routes import slots, vehicles
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from seed_data import seed_database
from routes import registration,free_slot

# ✅ Lifespan handles startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting up...")
    create_tables()  # Create tables automatically on startup
    seed_database()
    yield
    print("🛑 Shutting down...")

# Initialize FastAPI app with lifespan
app = FastAPI(title="Smart Parking Management System", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(registration.router, prefix="/register", tags=["Registration"])
app.include_router(slots.router, prefix="/slots", tags=["Slots"])
app.include_router(vehicles.router, prefix="/vehicles", tags=["Vehicles"])
app.include_router(free_slot.router)

# ✅ Serve index.html at home route
from database import get_db_connection

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.slot_id, s.is_occupied, v.license_plate, v.vehicle_type, u.user_name
        FROM slots s
        LEFT JOIN vehicles v ON s.vehicle_id = v.vehicle_id
        LEFT JOIN users u ON v.user_id = u.user_id
        ORDER BY s.slot_id;
    """)
    slots = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return templates.TemplateResponse("index.html", {"request": request, "slots": slots})

# Enable CORS (important for frontend-backend communication)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Run app
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
