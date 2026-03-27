import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [messages, setMessages] = useState([{ sender: 'AI', text: 'Hello, I am the triage nurse. How can I help you today?' }]);
  const [input, setInput] = useState('');
  const [summary, setSummary] = useState('');
  const [activePatients, setActivePatients] = useState([]);

  // Fetch all active patients from PostgreSQL whenever called
  const fetchActivePatients = async () => {
    try {
      const response = await axios.get('http://127.0.0.1:8000/active_sessions');
      setActivePatients(response.data.sessions);
    } catch(error) {
      console.error("Failed to fetch patients:", error);
    }
  };

  // Automatically load the waiting room on startup
  useEffect(() => {
    fetchActivePatients();
    
    // Auto-refresh the waiting room every 10 seconds!
    const interval = setInterval(() => {
        fetchActivePatients();
    }, 10000);
    return () => clearInterval(interval);
  }, []);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const newMessages = [...messages, { sender: 'User', text: input }];
    setMessages(newMessages);
    setInput('');

    try {
      const response = await axios.post('http://127.0.0.1:8000/chat/web', { text: input });
      setMessages([...newMessages, { sender: 'AI', text: response.data.response }]);
      // Refresh patient list to show the incoming conversation instantly
      fetchActivePatients();
    } catch (error) {
      console.error("Error sending message", error);
    }
  };

  const generateSummary = async (sessionId) => {
    try {
      setSummary("Generating summary for Session #" + sessionId + "...");
      const response = await axios.get(`http://127.0.0.1:8000/summary?session_id=${sessionId}`);
      setSummary(response.data.summary);
      
      // Generating the summary successfully marks the SQL session as INACTIVE! 
      // We must immediately update the list so the button vanishes from the waiting room.
      fetchActivePatients();
    } catch (error) {
      console.error("Error generating summary", error);
      setSummary("Failed to generate summary. Please check Rate Limits or Server Logs.");
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontFamily: 'Arial', height: '100vh', padding: '20px' }}>
      
      {/* LEFT SIDE: Web Patient Chat */}
      <div style={{ width: '45%' }}>
        <h2>📝 Triage Web Portal</h2>
        <div style={{ height: '500px', border: '1px solid #ccc', overflowY: 'scroll', padding: '10px', marginBottom: '10px', borderRadius: '10px' }}>
          {messages.map((msg, index) => (
            <div key={index} style={{ textAlign: msg.sender === 'User' ? 'right' : 'left', margin: '10px 0' }}>
              <span style={{ background: msg.sender === 'User' ? '#007bff' : '#f1f1f1', color: msg.sender === 'User' ? 'white' : 'black', padding: '10px', borderRadius: '10px', display: 'inline-block' }}>
                {msg.text}
              </span>
            </div>
          ))}
        </div>
        <input 
          type="text" 
          value={input} 
          onChange={(e) => setInput(e.target.value)} 
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          style={{ width: '70%', padding: '10px' }}
          placeholder="Type your symptoms..."
        />
        <button onClick={sendMessage} style={{ width: '20%', padding: '10px', marginLeft: '5px' }}>Send</button>
      </div>

      {/* RIGHT SIDE: Doctor Live Dashboard */}
      <div style={{ width: '45%', borderLeft: '2px dashed #ccc', paddingLeft: '30px' }}>
        <h2 style={{ color: '#d9534f' }}>🩺 Live Doctor Dashboard</h2>
        <button onClick={fetchActivePatients} style={{ padding: '8px', background: '#17a2b8', color: 'white', border: 'none', cursor: 'pointer', marginBottom: '20px', borderRadius: '5px' }}>
          ↻ Refresh Waiting Room
        </button>
        
        <h4>Patients waiting for Triage Review:</h4>
        {activePatients.length === 0 ? (
          <p><i>No active patients in the queue right now.</i></p>
        ) : (
          <ul style={{ listStyleType: 'none', padding: 0 }}>
            {activePatients.map(patient => (
              <li key={patient.session_id} style={{ background: '#f8f9fa', margin: '10px 0', padding: '15px', border: '1px solid #ddd', borderRadius: '8px' }}>
                <strong>Session ID:</strong> #{patient.session_id} <br/>
                <strong>Phone Source:</strong> {patient.phone_number} <br/>
                <strong>Started At:</strong> {new Date(patient.created_at).toLocaleTimeString()} <br/>
                <button 
                  onClick={() => generateSummary(patient.session_id)} 
                  style={{ marginTop: '15px', padding: '10px', background: '#28a745', color: 'white', border: 'none', cursor: 'pointer', borderRadius: '5px', width: '100%' }}
                >
                  Generate Medical Summary
                </button>
              </li>
            ))}
          </ul>
        )}
        
        {/* Output Panel for the Latest Generated Report */}
        {summary && (
          <div style={{ marginTop: '30px', padding: '20px', background: '#fff3cd', border: '1px solid #ffeeba', whiteSpace: 'pre-wrap', borderRadius: '10px' }}>
            <strong style={{ fontSize: '1.2em' }}>Final Medical Report:</strong><br/><br/>
            {summary}
          </div>
        )}
      </div>

    </div>
  );
}

export default App;