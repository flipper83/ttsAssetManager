#!/bin/bash
cd "$(dirname "$0")"
.venv/bin/python3 -m tts_manager.cli "$@"
