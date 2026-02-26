"""
Reusable GIF pipeline for AnimatedDrawings:
image -> annotations -> rendered video.gif
"""
import os
import sys
from pathlib import Path
from typing import Optional, Union

import requests
import yaml


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent


def get_examples_path() -> Path:
    return get_repo_root() / "examples"


def check_torchserve(url: str = "http://localhost:8080/ping") -> bool:
    try:
        r = requests.get(url, timeout=2)
        return r.status_code == 200 and (r.json() or {}).get("status") == "Healthy"
    except Exception:
        return False


def _resolve_cfg_path(
    examples_path: Path,
    cfg_value: Optional[Union[str, Path]],
    cfg_type: str,
    default_name: str,
) -> str:
    if cfg_type not in {"motion", "retarget"}:
        raise ValueError(f"Invalid cfg_type: {cfg_type}")

    if cfg_value is None:
        p = examples_path / "config" / cfg_type / default_name
        if p.suffix == "":
            p = p.with_suffix(".yaml")
        if not p.is_file():
            raise FileNotFoundError(f"Default {cfg_type} config not found: {p}")
        return str(p.resolve())

    raw = str(cfg_value).strip()
    if not raw:
        raise ValueError(f"{cfg_type}_cfg cannot be empty")

    p = Path(raw)
    if p.is_absolute():
        if not p.is_file():
            raise FileNotFoundError(f"{cfg_type} config not found: {p}")
        return str(p.resolve())

    candidates = []
    if "/" not in raw and "\\" not in raw:
        short = raw if raw.endswith(".yaml") else f"{raw}.yaml"
        candidates.append(examples_path / "config" / cfg_type / short)
    candidates.append(examples_path / raw)
    if not raw.endswith(".yaml"):
        candidates.append(examples_path / f"{raw}.yaml")

    for c in candidates:
        if c.is_file():
            return str(c.resolve())

    raise FileNotFoundError(
        f"{cfg_type} config not found from '{cfg_value}'. Tried: "
        + ", ".join(str(c) for c in candidates)
    )


def _render_with_mvc(anno_dir: Path, motion_cfg: str, retarget_cfg: str, use_mesa: bool) -> None:
    mvc_cfg = {
        "scene": {
            "ANIMATED_CHARACTERS": [
                {
                    "character_cfg": str((anno_dir / "char_cfg.yaml").resolve()),
                    "motion_cfg": str(Path(motion_cfg).resolve()),
                    "retarget_cfg": str(Path(retarget_cfg).resolve()),
                }
            ]
        },
        "controller": {
            "MODE": "video_render",
            "OUTPUT_VIDEO_PATH": str((anno_dir / "video.gif").resolve()),
        },
    }
    if use_mesa:
        mvc_cfg["view"] = {"USE_MESA": True}

    mvc_cfg_path = anno_dir / "mvc_cfg.yaml"
    with mvc_cfg_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(mvc_cfg, f, sort_keys=False)

    import animated_drawings.render as ad_render  # noqa: E402

    ad_render.start(str(mvc_cfg_path))


def process_image(
    img_path: Union[str, Path],
    output_root: Union[str, Path],
    motion_cfg: Optional[Union[str, Path]] = None,
    retarget_cfg: Optional[Union[str, Path]] = None,
) -> str:
    img_path = Path(img_path).resolve()
    output_root = Path(output_root).resolve()
    if not img_path.is_file():
        raise FileNotFoundError(f"Image not found: {img_path}")

    if not check_torchserve():
        raise RuntimeError(
            "TorchServe is not running or unhealthy. Ensure http://localhost:8080/ping returns Healthy."
        )

    repo_root = get_repo_root()
    examples_path = get_examples_path()
    for p in (str(repo_root), str(examples_path)):
        if p not in sys.path:
            sys.path.insert(0, p)

    from image_to_annotations import image_to_annotations  # noqa: E402

    stem = img_path.stem
    anno_dir = output_root / stem
    anno_dir.mkdir(parents=True, exist_ok=True)

    motion_cfg_path = _resolve_cfg_path(examples_path, motion_cfg, "motion", "dab.yaml")
    retarget_cfg_path = _resolve_cfg_path(examples_path, retarget_cfg, "retarget", "fair1_ppf.yaml")

    image_to_annotations(str(img_path), str(anno_dir))

    use_mesa = os.environ.get("AD_USE_MESA", "").lower() in {"1", "true", "yes"}
    _render_with_mvc(anno_dir, motion_cfg_path, retarget_cfg_path, use_mesa=use_mesa)

    gif_path = anno_dir / "video.gif"
    if not gif_path.is_file():
        raise RuntimeError(f"Pipeline did not produce {gif_path}")
    return str(gif_path)
