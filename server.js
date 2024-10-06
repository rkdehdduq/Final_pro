// server.js
const express = require('express');
const bodyParser = require('body-parser');
const { GoogleGenerativeAI } = require("@google/generative-ai");

// Express 애플리케이션 생성
const app = express();
const PORT = 3000;

// 미들웨어 설정
app.use(bodyParser.json());
app.use(express.static('public')); // 정적 파일 제공 (index.html이 포함된 폴더)

// API 키 환경 변수 설정
const genAI = new GoogleGenerativeAI(process.env.API_KEY);

// 클라이언트에서 요청을 받는 엔드포인트
app.post('/chat', async (req, res) => {
    const userMessage = req.body.message;

    try {
        // Gemini 모델 설정
        const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

        const chat = model.startChat({
            history: [
                {
                    role: "user",
                    parts: [{ text: userMessage }],
                }
            ],
            generationConfig: {
                maxOutputTokens: 100,
            },
        });

        // API에 메시지 전송
        const result = await chat.sendMessage(userMessage);
        const response = await result.response;
        const text = response.text();

        // 클라이언트에 응답 반환
        res.json({ reply: text });
    } catch (error) {
        console.error('Error communicating with Gemini API:', error.message);
        res.status(500).json({ reply: 'An error occurred while contacting the API.' });
    }
});

// 서버 실행
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
