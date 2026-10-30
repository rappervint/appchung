import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, 'token_usage.json')

def load_token_stats() -> dict:
    default_stats = {
        "total_requests": 0,
        "total_tokens": 0,
        "prompt_tokens": 0,
        "response_tokens": 0,
        "saved_local_requests": 0,
        "last_used_model": "gemini-3.5-flash-lite",
        "last_call": {
            "time": "",
            "model": "",
            "prompt_tokens": 0,
            "response_tokens": 0,
            "total_tokens": 0
        },
        "by_model": {},
        "by_date": {}
    }
    if not os.path.exists(TOKEN_FILE):
        return default_stats
    try:
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Đảm bảo có đầy đủ các key
            for k, v in default_stats.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception as e:
        print(f"[TokenTracker] Lỗi đọc {TOKEN_FILE}: {e}")
        return default_stats

def save_token_stats(stats: dict):
    try:
        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[TokenTracker] Lỗi lưu {TOKEN_FILE}: {e}")

def record_token_usage(model: str, prompt_tokens: int, resp_tokens: int, total_tokens: int = 0):
    """Ghi nhận token đã dùng sau mỗi lần gọi Gemini thành công"""
    if total_tokens <= 0:
        total_tokens = prompt_tokens + resp_tokens

    stats = load_token_stats()
    stats["total_requests"] = stats.get("total_requests", 0) + 1
    stats["total_tokens"] = stats.get("total_tokens", 0) + total_tokens
    stats["prompt_tokens"] = stats.get("prompt_tokens", 0) + prompt_tokens
    stats["response_tokens"] = stats.get("response_tokens", 0) + resp_tokens
    stats["last_used_model"] = model

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_key = datetime.now().strftime("%Y-%m-%d")

    stats["last_call"] = {
        "time": now_str,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "response_tokens": resp_tokens,
        "total_tokens": total_tokens
    }

    # Thống kê theo model
    if "by_model" not in stats: stats["by_model"] = {}
    clean_m = model.replace("models/", "")
    if clean_m not in stats["by_model"]:
        stats["by_model"][clean_m] = {"requests": 0, "tokens": 0}
    stats["by_model"][clean_m]["requests"] += 1
    stats["by_model"][clean_m]["tokens"] += total_tokens

    # Thống kê theo ngày
    if "by_date" not in stats: stats["by_date"] = {}
    if date_key not in stats["by_date"]:
        stats["by_date"][date_key] = {"requests": 0, "tokens": 0}
    stats["by_date"][date_key]["requests"] += 1
    stats["by_date"][date_key]["tokens"] += total_tokens

    save_token_stats(stats)
    return stats["last_call"]

def record_local_fast_path():
    """Ghi nhận lượt xử lý tức thì của AI Nội Bộ (tiết kiệm 100% token)"""
    stats = load_token_stats()
    stats["saved_local_requests"] = stats.get("saved_local_requests", 0) + 1
    save_token_stats(stats)

def get_token_summary() -> dict:
    """Trả về tổng hợp tài nguyên & token hiện tại"""
    stats = load_token_stats()
    today_key = datetime.now().strftime("%Y-%m-%d")
    today_info = stats.get("by_date", {}).get(today_key, {"requests": 0, "tokens": 0})

    return {
        "total_tokens": stats.get("total_tokens", 0),
        "prompt_tokens": stats.get("prompt_tokens", 0),
        "response_tokens": stats.get("response_tokens", 0),
        "total_requests": stats.get("total_requests", 0),
        "saved_local_requests": stats.get("saved_local_requests", 0),
        "today_tokens": today_info.get("tokens", 0),
        "today_requests": today_info.get("requests", 0),
        "last_call": stats.get("last_call", {}),
        "by_model": stats.get("by_model", {})
    }

def reset_token_stats():
    """Làm mới lại bộ đếm token"""
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
        except Exception:
            pass
    return load_token_stats()
