import { useState } from 'react';
import axios from 'axios';

// .env 파일의 환경 변수를 불러옵니다.
const BACKEND_URL = import.meta.env.VITE_API_BASE_URL;
const WS_URL = BACKEND_URL.replace('http', 'ws');

function App() {
  const [jobId, setJobId] = useState('');
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleStartTask = async () => {
    setIsLoading(true);
    setLogs(['작업을 요청합니다...']);
    
    try {
      // 1. 백엔드에 작업 요청
      const response = await axios.post(`${BACKEND_URL}/agent/invoke`);
      const newJobId = response.data.job_id;
      setJobId(newJobId);
      setLogs(prev => [...prev, `Job ID [${newJobId}]를 받았습니다.`]);

      // WebSocket URL
      const wsUrl = `${WS_URL}/ws/${newJobId}`;
      const socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        setLogs(prev => [...prev, 'WebSocket 연결 성공!']);
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setLogs(prev => [...prev, `[서버 메시지] ${JSON.stringify(data)}`]);
        if (data.status?.includes('완료')) {
          socket.close();
        }
      };

      socket.onclose = () => {
        setLogs(prev => [...prev, 'WebSocket 연결 종료.']);
        setIsLoading(false);
      };

      socket.onerror = (error) => {
        setLogs(prev => [...prev, `[에러] WebSocket 오류가 발생했습니다.`]);
        console.error("WebSocket Error:", error);
        setIsLoading(false);
      };

    } catch (error) {
      setLogs(prev => [...prev, `[에러] 백엔드 API 호출에 실패했습니다: ${error.message}`]);
      console.error("API Error:", error);
      setIsLoading(false);
    }
  };

  return (
    <div>
      <h1>백엔드 비동기 시스템 테스트</h1>
      <button onClick={handleStartTask} disabled={isLoading}>
        {isLoading ? '작업 중...' : '10초짜리 가짜 AI 작업 시작'}
      </button>
      <h3>실시간 로그:</h3>
      <pre style={{ border: '1px solid #ccc', padding: '10px', background: '#242424' }}>
        {logs.join('\n')}
      </pre>
    </div>
  );
}

export default App;