from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from models import create_tables
from routes import slots, vehicles
import uvicorn

# Initialize FastAPI app
app = FastAPI(title="Smart Parking Management System")

# Create tables if they don't exist
create_tables()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Root page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Include routers
app.include_router(slots.router, prefix="/slots", tags=["Slots"])
app.include_router(vehicles.router, prefix="/vehicles", tags=["Vehicles"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
