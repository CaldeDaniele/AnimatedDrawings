"""
FastAPI server for AnimatedDrawings GIF generation.
Supports synchronous POST /gif and async queue: POST /gif/submit → job_id, GET /gif/status/{job_id}, GET /gif/result/{job_id}.
"""
import json
import os
import queue
import tempfile
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response

from gif_pipeline import check_torchserve, process_image

app = FastAPI(
    title="AnimatedDrawings GIF API",
    description=(
        "Generate an animated GIF from an input image and motion configuration. "
        "Use POST /gif for synchronous (blocking) or POST /gif/submit + GET /gif/status/{job_id} for queue + polling."
    ),
    version="1.0.0",
)

_PIPELINE_LOCK = threading.Lock()
_JOBS_DIR = Path(os.environ.get("AD_JOBS_DIR", tempfile.gettempdir())) / "ad-gif-jobs"
_JOBS_DIR.mkdir(parents=True, exist_ok=True)
_job_status: Dict[str, Dict[str, Any]] = {}
_job_status_lock = threading.Lock()
_job_queue: queue.Queue = queue.Queue()


def _worker() -> None:
    while True:
        job_id = _job_queue.get()
        if job_id is None:
            break
        job_dir = _JOBS_DIR / job_id
        params_path = job_dir / "params.json"
        try:
            with _job_status_lock:
                _job_status[job_id]["status"] = "processing"
        except KeyError:
            continue
        try:
            if not params_path.is_file():
                raise FileNotFoundError(f"params.json not found for job {job_id}")
            with open(params_path, "r", encoding="utf-8") as f:
                params = json.load(f)
            input_path = job_dir / params["input_filename"]
            output_root = job_dir / "out"
            output_root.mkdir(parents=True, exist_ok=True)
            if not input_path.is_file():
                raise FileNotFoundError(f"Input image not found for job {job_id}")
            gif_path = process_image(
                input_path,
                output_root,
                motion_cfg=params.get("motion_cfg"),
                retarget_cfg=params.get("retarget_cfg"),
            )
            with _job_status_lock:
                _job_status[job_id]["status"] = "completed"
                _job_status[job_id]["gif_path"] = str(Path(gif_path).resolve())
                _job_status[job_id]["error"] = None
        except Exception as e:
            with _job_status_lock:
                if job_id in _job_status:
                    _job_status[job_id]["status"] = "failed"
                    _job_status[job_id]["error"] = str(e)
                    _job_status[job_id]["gif_path"] = None
        finally:
            _job_queue.task_done()


_worker_thread = threading.Thread(target=_worker, daemon=True)
_worker_thread.start()


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
    "/gif/submit",
    summary="Submit GIF job (queue)",
    description=(
        "Enqueues a GIF generation job. Returns job_id. Poll GET /gif/status/{job_id} for status; "
        "when status is 'completed', GET /gif/result/{job_id} returns the GIF bytes."
    ),
    responses={
        200: {"description": "Job submitted", "content": {"application/json": {"example": {"job_id": "abc123"}}}},
        400: {"description": "Invalid request"},
        503: {"description": "TorchServe unavailable/unhealthy"},
    },
)
def submit_gif(
    image: UploadFile = File(..., description="Input image (PNG/JPG/JPEG)."),
    motion_cfg: str = Form(
        ...,
        description="Motion config name or path (e.g. 'dab', 'config/motion/dab.yaml').",
    ),
    retarget_cfg: Optional[str] = Form(None, description="Optional retarget config. Default fair1_ppf."),
) -> JSONResponse:
    if not motion_cfg.strip():
        raise HTTPException(status_code=400, detail="motion_cfg cannot be empty")
    filename = image.filename or "input.png"
    suffix = Path(filename).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg"}:
        raise HTTPException(status_code=400, detail="image must be PNG/JPG/JPEG")
    if not check_torchserve():
        raise HTTPException(status_code=503, detail="TorchServe is not healthy")

    payload = image.file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="image payload is empty")

    job_id = uuid.uuid4().hex
    job_dir = _JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    input_filename = f"input{suffix}"
    input_path = job_dir / input_filename
    input_path.write_bytes(payload)
    params_path = job_dir / "params.json"
    params_path.write_text(
        json.dumps(
            {
                "motion_cfg": motion_cfg.strip(),
                "retarget_cfg": (retarget_cfg or "").strip() or None,
                "input_filename": input_filename,
            },
            indent=None,
        ),
        encoding="utf-8",
    )

    with _job_status_lock:
        _job_status[job_id] = {
            "status": "pending",
            "gif_path": None,
            "error": None,
        }
    _job_queue.put(job_id)

    return JSONResponse({"job_id": job_id})


@app.get(
    "/gif/status/{job_id}",
    summary="Get job status",
    description="Returns status: pending, processing, completed, or failed. When completed, gif_url is set for downloading.",
    responses={
        200: {"description": "Job status"},
        404: {"description": "Job not found"},
    },
)
def get_status(job_id: str) -> JSONResponse:
    with _job_status_lock:
        if job_id not in _job_status:
            raise HTTPException(status_code=404, detail="Job not found")
        rec = _job_status[job_id].copy()
    out: Dict[str, Any] = {"job_id": job_id, "status": rec["status"]}
    if rec.get("error"):
        out["error"] = rec["error"]
    if rec["status"] == "completed" and rec.get("gif_path"):
        out["gif_url"] = f"/gif/result/{job_id}"
    return JSONResponse(out)


@app.get(
    "/gif/result/{job_id}",
    summary="Get GIF result",
    description="Returns the generated GIF bytes when the job status is completed.",
    responses={
        200: {"description": "GIF bytes", "content": {"image/gif": {}}},
        404: {"description": "Job not found or not completed"},
    },
)
def get_result(job_id: str) -> Response:
    with _job_status_lock:
        if job_id not in _job_status:
            raise HTTPException(status_code=404, detail="Job not found")
        rec = _job_status[job_id]
        if rec["status"] != "completed" or not rec.get("gif_path"):
            raise HTTPException(
                status_code=404,
                detail="Job not completed or no result" if rec["status"] != "failed" else rec.get("error", "Job failed"),
            )
        gif_path = Path(rec["gif_path"])
    if not gif_path.is_file():
        raise HTTPException(status_code=404, detail="Result file no longer available")
    return Response(content=gif_path.read_bytes(), media_type="image/gif")


@app.post(
    "/gif",
    summary="Generate animated GIF (synchronous)",
    description=(
        "Accepts an image and motion configuration, runs the pipeline, and returns the GIF. "
        "Can timeout under load; prefer /gif/submit + polling for production."
    ),
    responses={
        200: {"description": "Generated GIF", "content": {"image/gif": {}}},
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
