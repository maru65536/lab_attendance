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
    const diffMinutes = safeFloor(diffMs / (1000 * 60))
    const hours = safeFloor(diffMinutes / 60)
    const minutes = diffMinutes % 60
    
    if (hours > 0) {
      return `在室時間: ${hours}時間${minutes}分`
    } else {
      return `在室時間: ${minutes}分`
    }
  }

  // 安全な時刻フォーマット関数
  const formatTime = (date: Date): string => {
    try {
      return date.toLocaleTimeString('ja-JP', {
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch (error) {
      // フォールバック - padStartを使わない
      const hours = date.getHours()
      const minutes = date.getMinutes()
      return `${hours < 10 ? '0' : ''}${hours}:${minutes < 10 ? '0' : ''}${minutes}`
    }
  }

  // 安全なMath.floor関数
  const safeFloor = (num: number): number => {
    try {
      return Math.floor(num)
    } catch (error) {
      return parseInt(num.toString().split('.')[0], 10) || 0
    }
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
          const duration = safeFloor((exitTime.getTime() - enterTime.getTime()) / (1000 * 60) + 0.5)
          
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
          const duration = safeFloor((currentTime.getTime() - enterTime.getTime()) / (1000 * 60) + 0.5)
          
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
    
    // 過去30日分のデータを生成（データがない日も含む、新しい日が先頭）
    const sessions: AttendanceSession[] = []
    for (let i = 0; i < 30; i++) {
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
                最終更新: {(() => {
                  try {
                    return toJST(status.last_action_time).toLocaleString('ja-JP')
                  } catch (error) {
                    const date = toJST(status.last_action_time)
                    return `${date.getFullYear()}/${(date.getMonth() + 1).toString().padStart(2, '0')}/${date.getDate().toString().padStart(2, '0')} ${formatTime(date)}`
                  }
                })()}
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
          {/* 日付軸（縦軸） */}
          <div className="date-axis-vertical">
            {attendanceSessions.map((session) => (
              <div key={session.date} className="date-label-vertical">
                <div className="date-text">
                  {(() => {
                    try {
                      return new Date(session.date).toLocaleDateString('ja-JP', {
                        month: 'short',
                        day: 'numeric'
                      })
                    } catch (error) {
                      const date = new Date(session.date)
                      return `${date.getMonth() + 1}/${date.getDate()}`
                    }
                  })()}
                </div>
                <div className="total-time">
                  {safeFloor(session.totalMinutes / 60)}h{session.totalMinutes % 60}m
                </div>
              </div>
            ))}
          </div>
          
          {/* メインチャート */}
          <div className="chart-main">
            {/* 時間軸（横軸） */}
            <div className="time-axis-horizontal">
              {Array.from({ length: 25 }, (_, hour) => (
                <div key={hour} className="time-label-horizontal">
                  {hour === 24 ? '24' : hour.toString()}
                </div>
              ))}
            </div>
            
            {/* データグリッド - 横バー表示 */}
            <div className="data-grid-horizontal">
              {attendanceSessions.map((session) => (
                <div key={session.date} className="day-row">
                  <div className="time-bar-horizontal">
                    {session.sessions.map((sessionData, index) => {
                      const startHour = sessionData.startTime.getHours() + sessionData.startTime.getMinutes() / 60
                      const endHour = sessionData.endTime.getHours() + sessionData.endTime.getMinutes() / 60
                      const width = ((endHour - startHour) / 24) * 100
                      const left = (startHour / 24) * 100
                      
                      // 進行中のセッションかどうかを判定
                      const isOngoing = status?.current_status === 'enter' && 
                                       Math.abs(sessionData.endTime.getTime() - currentTime.getTime()) < 5000 // 5秒以内なら進行中
                      
                      return (
                        <div
                          key={index}
                          className={`session-bar ${isOngoing ? 'ongoing' : ''}`}
                          style={{
                            position: 'absolute',
                            left: `${left}%`,
                            width: `${width}%`,
                            top: '0',
                            bottom: '0',
                          }}
                          title={`${session.date}\n${formatTime(sessionData.startTime)} - ${isOngoing ? '進行中' : formatTime(sessionData.endTime)}\n${isOngoing ? '現在の' : ''}滞在時間: ${safeFloor(sessionData.duration / 60)}時間${sessionData.duration % 60}分`}
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
            <p>総滞在時間: {safeFloor(attendanceSessions.reduce((sum, s) => sum + s.totalMinutes, 0) / 60)}時間</p>
            <p className="auto-update-info">30秒ごとに自動更新</p>
          </div>
        )}
      </main>

    </div>
  )
}