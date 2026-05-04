import os
import json
from src.core.config import Config

def save_output(data: dict):
    """Guarda la respuesta final en latest_response.json."""
    os.makedirs(Config.METRICS_DIR, exist_ok=True)
    file_path = os.path.join(Config.METRICS_DIR, "latest_response.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def save_metrics_log(metrics: dict):
    """Añade métricas al histórico metrics.json."""
    os.makedirs(Config.METRICS_DIR, exist_ok=True)
    log_file = os.path.join(Config.METRICS_DIR, "metrics.json")
    history = []
    
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            try:
                history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []
    
    history.append(metrics)
    with open(log_file, "w") as f:
        json.dump(history, f, indent=4)

def save_history(data: dict):
    """Añade el payload completo al histórico history.json."""
    os.makedirs(Config.METRICS_DIR, exist_ok=True)
    log_file = os.path.join(Config.METRICS_DIR, "history.json")
    history = []
    
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            try:
                history = json.load(f)
            except (json.JSONDecodeError, IOError):
                history = []
                
    history.append(data)
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
