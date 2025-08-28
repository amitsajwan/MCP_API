#!/usr/bin/env python3
"""start_demo.py

Unified demo/orchestration script for the OpenAPI MCP project.

Goals:
    * One command to launch everything you typically need.
    * Support dev mode (separate Vite dev server) and prod mode (serve built assets).
    * Optional mock API server for offline testing and FORCE_BASE_URL overrides.
    * Helpful colored console output & graceful shutdown (Ctrl+C).

Examples:
    Dev (MCP + Chatbot + Vite + Mock API):
        python start_demo.py --dev --with-mock

    Prod (build frontend then serve via chatbot):
        python start_demo.py --prod

    Dev without frontend (API only):
        python start_demo.py --dev --no-frontend

    Override base URL for a spec:
        python start_demo.py --dev --force-base cash=http://localhost:9001

Notes:
    * The script will run `npm install` automatically (once) if in dev mode and dependencies are missing.
    * On Windows PowerShell you can still use the same commands.
"""

import subprocess
import sys
import time
import threading
import os
import argparse
from pathlib import Path
from typing import Dict, List, Optional

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"


def color(txt: str, c: str) -> str:
    # Basic color wrapper; ignore if not a TTY
    if not sys.stdout.isatty():
        return txt
    return f"{c}{txt}{RESET}"

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        ('fastmcp', 'fastmcp'), 
        ('requests', 'requests'), 
        ('yaml', 'pyyaml'), 
        ('fastapi', 'fastapi'), 
        ('uvicorn', 'uvicorn'), 
        ('pydantic', 'pydantic'), 
        ('aiohttp', 'aiohttp'), 
        ('openapi_spec_validator', 'openapi_spec_validator')
    ]
    
    missing_packages = []
    for import_name, package_name in required_packages:
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n💡 Install them with:")
        print("   pip install -r requirements.txt")
        return False
    
    return True

def check_api_specs():
    """Check if API specification files exist"""
    api_specs_dir = Path("openapi_specs")
    required_specs = [
        "cash_api.yaml",
        "securities_api.yaml", 
        "cls_api.yaml",
        "mailbox_api.yaml"
    ]
    
    if not api_specs_dir.exists():
        print("❌ openapi_specs directory not found!")
        return False
    
    missing_specs = []
    for spec in required_specs:
        if not (api_specs_dir / spec).exists():
            missing_specs.append(spec)
    
    if missing_specs:
        print("❌ Missing API specification files:")
        for spec in missing_specs:
            print(f"   - openapi_specs/{spec}")
        return False
    
    return True

def _stream_output(name: str, process: subprocess.Popen):
    """Continuously stream stdout/stderr of a subprocess with prefixes."""
    def reader(stream, is_err=False):
        for line in iter(stream.readline, ''):
            line = line.rstrip()  # strip newline
            if not line:
                continue
            prefix = color(f"[{name}]", RED if is_err else CYAN)
            print(f"{prefix} {line}")
        stream.close()

    threading.Thread(target=reader, args=(process.stdout, False), daemon=True).start()
    threading.Thread(target=reader, args=(process.stderr, True), daemon=True).start()


def start_process(cmd: List[str], name: str, cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None, wait: float = 2.5):
    print(color(f"→ Starting {name}...", BOLD))
    try:
        process = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        _stream_output(name, process)
        time.sleep(wait)
        if process.poll() is None:
            print(color(f"✓ {name} started", GREEN))
            return process
        else:
            print(color(f"✗ {name} exited early (code {process.returncode})", RED))
            return None
    except FileNotFoundError:
        print(color(f"✗ Command not found for {name}: {cmd[0]}", RED))
        return None
    except Exception as e:
        print(color(f"✗ Failed to start {name}: {e}", RED))
        return None


def start_mcp_server(extra_env: Dict[str, str]):
    # Force HTTP transport so the chatbot (HTTP client) can reach it
    return start_process([sys.executable, "openapi_mcp_server.py", "--transport", "http"], "MCP", env={**os.environ, **extra_env})

def start_chatbot(extra_env: Dict[str, str]):
    return start_process([sys.executable, "chatbot_app.py"], "CHATBOT", env={**os.environ, **extra_env})


def start_mock_api(extra_env: Dict[str, str], port: int):
    # Pass explicit --port to avoid relying on script default; also set env for code paths that read it
    env = {**os.environ, **extra_env, "MOCK_API_PORT": str(port)}
    return start_process([sys.executable, "mock_api_server.py", "--port", str(port)], f"MOCK({port})", env=env)


def ensure_frontend_dependencies(frontend_dir: Path):
    import shutil
    if shutil.which('npm') is None:
        print(color("npm not found on PATH; skipping frontend (install Node.js from https://nodejs.org)", YELLOW))
        return False
    node_modules = frontend_dir / 'node_modules'
    pkg_json = frontend_dir / 'package.json'
    if not pkg_json.exists():
        print(color("No frontend/package.json found; skipping frontend start", YELLOW))
        return False
    if node_modules.exists():
        return True
    print(color("Installing frontend dependencies (npm install)…", BOLD))
    proc = subprocess.run(["npm", "install"], cwd=str(frontend_dir))
    if proc.returncode != 0:
        print(color("npm install failed; continuing without frontend", RED))
        return False
    return True


def start_frontend_dev(frontend_dir: Path, port: int):
    # Vite will auto choose a new port if busy if we pass --port
    return start_process(["npm", "run", "dev", "--", "--port", str(port)], "FRONTEND", cwd=str(frontend_dir))


