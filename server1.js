// .env 파일에서 환경 변수 불러오기 위한 dotenv 모듈 불러옴
require('dotenv').config();
// 필요한 모듈 추가
const mongoose = require('mongoose'); // MongoDB 연결을 위한 mongoose 모듈 추가

// MongoDB 연결 설정
mongoose.connect(process.env.MONGODB_URI)
    .then(() => console.log('MongoDB 연결됨'))
    .catch(err => console.error('MongoDB 연결 오류', err));

// 사용자 스키마 정의
const userSchema = new mongoose.Schema({
    fullname: { type: String, required: true },
    email: { type: String, required: true, unique: true },
    username: { type: String, required: true, unique: true },
    password: { type: String, required: true },
});

// 사용자 모델 생성
const User = mongoose.model('User', userSchema);

// Express.js 프레임워크 불러옴
const express = require('express');
// JSON 요청 파싱할 body-parser 미들웨어 불러옴
const bodyParser = require('body-parser');
const OpenAI = require("openai"); // OpenAI SDK 불러옴
// readline 모듈 불러옴. 터미널 입력 처리용
const readline = require("readline");
// 경로 처리를 위한 path 모듈
const path = require('path'); 

// OpenAI API 초기화
const openai = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY,
});

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



// 클라이언트로부터 전송된 메시지를 처리하는 POST 경로 설정
app.post('/send-message', async (req, res) => {
    const userMessage = req.body.message; // 요청 본문에서 사용자 메시지 가져오기

    if (!userMessage) {
        return res.status(400).json({ error: '메시지는 비어 있을 수 없음' }); // 메시지가 비어있을 경우 오류 응답
    }

    try {
        // OpenAI API에 사용자 메시지 전송하고 응답 받음
        const response = await openai.chat.completions.create({
            model: "gpt-3.5-turbo", // 또는 "gpt-4" 등 원하는 모델 선택
            messages: [{ role: "user", content: userMessage }], // 사용자 메시지를 포함한 메시지 배열
        });

        const botReply = response.choices[0].message.content; // AI의 응답 텍스트 추출
        res.json({ reply: botReply }); // 챗봇의 응답을 JSON 형식으로 클라이언트에 전송
    } catch (error) {
        console.error('챗 API 요청 중 오류 발생', error); // 오류 발생 시 콘솔에 로그 출력
        res.status(500).json({ reply: '죄송함. 요청 처리 중 오류 발생' }); // 서버 오류 응답
    }
});



// 회원가입 API 추가
app.post('/api/signup', async (req, res) => {
    const { fullname, email, username, password } = req.body;

    // 입력값 확인
    if (!fullname || !email || !username || !password) {
        return res.status(400).json({ error: '모든 필드를 입력해야 합니다.' });
    }

    try {
        // 사용자 정보 저장
        const newUser = new User({ fullname, email, username, password });
        await newUser.save();
        res.status(201).json({ message: '사용자가 성공적으로 생성되었습니다.' });
    } catch (error) {
        console.error('사용자 생성 중 오류 발생', error);
        res.status(500).json({ error: '사용자를 생성하는 동안 오류가 발생했습니다.' });
    }
});

// 로그인 API 추가
app.post('/api/login', async (req, res) => {
    const { username, password } = req.body;

    // 입력값 확인
    if (!username || !password) {
        return res.status(400).json({ error: '사용자 이름과 비밀번호를 입력해야 합니다.' });
    }

    try {
        // 사용자 조회
        const user = await User.findOne({ username });
        if (!user) {
            return res.status(401).json({ error: '사용자 이름 또는 비밀번호가 잘못되었습니다.' });
        }

        // 비밀번호 확인 (비밀번호 암호화 사용 시 적절한 비교 방법 필요)
        if (user.password !== password) {
            return res.status(401).json({ error: '사용자 이름 또는 비밀번호가 잘못되었습니다.' });
        }

        // 로그인 성공
        res.json({ message: '로그인 성공' });
    } catch (error) {
        console.error('로그인 중 오류 발생', error);
        res.status(500).json({ error: '로그인 처리 중 오류가 발생했습니다.' });
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
    console.log(`서버가 http://localhost:${PORT} 에서 실행 중임`);
});

// 터미널에서 수동으로 입력 받기 위한 readline 인터페이스 설정
const rl = readline.createInterface({
    input: process.stdin, // 표준 입력 사용
    output: process.stdout // 표준 출력 사용
});


// // 터미널 입력 처리하는 이벤트 리스너
// rl.on("line", async function(line) {
//     // 입력된 줄이 비어있으면 readline 인터페이스 종료
//     if (!line) {
//         rl.close();
//         return;
//     }
//     // 입력된 줄 처리
//     await run(line);
// }).on("close", function() {
//     // readline 인터페이스 종료 시 프로세스 종료
//     process.exit();
// });
