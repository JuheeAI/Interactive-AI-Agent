import { useState, useRef } from 'react';
import axios from 'axios';

const BACKEND_URL = import.meta.env.VITE_API_BASE_URL; 
const WS_URL = BACKEND_URL.replace('http', 'ws');

function App() {
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState('');
  const [resultImage, setResultImage] = useState('');
  const promptInputRef = useRef(null);

  const handleImageChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImageFile(file);
      setImagePreview(URL.createObjectURL(file));
      setResultImage(''); 
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!imageFile || !promptInputRef.current.value) {
      alert("Please upload an image and enter a prompt.");
      return;
    }

    setIsLoading(true);
    setLogs(['작업을 요청합니다...']);
    setResultImage('');
    
    const formData = new FormData();
    formData.append('image', imageFile);
    formData.append('prompt', promptInputRef.current.value);

    try {
      const response = await axios.post(`${BACKEND_URL}/agent/invoke`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      
      const newJobId = response.data.job_id;
      setLogs(prev => [...prev, `Job ID [${newJobId}]를 받았습니다.`]);

      const wsUrl = `${WS_URL}/ws/${newJobId}`;
      const socket = new WebSocket(wsUrl);

      socket.onopen = () => setLogs(prev => [...prev, 'WebSocket 연결 성공!']);
      
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.status?.includes('완료')) {
          const finalResult = data.result;

          if (finalResult.result_type === 'image') {
            setResultImage(finalResult.data); // Base64 이미지 데이터 설정
            setLogs(prev => [...prev, "[✅ 이미지 결과 수신 완료]"]);
          } else {
            setLogs(prev => [...prev, `[✅ 최종 답변] ${finalResult.data}`]);
          }
          socket.close();
        } else {
          setLogs(prev => [...prev, `[서버 메시지] ${JSON.stringify(data)}`]);
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
      <h1>멀티모달 AI 에이전트</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label>1. 이미지 업로드:</label>
          <input type="file" accept="image/*" onChange={handleImageChange} disabled={isLoading} />
        </div>
        {imagePreview && <img src={imagePreview} alt="Preview" width="200" style={{ marginTop: '10px' }} />}
        
        <div style={{ marginTop: '10px' }}>
          <label>2. 요청사항 입력:</label>
          <input type="text" ref={promptInputRef} placeholder="예: 고양이 눈 색깔이 뭐야?" disabled={isLoading} style={{ width: '300px', marginLeft: '5px' }} />
        </div>
        
        <button type="submit" disabled={isLoading} style={{ marginTop: '10px' }}>
          {isLoading ? '에이전트 작업 중...' : '작업 실행'}
        </button>
      </form>
      <h3>실시간 로그:</h3>
      <pre style={{ border: '1px solid #ccc', padding: '10px', background: '#242424', color: 'white', minHeight: '200px' }}>
        {logs.join('\n')}
      </pre>

      {/* --- 결과 이미지를 표시할 영역 --- */}
      {resultImage && (
        <div style={{ marginTop: '20px' }}>
          <h3>결과 이미지:</h3>
          <img src={resultImage} alt="Agent Result" style={{ maxWidth: '400px', border: '1px solid #ccc' }} />
        </div>
      )}
    </div>
  );
}

export default App;