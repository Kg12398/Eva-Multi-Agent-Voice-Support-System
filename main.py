"""
🎙️ Gauri Multi-Agent Voice Support Suite — Master Entry Point

This root-level script provides a unified launcher for all backend services.
You can run the LiveKit Voice Worker, the FastAPI REST Server, or both simultaneously!

Usage:
  python main.py          # Starts the LiveKit Voice Worker (Default)
  python main.py worker   # Starts the LiveKit Voice Worker
  python main.py api      # Starts the FastAPI REST Server (Dashboard Backend)
  python main.py all      # Starts BOTH services simultaneously in parallel
"""

import sys
import subprocess
import argparse
from multiprocessing import Process


def run_worker():
    """Execute the LiveKit Agent voice pipeline worker."""
    print("\n🎙️  Starting Gauri LiveKit Voice Agent Worker...")
    try:
        subprocess.run([sys.executable, "-m", "app.voice_pipeline.livekit_worker", "dev"])
    except KeyboardInterrupt:
        print("\nStopping LiveKit Voice Agent Worker...")


def run_api():
    """Execute the FastAPI server with uvicorn reload."""
    print("\n🚀 Starting FastAPI REST API Dashboard Server...")
    try:
        import uvicorn
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
    except KeyboardInterrupt:
        print("\nStopping FastAPI Server...")
    except ImportError:
        print("\n[ERROR] 'uvicorn' is not installed. Please run: pip install -r requirements.txt")


def run_all():
    """Launch both the LiveKit Worker and FastAPI Server in parallel processes."""
    print("\n🔥 Starting Gauri System: Voice Worker & FastAPI Server in parallel...")
    
    worker_process = Process(target=run_worker)
    api_process = Process(target=run_api)
    
    try:
        worker_process.start()
        api_process.start()
        
        worker_process.join()
        api_process.join()
    except KeyboardInterrupt:
        print("\n[SYSTEM] Interrupted. Terminating all processes...")
        worker_process.terminate()
        api_process.terminate()
        worker_process.join()
        api_process.join()
        print("[SYSTEM] All services stopped. Goodbye!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gauri Multi-Agent Voice Support Suite Master CLI Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "mode", 
        choices=["worker", "api", "all"], 
        nargs="?", 
        default="worker",
        help="Service to launch: 'worker' (LiveKit Voice Agent - Default), 'api' (FastAPI Backend), or 'all' (Both)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "worker":
        run_worker()
    elif args.mode == "api":
        run_api()
    elif args.mode == "all":
        run_all()
