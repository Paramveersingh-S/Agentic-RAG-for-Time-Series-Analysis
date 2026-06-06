import { useState } from 'react'
import axios from 'axios'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts'
import './App.css'

function App() {
  const [messages, setMessages] = useState([
    { role: 'ai', content: 'Hello! I am your Agentic RAG Time-Series Assistant powered by Gemini. Ask me about historical metrics, future forecasts, or why an anomaly occurred!' }
  ])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [chartData, setChartData] = useState([])
  const [forecastData, setForecastData] = useState(null)

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage = { role: 'user', content: input }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      // Using relative path so Vite proxy handles the connection inside the Codespace
      const response = await axios.post('/api/chat', { query: input })
      
      const { answer, chart_data, forecast_data } = response.data
      
      setMessages(prev => [...prev, { role: 'ai', content: answer }])
      
      if (chart_data && chart_data.length > 0) {
        // Reverse so chronological order is left to right
        setChartData([...chart_data].reverse())
      }
      
      if (forecast_data) {
        setForecastData(forecast_data)
      }

    } catch (error) {
      console.error(error)
      setMessages(prev => [...prev, { role: 'ai', content: 'Sorry, I encountered an error communicating with the backend agents.' }])
    } finally {
      setIsLoading(false)
    }
  }

  // Combine historical and forecast data for the chart if both exist
  const renderChart = () => {
    if (chartData.length === 0 && !forecastData) {
      return <div className="placeholder-viz">Submit a query to visualize data</div>
    }

    let combinedData = [...chartData]
    
    // Simple logic to append forecast points if they exist
    if (forecastData && forecastData.predictions) {
      forecastData.predictions.forEach((pred, idx) => {
        combinedData.push({
          metric_hour: `Forecast +${idx + 1}`,
          forecast_value: pred
        })
      })
    }

    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={combinedData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis 
            dataKey="metric_hour" 
            stroke="#94a3b8" 
            tickFormatter={(tick) => {
              if(tick.startsWith('Forecast')) return tick;
              const d = new Date(tick);
              return isNaN(d) ? tick : `${d.getMonth()+1}/${d.getDate()}`;
            }}
          />
          <YAxis stroke="#94a3b8" />
          <Tooltip 
            contentStyle={{ backgroundColor: '#141a26', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
            itemStyle={{ color: '#f8fafc' }}
          />
          <Legend />
          <Line 
            type="monotone" 
            name="Historical Value"
            dataKey="target_value" 
            stroke="#3b82f6" 
            strokeWidth={3}
            dot={{ r: 4, fill: '#3b82f6' }}
            activeDot={{ r: 6 }} 
          />
          <Line 
            type="monotone" 
            name="Forecast Prediction"
            dataKey="forecast_value" 
            stroke="#8b5cf6" 
            strokeWidth={3}
            strokeDasharray="5 5"
            dot={{ r: 4, fill: '#8b5cf6' }}
            activeDot={{ r: 6 }} 
          />
        </LineChart>
      </ResponsiveContainer>
    )
  }

  return (
    <div className="app-container">
      
      {/* Left Chat Panel */}
      <div className="glass-panel chat-section">
        <div className="header">
          <h1>Time-Series RAG</h1>
          <p>Powered by Gemini & LangGraph</p>
        </div>

        <div className="chat-history">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              {msg.content}
            </div>
          ))}
          {isLoading && (
            <div className="message ai" style={{ opacity: 0.7 }}>
              Agents are analyzing...
            </div>
          )}
        </div>

        <div className="input-container">
          <input 
            type="text" 
            className="chat-input"
            placeholder="Ask about your data..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          />
          <button 
            className="send-btn" 
            onClick={handleSend} 
            disabled={isLoading || !input.trim()}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
      </div>

      {/* Right Visualization Panel */}
      <div className="glass-panel viz-section">
        <div className="chart-container">
          <div className="chart-title">
            <svg className="chart-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
            </svg>
            Live Visualization Hub
          </div>
          {renderChart()}
        </div>
      </div>

    </div>
  )
}

export default App
