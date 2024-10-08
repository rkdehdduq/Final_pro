// Express.js 프레임워크 불러옴
const express = require('express');
// JSON 요청 파싱할 body-parser 미들웨어 불러옴
const bodyParser = require('body-parser');
// Google Generative AI SDK 불러옴
const { GoogleGenerativeAI } = require("@google/generative-ai");
// readline 모듈 불러옴. 터미널 입력 처리용
const readline = require("readline");
// .env 파일에서 환경 변수 불러오기 위한 dotenv 모듈 불러옴
require('dotenv').config();
// 경로 처리를 위한 path 모듈
const path = require('path'); 


// Express 애플리케이션 생성
const app = express();
// 사용할 포트 설정. 환경 변수 PORT가 없으면 기본적으로 3000 사용
const PORT = process.env.PORT || 3000;

// JSON 요청 파싱하는 미들웨어 설정
app.use(bodyParser.json());

// 정적 파일 제공할 미들웨어 설정. 'public' 폴더의 파일 제공
app.use(express.static(path.join(__dirname, 'public')));
// 루트 경로로 요청이 왔을 때 login.html 제공
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', '1_login.html'));
});
// '/index' 경로로 접속하면 index.html 제공
app.get('/index', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', '2_index.html'));
});
// Google Generative AI 초기화
const genAI = new GoogleGenerativeAI(process.env.OPENAI_API_KEY); // API 키로 Generative AI 인스턴스 생성
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" }); // 사용할 AI 모델 설정
const chat = model.startChat(); // 채팅 세션 시작

// 클라이언트로부터 전송된 메시지를 처리하는 POST 경로 설정
app.post('/send-message', async (req, res) => {
    const userMessage = req.body.message; // 클라이언트에서 보낸 메시지 추출

    // 메시지가 비어있는지 확인. 비어있으면 400 오류 응답
    if (!userMessage) {
        return res.status(400).json({ error: '메시지는 비어 있을 수 없음' });
    }

    try {
        // AI에게 사용자 메시지 전송하고 응답 받음
        const result = await chat.sendMessage(userMessage);
        const botReply = result.response.text(); // AI의 응답 텍스트 추출

        // 봇의 응답을 클라이언트에 JSON 형식으로 전달
        res.json({ reply: botReply });
    } catch (error) {
        // API 요청 중 오류 발생 시 콘솔에 에러 출력 및 500 오류 응답
        console.error('챗 API 요청 중 오류 발생', error);
        res.status(500).json({ reply: '죄송함. 요청 처리 중 오류 발생' });
    }
});

// 서버 시작. 설정된 포트에서 실행
app.listen(PORT, (err) => {
    if (err) {
        // 서버 시작 중 오류 발생 시 콘솔에 에러 출력 후 프로세스 종료
        console.error('서버 시작 중 오류 발생', err);
        process.exit(1);
    }
    // 서버가 정상적으로 실행 중일 때 콘솔에 메시지 출력
    console.log(`서버가 http://localhost:${PORT}에서 실행 중임`);
});

// 터미널에서 수동으로 입력 받기 위한 readline 인터페이스 설정
const rl = readline.createInterface({
    input: process.stdin, // 표준 입력 사용
    output: process.stdout // 표준 출력 사용
});

// 사용자 입력 처리하는 함수
async function run(line = '') {
    // 입력된 줄을 AI에게 전송하고 응답 받음
    const result = await chat.sendMessage(line);
    const response = result.response; // AI의 응답 가져옴
    const text = response.text(); // 응답 텍스트 추출
    // AI의 응답을 터미널에 출력
    process.stdout.write('GEMINI : ' + text + '\n');
}

// 터미널 입력 처리하는 이벤트 리스너
rl.on("line", async function(line) {
    // 입력된 줄이 비어있으면 readline 인터페이스 종료
    if (!line) {
        rl.close();
        return;
    }
    // 입력된 줄 처리
    run(line);
}).on("close", function() {
    // readline 인터페이스 종료 시 프로세스 종료
    process.exit();
});
