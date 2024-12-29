INPUT_SCHEMA = {
    "id": {
        "type": str,
        "required": True,
    },
    "prompt": {
        "type": str,
        "required": True,
    },
    "height": {"type": int, "required": False, "default": 1280},
    "width": {"type": int, "required": False, "default": 720},
    "video_length": {"type": int, "required": False, "default": 129},
    "seed": {"type": int, "required": False, "default": 42},
    "negative_prompt": {"type": str, "required": False, "default": ""},
    "infer_steps": {"type": int, "required": False, "default": 30},
    "guidance_scale": {"type": float, "required": False, "default": 6},
    "flow_shift": {"type": float, "required": False, "default": 5.0},
    "num_videos_per_prompt": {"type": int, "required": False, "default": 1},
    "webhook_url": {"type": str, "required": True},
    "ulysses_degree": {"type": int, "required": False, "default": 2},
    "ring_degree": {"type": int, "required": False, "default": 2},
}
