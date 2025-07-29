from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import datetime
from typing import List, Dict, Any
import os

app = FastAPI(
    title="Lab Attendance API",
    description="研究室滞在時間記録システム",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番では適切なドメインに制限
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベースファイルのパス
DB_PATH = os.path.join(os.path.dirname(__file__), "attendance.db")

# データベース初期化
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL CHECK (action IN ('enter', 'exit')),
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# 起動時にデータベース初期化
init_db()

# リクエストモデル
class AttendanceEntry(BaseModel):
    action: str

class AttendanceLog(BaseModel):
    id: int
    action: str
    timestamp: str

# 最後のアクションを取得する関数
def get_last_action():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT action FROM attendance_logs ORDER BY timestamp DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# ヘルスチェック
@app.get("/")
async def health_check():
    return {
        "status": "ok", 
        "message": "Lab Attendance API is running",
        "version": "1.0.0"
    }

# 入退室記録エンドポイント（POST）
@app.post("/api/lab-entry")
async def lab_entry_post(entry: AttendanceEntry):
    if entry.action not in ["enter", "exit"]:
        raise HTTPException(status_code=400, detail="Action must be 'enter' or 'exit'")
    
    # 重複チェック
    last_action = get_last_action()
    if last_action == entry.action:
        return {
            "status": "ignored", 
            "message": f"Duplicate {entry.action} action ignored", 
            "action": entry.action
        }
    
    # データベースに記録
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO attendance_logs (action) VALUES (?)", (entry.action,))
    conn.commit()
    conn.close()
    
    return {
        "status": "success", 
        "message": f"Successfully recorded {entry.action}", 
        "action": entry.action
    }

# 入退室記録エンドポイント（GET）
@app.get("/api/lab-entry")
async def lab_entry_get(action: str):
    if action not in ["enter", "exit"]:
        raise HTTPException(status_code=400, detail="Action must be 'enter' or 'exit'")
    
    # 重複チェック
    last_action = get_last_action()
    if last_action == action:
        return {
            "status": "ignored", 
            "message": f"Duplicate {action} action ignored", 
            "action": action
        }
    
    # データベースに記録
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO attendance_logs (action) VALUES (?)", (action,))
    conn.commit()
    conn.close()
    
    return {
        "status": "success", 
        "message": f"Successfully recorded {action}", 
        "action": action
    }

# データ取得用エンドポイント（フロントエンド用）
@app.get("/api/attendance-data")
async def get_attendance_data(days: int = 30):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 指定日数分のデータを取得
    cursor.execute("""
        SELECT id, action, timestamp 
        FROM attendance_logs 
        WHERE timestamp >= datetime('now', '-{} days')
        ORDER BY timestamp ASC
    """.format(days))
    
    rows = cursor.fetchall()
    conn.close()
    
    # データを整形
    attendance_data = []
    for row in rows:
        attendance_data.append({
            "id": row[0],
            "action": row[1],
            "timestamp": row[2]
        })
    
    return {
        "data": attendance_data, 
        "count": len(attendance_data),
        "days": days
    }

# 最新のステータス取得
@app.get("/api/status")
async def get_status():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT action, timestamp 
        FROM attendance_logs 
        ORDER BY timestamp DESC 
        LIMIT 1
    """)
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {
            "current_status": result[0],
            "last_action_time": result[1]
        }
    else:
        return {
            "current_status": "unknown",
            "last_action_time": None
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)