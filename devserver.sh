#!/bin/sh
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
