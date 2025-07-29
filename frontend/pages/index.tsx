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

export default function Home() {
  const [attendanceData, setAttendanceData] = useState<AttendanceData | null>(null)
  const [status, setStatus] = useState<Status | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

  // 滞在時間を計算する関数
  const calculateAttendanceTime = () => {
    if (!attendanceData?.data || attendanceData.data.length === 0) {
      return []
    }

    const logs = attendanceData.data
    const attendanceSessions: { date: string; hours: number[] }[] = []
    
    for (let i = 0; i < logs.length; i++) {
      const log = logs[i]
      
      if (log.action === 'enter') {
        const enterTime = new Date(log.timestamp)
        const nextLog = logs[i + 1]
        
        if (nextLog && nextLog.action === 'exit') {
          const exitTime = new Date(nextLog.timestamp)
          const date = enterTime.toISOString().split('T')[0]
          
          // 滞在時間を時間単位で計算
          const startHour = enterTime.getHours()
          const endHour = exitTime.getHours()
          
          let existingSession = attendanceSessions.find(s => s.date === date)
          if (!existingSession) {
            existingSession = { date, hours: Array(24).fill(0) }
            attendanceSessions.push(existingSession)
          }
          
          // 滞在した時間をマーク
          for (let hour = startHour; hour <= endHour; hour++) {
            existingSession.hours[hour] = 1
          }
        }
      }
    }
    
    return attendanceSessions.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()).slice(0, 30)
  }

  const attendanceSessions = calculateAttendanceTime()

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
                最終更新: {new Date(status.last_action_time).toLocaleString('ja-JP')}
              </span>
            )}
          </div>
        )}
      </header>

      <main className="main">
        <div className="attendance-grid">
          <div className="time-labels">
            {Array.from({ length: 24 }, (_, i) => (
              <div key={i} className="time-label">
                {i.toString().padStart(2, '0')}:00
              </div>
            ))}
          </div>
          
          <div className="attendance-chart">
            {attendanceSessions.map((session, dayIndex) => (
              <div key={session.date} className="day-row">
                <div className="date-label">
                  {new Date(session.date).toLocaleDateString('ja-JP', {
                    month: 'short',
                    day: 'numeric'
                  })}
                </div>
                <div className="hours-row">
                  {session.hours.map((present, hour) => (
                    <div
                      key={hour}
                      className={`hour-cell ${present ? 'present' : 'absent'}`}
                      title={`${session.date} ${hour}:00-${hour + 1}:00`}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {attendanceData && (
          <div className="stats">
            <p>過去30日間の記録: {attendanceData.count}件</p>
            <button onClick={fetchData} className="refresh-button">
              データを更新
            </button>
          </div>
        )}
      </main>
    </div>
  )
}