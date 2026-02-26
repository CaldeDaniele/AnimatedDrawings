"""
FastAPI server for AnimatedDrawings GIF generation.
"""
import tempfile
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

from gif_pipeline import check_torchserve, process_image

app = FastAPI(
    title="AnimatedDrawings GIF API",
    description=(
        "Generate an animated GIF from an input image and motion configuration "
        "using AnimatedDrawings + TorchServe."
    ),
    version="1.0.0",
)

_PIPELINE_LOCK = threading.Lock()


@app.get(
    "/health",
    summary="Health check",
    description="Checks whether TorchServe is reachable and healthy.",
    responses={
        200: {"description": "Service healthy"},
        503: {"description": "TorchServe unavailable/unhealthy"},
    },
)
def health() -> JSONResponse:
    if not check_torchserve():
        raise HTTPException(status_code=503, detail="TorchServe is not healthy")
    return JSONResponse({"status": "ok"})


@app.post(
    "/gif",
    summary="Generate animated GIF",
    description=(
        "Accepts an image and motion configuration, runs the AnimatedDrawings pipeline, "
        "and returns the generated GIF."
    ),
    responses={
        200: {
            "description": "Generated GIF",
            "content": {"image/gif": {}},
        },
        400: {"description": "Invalid request"},
        503: {"description": "TorchServe unavailable/unhealthy"},
        500: {"description": "Pipeline error"},
    },
)
def generate_gif(
    image: UploadFile = File(..., description="Input image (PNG/JPG/JPEG)."),
    motion_cfg: str = Form(
        ...,
        description=(
            "Motion config name or path. Examples: 'dab', "
            "'config/motion/dab.yaml', or an absolute path."
        ),
    ),
    retarget_cfg: Optional[str] = Form(
        None,
        description=(
            "Optional retarget config name or path. Default is fair1_ppf."
        ),
    ),
) -> Response:
    if not motion_cfg.strip():
        raise HTTPException(status_code=400, detail="motion_cfg cannot be empty")

    filename = image.filename or "input.png"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="image must be PNG/JPG/JPEG")

    if not check_torchserve():
        raise HTTPException(status_code=503, detail="TorchServe is not healthy")

    with tempfile.TemporaryDirectory(prefix="ad-api-") as tmp_dir:
        tmp_root = Path(tmp_dir)
        input_path = tmp_root / f"input{suffix}"
        output_root = tmp_root / "out"
        output_root.mkdir(parents=True, exist_ok=True)

        payload = image.file.read()
        if not payload:
            raise HTTPException(status_code=400, detail="image payload is empty")
        input_path.write_bytes(payload)

        try:
            with _PIPELINE_LOCK:
                gif_path = process_image(
                    input_path,
                    output_root,
                    motion_cfg=motion_cfg,
                    retarget_cfg=retarget_cfg,
                )
            gif_bytes = Path(gif_path).read_bytes()
        except FileNotFoundError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        except RuntimeError as e:
            msg = str(e)
            if "TorchServe" in msg:
                raise HTTPException(status_code=503, detail=msg) from e
            raise HTTPException(status_code=500, detail=msg) from e
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e)) from e

    return Response(content=gif_bytes, media_type="image/gif")
