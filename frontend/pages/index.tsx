import { useState, useEffect } from 'react'
import axios from 'axios'

interface AttendanceLog {
  id: number
  action: string
  timestamp: string
}

interface AttendanceData {
  data: AttendanceLog[]
  count: number
  days: number
}

interface Status {
  current_status: string
  last_action_time: string | null
}

interface AttendanceSession {
  date: string
  sessions: {
    startTime: Date
    endTime: Date
    duration: number // 分単位
  }[]
  totalMinutes: number
}

export default function Home() {
  const [attendanceData, setAttendanceData] = useState<AttendanceData | null>(null)
  const [status, setStatus] = useState<Status | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // JST時間に変換する関数
  const toJST = (utcTimeString: string): Date => {
    const utcDate = new Date(utcTimeString + 'Z') // UTCとして解釈
    return new Date(utcDate.getTime() + 9 * 60 * 60 * 1000) // JST = UTC+9
  }

  // データを取得する関数
  const fetchData = async () => {
    try {
      const [attendanceResponse, statusResponse] = await Promise.all([
        axios.get('/api/attendance-data?days=30'),
        axios.get('/api/status')
      ])
      
      setAttendanceData(attendanceResponse.data)
      setStatus(statusResponse.data)
      setError(null)
    } catch (err) {
      console.error('データの取得に失敗しました:', err)
      setError('データの取得に失敗しました')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    
    // 30秒ごとにデータを更新
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  // 滞在セッションを計算する関数
  const calculateAttendanceSessions = (): AttendanceSession[] => {
    if (!attendanceData?.data || attendanceData.data.length === 0) {
      return []
    }

    const logs = attendanceData.data
    const sessionsByDate: { [date: string]: AttendanceSession } = {}
    
    for (let i = 0; i < logs.length; i++) {
      const log = logs[i]
      
      if (log.action === 'enter') {
        const enterTime = toJST(log.timestamp)
        const nextLog = logs[i + 1]
        
        if (nextLog && nextLog.action === 'exit') {
          const exitTime = toJST(nextLog.timestamp)
          const date = enterTime.toISOString().split('T')[0]
          const duration = Math.round((exitTime.getTime() - enterTime.getTime()) / (1000 * 60))
          
          if (!sessionsByDate[date]) {
            sessionsByDate[date] = {
              date,
              sessions: [],
              totalMinutes: 0
            }
          }
          
          sessionsByDate[date].sessions.push({
            startTime: enterTime,
            endTime: exitTime,
            duration
          })
          sessionsByDate[date].totalMinutes += duration
        }
      }
    }
    
    // 過去30日分のデータを生成（データがない日も含む）
    const sessions: AttendanceSession[] = []
    for (let i = 29; i >= 0; i--) {
      const date = new Date()
      date.setDate(date.getDate() - i)
      const dateStr = date.toISOString().split('T')[0]
      
      sessions.push(sessionsByDate[dateStr] || {
        date: dateStr,
        sessions: [],
        totalMinutes: 0
      })
    }
    
    return sessions
  }

  // 時間範囲でのセッション情報を取得
  const getSessionAtTime = (session: AttendanceSession, hour: number, minute: number): {
    isActive: boolean
    sessionInfo?: {
      startTime: Date
      endTime: Date
      duration: number
    }
  } => {
    const targetTime = new Date(session.date + `T${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}:00`)
    
    for (const sessionData of session.sessions) {
      if (targetTime >= sessionData.startTime && targetTime <= sessionData.endTime) {
        return {
          isActive: true,
          sessionInfo: sessionData
        }
      }
    }
    
    return { isActive: false }
  }

  const attendanceSessions = calculateAttendanceSessions()

  if (loading) {
    return (
      <div className="container">
        <div className="loading">データを読み込み中...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="container">
        <div className="error">{error}</div>
        <button onClick={fetchData} className="retry-button">
          再試行
        </button>
      </div>
    )
  }

  return (
    <div className="container">
      <header className="header">
        <h1>研究室滞在時間</h1>
        {status && (
          <div className="status">
            <span className={`status-indicator ${status.current_status}`}>
              {status.current_status === 'enter' ? '在室中' : 
               status.current_status === 'exit' ? '不在' : '不明'}
            </span>
            {status.last_action_time && (
              <span className="last-action">
                最終更新: {toJST(status.last_action_time).toLocaleString('ja-JP')}
              </span>
            )}
          </div>
        )}
      </header>

      <main className="main">
        <div className="chart-container">
          {/* 時間軸（縦軸） */}
          <div className="time-axis">
            {Array.from({ length: 24 }, (_, hour) => (
              <div key={hour} className="time-label">
                {hour.toString().padStart(2, '0')}:00
              </div>
            ))}
          </div>
          
          {/* メインチャート */}
          <div className="chart-main">
            {/* 日付軸（横軸） */}
            <div className="date-axis">
              {attendanceSessions.map((session) => (
                <div key={session.date} className="date-label">
                  {new Date(session.date).toLocaleDateString('ja-JP', {
                    month: 'short',
                    day: 'numeric'
                  })}
                  <div className="total-time">
                    {Math.floor(session.totalMinutes / 60)}h{session.totalMinutes % 60}m
                  </div>
                </div>
              ))}
            </div>
            
            {/* データグリッド */}
            <div className="data-grid">
              {Array.from({ length: 24 }, (_, hour) => (
                <div key={hour} className="hour-row">
                  {attendanceSessions.map((session) => {
                    const sessionInfo = getSessionAtTime(session, hour, 0)
                    return (
                      <div
                        key={`${session.date}-${hour}`}
                        className={`time-cell ${sessionInfo.isActive ? 'active' : 'inactive'}`}
                        title={
                          sessionInfo.isActive && sessionInfo.sessionInfo
                            ? `${session.date} ${hour}:00 - 在室中\n${sessionInfo.sessionInfo.startTime.toLocaleTimeString('ja-JP')} - ${sessionInfo.sessionInfo.endTime.toLocaleTimeString('ja-JP')}\n滞在時間: ${Math.floor(sessionInfo.sessionInfo.duration / 60)}時間${sessionInfo.sessionInfo.duration % 60}分`
                            : `${session.date} ${hour}:00 - 不在`
                        }
                      />
                    )
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>

        {attendanceData && (
          <div className="stats">
            <p>過去30日間の入退室記録: {attendanceData.count}件</p>
            <p>総滞在時間: {Math.floor(attendanceSessions.reduce((sum, s) => sum + s.totalMinutes, 0) / 60)}時間</p>
            <button onClick={fetchData} className="refresh-button">
              最新データに更新
            </button>
          </div>
        )}
      </main>
    </div>
  )
}