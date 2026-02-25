from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List
from pydantic import BaseModel
import os
import sys

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


from app.geometry import analyze_file_from_bytes

app = FastAPI()

# Mount static folder
## app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount(
    "/static",
    StaticFiles(directory=resource_path("static")),
    name="static"
)

# templates = Jinja2Templates(directory="templates")
templates = Jinja2Templates(directory=resource_path("templates"))

# Store geometries
latest_geometries = []


# ---------------- HOME ----------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "file_urls": []
        }
    )


# ---------------- UPLOAD ----------------
@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, files: List[UploadFile] = File(...)):

    global latest_geometries
    latest_geometries = []

    file_urls = []

    os.makedirs("static/uploads", exist_ok=True)

    for file in files:
        contents = await file.read()

        geometry = analyze_file_from_bytes(contents, file.filename)
        latest_geometries.append(geometry)

        file_path = f"static/uploads/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(contents)

        file_urls.append(f"/{file_path}")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "file_urls": file_urls
        }
    )


# ---------------- CALCULATION ----------------
class CalculationInput(BaseModel):
    silicon_rate: float
    part_rate: float
    master_part: float
    boundary_spacing: float
    part_waste_gate: float


@app.post("/calculate")
async def calculate(data: CalculationInput):

    global latest_geometries

    if not latest_geometries:
        return {"error": "No STL uploaded yet"}

    geometry = latest_geometries[0]

    x = geometry["bounding_box"]["x_length"]
    y = geometry["bounding_box"]["y_width"]
    z = geometry["bounding_box"]["z_height"]
    volume = geometry["volume"]

    # Add spacing
    new_x = x + data.boundary_spacing
    new_y = y + data.boundary_spacing
    new_z = z + data.boundary_spacing

    # # Volume in CC
    volume_in_cc = (volume * 0.001)

    # # Weight
    weight = (volume_in_cc * 1.1)

    # # Master Pattern Cost
    master_pattern_cost = (volume_in_cc * data.master_part)

    # # Silicon Mold Cost
    mold_block_volume_mm3 = new_x * new_y * new_z
    mold_block_volume_cc = mold_block_volume_mm3 * 0.001
    mold_cost = (mold_block_volume_cc * 1.1 * data.silicon_rate)

    # # Development Cost
    development_cost = (master_pattern_cost + mold_cost)

    # # Part Cost
    part_cost = (weight + data.part_waste_gate) * data.part_rate
  

    return {
        "x_dimension": x,
        "y_dimension": y,
        "z_dimension": z,
        "volume": volume,

        "new_X": new_x,
        "new_Y": new_y,
        "new_Z": new_z,

        "volume_in_cc": volume_in_cc,
        "weight": weight,

        "master_pattern_cost": master_pattern_cost,
        "mold_cost": mold_cost,
        "development_cost": development_cost,
        "part_cost": part_cost
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False, log_level="info")