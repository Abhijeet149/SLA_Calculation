import io
import trimesh

def analyze_file_from_bytes(contents: bytes, filename: str):

    filename = filename.lower()

    if filename.endswith(".stl"):

        mesh = trimesh.load(io.BytesIO(contents), file_type="stl")

        if mesh.is_empty:
            raise ValueError("Invalid STL file")

        bbox = mesh.bounds
        dimensions = bbox[1] - bbox[0]

        return {
            "file_type": "STL",
            "file_name": filename,
            "bounding_box": {
                "x_length": float(dimensions[0]),
                "y_width": float(dimensions[1]),
                "z_height": float(dimensions[2]),
            },
            "volume": float(mesh.volume),
            "surface_area": float(mesh.area),
        }

    else:
        raise ValueError("Only STL supported for now")