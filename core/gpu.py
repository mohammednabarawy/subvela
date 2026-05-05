"""
GPU detection and configuration for SubVela.

Provides automatic CUDA detection for CTranslate2-based models
(faster-whisper transcription and NLLB translation).
"""

import os
import sys
import functools


def _inject_cuda_paths():
    """Inject NVIDIA pip paths into DLL search so CTranslate2 can find cuBLAS on Windows."""
    if os.name != "nt":
        return
    try:
        import site
        site_packages = getattr(site, "getsitepackages", lambda: [])()
        if not site_packages and hasattr(site, "USER_SITE"):
            site_packages = [site.USER_SITE]
        for sp in site_packages:
            nvidia_dir = os.path.join(sp, "nvidia")
            if os.path.exists(nvidia_dir):
                for module in os.listdir(nvidia_dir):
                    bin_dir = os.path.join(nvidia_dir, module, "bin")
                    if os.path.exists(bin_dir):
                        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
                        if hasattr(os, "add_dll_directory"):
                            try:
                                os.add_dll_directory(bin_dir)
                            except Exception:
                                pass
    except Exception:
        pass

# Run early so any subsequent imports of ctranslate2 find the CUDA DLLs
_inject_cuda_paths()


@functools.lru_cache(maxsize=1)
def detect_gpu() -> dict:
    """Detect CUDA GPU availability and return device configuration.

    Returns a dict with:
        available (bool): True if a usable CUDA GPU was found.
        device (str): "cuda" or "cpu".
        compute_type (str): "float16" for CUDA, "int8" for CPU.
        gpu_name (str): Human-readable GPU name, or empty string.
        vram_mb (int): Approximate VRAM in MB, or 0.
        reason (str): Why GPU is or isn't available.
    """
    # Allow manual override via environment variable
    force = os.environ.get("SUBVELA_DEVICE", "").strip().lower()
    if force == "cpu":
        return {
            "available": False,
            "device": "cpu",
            "compute_type": "int8",
            "gpu_name": "",
            "vram_mb": 0,
            "reason": "GPU disabled via SUBVELA_DEVICE=cpu",
        }

    # Try ctranslate2 CUDA support first (this is what faster-whisper uses)
    try:
        import ctranslate2
        supported = ctranslate2.get_supported_compute_types("cuda")
        if supported:
            gpu_name, vram_mb = _get_nvidia_gpu_info()
            compute_type = _pick_compute_type(supported, vram_mb)
            return {
                "available": True,
                "device": "cuda",
                "compute_type": compute_type,
                "gpu_name": gpu_name,
                "vram_mb": vram_mb,
                "reason": f"CUDA available via CTranslate2 ({gpu_name})",
            }
    except Exception:
        pass

    # Fallback: check if CUDA toolkit is visible at all
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            vram_mb = torch.cuda.get_device_properties(0).total_mem // (1024 * 1024)
            return {
                "available": True,
                "device": "cuda",
                "compute_type": "float16",
                "gpu_name": gpu_name,
                "vram_mb": vram_mb,
                "reason": f"CUDA available via PyTorch ({gpu_name})",
            }
    except Exception:
        pass

    return {
        "available": False,
        "device": "cpu",
        "compute_type": "int8",
        "gpu_name": "",
        "vram_mb": 0,
        "reason": "No CUDA-capable GPU detected. Install ctranslate2 with CUDA support.",
    }


def _get_nvidia_gpu_info() -> tuple[str, int]:
    """Try to get GPU name and VRAM via nvidia-smi or pynvml."""
    # Try pynvml first (more reliable in Python)
    try:
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode("utf-8")
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        vram_mb = mem_info.total // (1024 * 1024)
        pynvml.nvmlShutdown()
        return name, vram_mb
    except Exception:
        pass

    # Fallback to PyTorch
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            vram_mb = torch.cuda.get_device_properties(0).total_mem // (1024 * 1024)
            return name, vram_mb
    except Exception:
        pass

    # Last resort: nvidia-smi CLI
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            line = result.stdout.strip().split("\n")[0]
            parts = line.split(",")
            name = parts[0].strip()
            vram_mb = int(parts[1].strip()) if len(parts) > 1 else 0
            return name, vram_mb
    except Exception:
        pass

    return "NVIDIA GPU", 0


def _pick_compute_type(supported_types: list[str], vram_mb: int) -> str:
    """Pick the best compute type based on GPU VRAM and supported types.

    For RTX 5060 Ti (16 GB VRAM), float16 is ideal.
    For GPUs with < 4 GB, use int8 to save memory.
    """
    if vram_mb > 0 and vram_mb < 4096:
        # Low VRAM: prefer int8 quantization
        if "int8" in supported_types:
            return "int8"
        if "int8_float16" in supported_types:
            return "int8_float16"

    # High VRAM: prefer float16 for best quality
    if "float16" in supported_types:
        return "float16"
    if "int8_float16" in supported_types:
        return "int8_float16"
    if "int8" in supported_types:
        return "int8"

    return supported_types[0] if supported_types else "float16"


def get_device_and_compute() -> tuple[str, str]:
    """Convenience: returns (device, compute_type) tuple."""
    info = detect_gpu()
    return info["device"], info["compute_type"]


def print_gpu_status():
    """Print GPU detection results to stdout."""
    info = detect_gpu()
    if info["available"]:
        print(f"[GPU] OK: {info['gpu_name']} ({info['vram_mb']} MB VRAM)")
        print(f"[GPU]   Device: {info['device']}, Compute: {info['compute_type']}")
    else:
        print(f"[GPU] NONE: Running on CPU - {info['reason']}")
