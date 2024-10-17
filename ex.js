const express = require('express');
const bodyParser = require('body-parser');
const { spawn } = require('child_process');

const app = express();
const PORT = 3000;

app.use(bodyParser.json());

app.post('/send-message', async (req, res) => {
    const userMessage = "정보기술 펀드 추천해줘"; // 사용자 메시지를 직접 설정

    // 메시지가 비어 있는지 확인
    if (!userMessage) {
        return res.status(400).json({ error: '메시지는 비어 있을 수 없음' });
    }

    // Python 스크립트 실행
    const pythonProcess = spawn('python3', ['test1.py', userMessage]);

    // Python 스크립트의 stdout에서 데이터 수신
    pythonProcess.stdout.on('data', (data) => {
        const output = data.toString();
        console.log(`Python Output: ${output}`); // Python 스크립트의 출력을 콘솔에 출력

        try {
            const response = JSON.parse(output);
            res.json({ response: response.response });
        } catch (error) {
            console.error(`JSON 파싱 오류: ${error}`);
            res.status(500).send('응답을 처리하는 중 오류가 발생했습니다.');
        }
    });

    // 오류 처리
    pythonProcess.stderr.on('data', (data) => {
        console.error(`Error: ${data}`);
        res.status(500).send('요청 처리 중 오류가 발생했습니다.');
    });
});

app.listen(PORT, () => {
    console.log(`서버가 http://localhost:${PORT} 에서 실행 중입니다.`);
});