def build_frontend(frontend_dir: Path):
    print(color("Building production frontend (npm run build)…", BOLD))
    proc = subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir))
    if proc.returncode != 0:
        print(color("Frontend build failed; continuing (chatbot will show placeholder)", RED))
        return False
    print(color("Frontend build complete", GREEN))
    return True

def monitor_processes(processes: Dict[str, subprocess.Popen]):
    try:
        while True:
            for name, proc in list(processes.items()):
                if proc and proc.poll() is not None:
                    print(color(f"⚠ {name} exited (code {proc.returncode})", YELLOW))
                    processes.pop(name, None)
            if not processes:
                print(color("All processes exited", YELLOW))
                break
            time.sleep(4)
    except KeyboardInterrupt:
        print(color("\nShutting down…", BOLD))
        for name, proc in processes.items():
            try:
                proc.terminate()
            except Exception:
                pass
        # Grace period
        deadline = time.time() + 5
        for name, proc in processes.items():
            if proc.poll() is None and time.time() < deadline:
                try:
                    proc.wait(timeout=max(0, deadline - time.time()))
                except subprocess.TimeoutExpired:
                    proc.kill()
        print(color("Shutdown complete", GREEN))


def parse_args():
    parser = argparse.ArgumentParser(description="Unified demo launcher")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dev', action='store_true', help='Dev mode (Vite dev server)')
    mode.add_argument('--prod', action='store_true', help='Production mode (build + serve)')
    parser.add_argument('--with-mock', action='store_true', help='Start mock_api_server.py')
    parser.add_argument('--mock-port', type=int, default=9001, help='Port for mock API server')
    parser.add_argument('--vite-port', type=int, default=9517, help='Port for Vite dev server')
    parser.add_argument('--no-frontend', action='store_true', help='Skip starting frontend even in dev mode')
    parser.add_argument('--force-base', action='append', metavar='SPEC=URL', help='Force base URL for a spec (can repeat)')
    parser.add_argument('--fast-exit', action='store_true', help='Exit after starting (do not monitor)')
    return parser.parse_args()

def main():
    args = parse_args()
    print(color("OpenAPI MCP Demo Launcher", BOLD))
    print("=" * 60)
    mode = 'dev' if args.dev or (not args.prod) else 'prod'
    print(f"Mode: {mode}")

    # Pre-flight checks
    if not check_dependencies():
        return
    check_api_specs()  # Non-fatal; user may load later

    extra_env = {}
    if args.force_base:
        for spec_pair in args.force_base:
            if '=' not in spec_pair:
                print(color(f"Ignoring malformed --force-base '{spec_pair}' (expected SPEC=URL)", YELLOW))
                continue
            spec, url = spec_pair.split('=', 1)
            env_key = f"FORCE_BASE_URL_{spec.strip().upper()}"
            extra_env[env_key] = url.strip()
    processes = {}

    # Mock API server first (so base URLs resolve)
    if args.with_mock:
        mock_proc = start_mock_api(extra_env, args.mock_port)
        if mock_proc:
            processes['MOCK'] = mock_proc
            # If user did not specify a base override for 'cash', set a helpful default
            if not any(k.startswith('FORCE_BASE_URL_CASH') for k in extra_env):
                extra_env['FORCE_BASE_URL_CASH'] = f"http://localhost:{args.mock_port}"

    # MCP server
    mcp_proc = start_mcp_server(extra_env)
    if not mcp_proc:
        print(color("Cannot continue without MCP server", RED))
        return
    processes['MCP'] = mcp_proc

    # Chatbot (serves API + optionally built frontend)
    frontend_dir = Path('frontend')  # define once for subsequent logic
    if mode == 'prod':
        # build frontend first if exists
        if frontend_dir.exists() and not args.no_frontend:
            if ensure_frontend_dependencies(frontend_dir):
                build_frontend(frontend_dir)
    chatbot_proc = start_chatbot(extra_env)
    if not chatbot_proc:
        print(color("Chatbot failed; shutting down", RED))
        for p in processes.values():
            p.terminate()
        return
    processes['CHATBOT'] = chatbot_proc

    # Frontend dev server (dev mode only)
    if mode == 'dev' and not args.no_frontend:
        frontend_dir = Path('frontend')
        if frontend_dir.exists():
            if ensure_frontend_dependencies(frontend_dir):
                fe_proc = start_frontend_dev(frontend_dir, args.vite_port)
                if fe_proc:
                    processes['FRONTEND'] = fe_proc
        else:
            print(color("No frontend directory present; skipping UI", YELLOW))

    print("\n" + color("Services Running", BOLD))
    print("- MCP Server:       http://localhost:9000")
    print("- Chatbot API:      http://localhost:9080")
    if 'FRONTEND' in processes:
        print(f"- Vite Dev UI:      http://localhost:{args.vite_port}")
    if mode == 'prod' and not args.no_frontend:
        print("- Built UI (served): http://localhost:9080/app/")
    if 'MOCK' in processes:
        print(f"- Mock API:         http://localhost:{args.mock_port}")
    if extra_env:
        print(color("Base URL overrides:", DIM))
        for k, v in extra_env.items():
            if k.startswith('FORCE_BASE_URL'):
                print(f"  {k} = {v}")

    print("\nTry queries:")
    print("  Show me all pending payments that need approval")
    print("  What's my current portfolio value?")
    print("  Give me a summary of all financial activities")
    print("\nCtrl+C to stop.")

    if args.fast_exit:
        print(color("--fast-exit specified; not monitoring processes", YELLOW))
        return
    monitor_processes(processes)

if __name__ == "__main__":
    main()
