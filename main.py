from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from models import create_tables
from routes import slots, vehicles
from database import get_slot_by_id, free_slot
import uvicorn

# Initialize app
app = FastAPI(title="Smart Parking Management System")

# Create database tables if they don't exist
create_tables()

# Mount static folder (for CSS, JS, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")


# ✅ Root Route - main landing page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Default page that appears when app opens."""
    return templates.TemplateResponse("index.html", {"request": request})


# ✅ Free slot route (for displaying free_slot.html)
@app.get("/free_slot", response_class=HTMLResponse)
async def free_slot_page(request: Request):
    return templates.TemplateResponse("free_slot.html", {"request": request})


# ✅ Slot details route (dynamic view of parking slot)
@app.get("/slot/{slot_id}", response_class=HTMLResponse)
async def show_slot_details(request: Request, slot_id: int):
    slot = get_slot_by_id(slot_id)
    if not slot:
        return HTMLResponse("<h3>Invalid Slot ID</h3>", status_code=404)

    html_content = f"""
    <html>
    <head>
        <title>Slot {slot_id} Details</title>
    </head>
    <body>
        <h2>Parking Slot {slot_id}</h2>
        <p>Status: {"Occupied" if slot['is_occupied'] else "Free"}</p>
        <p>Vehicle ID: {slot['vehicle_id']}</p>
        <form action="/free/{slot_id}" method="post">
            <button type="submit">Leave Slot</button>
        </form>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ✅ Free the slot (for POST form submission)
@app.post("/free/{slot_id}")
async def free_the_slot(slot_id: int):
    free_slot(slot_id)
    return {"message": f"Slot {slot_id} has been freed successfully!"}


# ✅ Include your routers
app.include_router(slots.router, prefix="/slots", tags=["Slots"])
app.include_router(vehicles.router, prefix="/vehicles", tags=["Vehicles"])


# ✅ Run locally
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
