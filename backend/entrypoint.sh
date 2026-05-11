#!/bin/bash

# Script para determinar qué comando correr basado en SERVICE_TYPE
if [ "$SERVICE_TYPE" = "worker" ]; then
    echo "🔧 Starting Worker Scheduler..."
    exec python -m app.workers.continuous_scheduler
else
    echo "🌐 Starting Web Server..."
    exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
fi
