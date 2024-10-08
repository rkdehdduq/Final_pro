// login.js

// DOMContentLoaded 이벤트가 발생하면 스크립트가 실행됩니다.
document.addEventListener("DOMContentLoaded", function() {
    // 로그인 버튼을 선택합니다.
    const loginButton = document.getElementById("login-btn");

    // 로그인 버튼에 클릭 이벤트 리스너를 추가합니다.
    loginButton.addEventListener("click", function() {
        // 페이지를 index.html로 리다이렉트합니다.
        window.location.href = '/index'; // 서버의 '/index' 경로로 이동
    });
});
