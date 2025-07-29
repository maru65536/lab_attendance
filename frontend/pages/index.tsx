import { useState, useEffect, useRef } from 'react'
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
  const [currentTime, setCurrentTime] = useState(new Date())
  const [tooltip, setTooltip] = useState<{x: number, y: number, content: string, visible: boolean}>({
    x: 0, y: 0, content: '', visible: false
  })

  // UTC時間をJSTに変換する関数
  const toJST = (utcTimeString: string): Date => {
    // バックエンドから返される時刻をUTCとして解釈
    return new Date(utcTimeString + 'Z')
  }

  // 在室時間を計算する関数
  const calculateCurrentStayTime = (): string => {
    if (!status || status.current_status !== 'enter' || !status.last_action_time) {
      return ''
    }
    
    const enterTime = toJST(status.last_action_time)
    const diffMs = currentTime.getTime() - enterTime.getTime()
    const diffMinutes = Math.floor(diffMs / (1000 * 60))
    const hours = Math.floor(diffMinutes / 60)
    const minutes = diffMinutes % 60
    
    if (hours > 0) {
      return `在室時間: ${hours}時間${minutes}分`
    } else {
      return `在室時間: ${minutes}分`
    }
  }

  // ツールチップハンドラー
  const handleMouseEnter = (event: React.MouseEvent, content: string) => {
    const rect = event.currentTarget.getBoundingClientRect()
    setTooltip({
      x: rect.left + rect.width / 2,
      y: rect.top - 10,
      content,
      visible: true
    })
  }

  const handleMouseLeave = () => {
    setTooltip(prev => ({ ...prev, visible: false }))
  }

  // データを取得する関数
  const fetchData = async () => {
    try {
      const [attendanceResponse, statusResponse] = await Promise.all([
        axios.get('/lab_attendance/api/attendance-data?days=30'),
        axios.get('/lab_attendance/api/status')
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
    const dataInterval = setInterval(fetchData, 30000)
    
    // 1秒ごとに現在時刻を更新（在室時間のリアルタイム表示用）
    const timeInterval = setInterval(() => {
      setCurrentTime(new Date())
    }, 1000)
    
    return () => {
      clearInterval(dataInterval)
      clearInterval(timeInterval)
    }
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
          // 完了したセッション
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
        } else if (i === logs.length - 1 && status?.current_status === 'enter') {
          // 現在進行中のセッション（最後のenterで、現在在室中の場合）
          const date = enterTime.toISOString().split('T')[0]
          const duration = Math.round((currentTime.getTime() - enterTime.getTime()) / (1000 * 60))
          
          if (!sessionsByDate[date]) {
            sessionsByDate[date] = {
              date,
              sessions: [],
              totalMinutes: 0
            }
          }
          
          sessionsByDate[date].sessions.push({
            startTime: enterTime,
            endTime: currentTime, // 現在時刻を終了時刻として使用
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
            {status.current_status === 'enter' && (
              <span className="last-action">
                {calculateCurrentStayTime()}
              </span>
            )}
          </div>
        )}
      </header>

      <main className="main">
        <div className="chart-container">
          {/* 時間軸（縦軸） */}
          <div className="time-axis">
            {Array.from({ length: 25 }, (_, hour) => (
              <div key={hour} className="time-label">
                {hour === 24 ? '24:00' : `${hour.toString().padStart(2, '0')}:00`}
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
            
            {/* データグリッド - 連続バー表示 */}
            <div className="data-grid">
              {attendanceSessions.map((session) => (
                <div key={session.date} className="day-column">
                  <div className="time-bar">
                    {session.sessions.map((sessionData, index) => {
                      const startHour = sessionData.startTime.getHours() + sessionData.startTime.getMinutes() / 60
                      const endHour = sessionData.endTime.getHours() + sessionData.endTime.getMinutes() / 60
                      const height = ((endHour - startHour) / 24) * 100
                      const top = (startHour / 24) * 100
                      
                      // 進行中のセッションかどうかを判定
                      const isOngoing = status?.current_status === 'enter' && 
                                       Math.abs(sessionData.endTime.getTime() - currentTime.getTime()) < 5000 // 5秒以内なら進行中
                      
                      return (
                        <div
                          key={index}
                          className={`session-bar ${isOngoing ? 'ongoing' : ''}`}
                          style={{
                            position: 'absolute',
                            top: `${top}%`,
                            height: `${height}%`,
                            left: '0',
                            right: '0',
                          }}
                          onMouseEnter={(e) => handleMouseEnter(e, 
                            `${session.date}\n${sessionData.startTime.toLocaleTimeString('ja-JP', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })} - ${isOngoing ? '進行中' : sessionData.endTime.toLocaleTimeString('ja-JP', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}\n${isOngoing ? '現在の' : ''}滞在時間: ${Math.floor(sessionData.duration / 60)}時間${sessionData.duration % 60}分`
                          )}
                          onMouseLeave={handleMouseLeave}
                        />
                      )
                    })}
                  </div>
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

      {/* 固定ツールチップ */}
      {tooltip.visible && (
        <div
          className="fixed-tooltip"
          style={{
            position: 'fixed',
            left: `${tooltip.x}px`,
            top: `${tooltip.y}px`,
            transform: 'translateX(-50%)',
            background: '#1e293b',
            color: 'white',
            padding: '10px 14px',
            borderRadius: '8px',
            whiteSpace: 'pre-line',
            fontSize: '0.75rem',
            zIndex: 9999,
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            minWidth: '140px',
            textAlign: 'center',
            pointerEvents: 'none'
          }}
        >
          {tooltip.content}
          <div
            style={{
              position: 'absolute',
              top: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              borderLeft: '6px solid transparent',
              borderRight: '6px solid transparent',
              borderTop: '6px solid #1e293b'
            }}
          />
        </div>
      )}
    </div>
  )
}