const PROXY = "https://cors-anywhere.herokuapp.com/"; // CORS 문제 떄문에 프록시 서버를 통한 iframe 구현. 사이트 들어가서 버튼 클릭해야 서버 실행

// 본문에서 해당 문자열 찾기
function escapeRegExp(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); // 해당 매치된 문자열 찾기
}

// 지정된 문자열을 하이라이트하고, 링크화 시키기.
function highlightAndLinkWords(words, urls) {
    let bodyText = document.body.innerHTML; // 웹 페이지의 본문 내용을 문자열로 가져오기
    words.forEach((word, index) => {
        const escapedWord = escapeRegExp(word); // 정규 표현식
        const url = urls[index % urls.length]; // 배열에서 현재 단어의 인덱스에 해당하는 URL 가져오기
        const className = `highlight-${index + 1}`; // 각 단어에 대해 다른 클래스 이름 생성
        const proxyUrl = `${PROXY}${url.replace(/^https?:\/\//, '')}`; // 프록시 URL 생성, 중복 슬래시 제거

        const linkedText = bodyText.replace(new RegExp(`(${escapedWord})(?![^<]*>)`, 'gi'), `<a href="${url}" target="_blank" class="${className}" data-preview="${proxyUrl}">$1</a>`); // 일치하는 단어 검색
        bodyText = linkedText; // 다음 단어도 같은 방법으로 처리
    });
    document.body.innerHTML = bodyText; // 수정한 부분을 웹 페이지에 반영
}

// 서버에 연결되지 않아 JSON 데이터를 직접 입력
const data = {
    "news": {
        "link1": [
            "https://n.news.naver.com/mnews/article/081/0003454354?sid=102"
        ],
        "link2": [
            "https://n.news.naver.com/mnews/article/029/0002868915?sid=101"
        ],
        "link3": [
            "https://n.news.naver.com/mnews/article/022/0003932721?sid=100"
        ]
    },
    "summary": {
        "sentence1": "정부여당을 향해 “차등 지원도 수용하겠다”며 이른 시일 내 협의하자고 제안한 것이다.",
        "sentence2": "더불어민주당 이재명 대표가 민생회복지원금과 관련해 고수해오던 ‘보편 지원’ 주장을 내려놨다.",
        "sentence3": "하지만 여당은 ‘차등 지원’을 전제로 하더라도 여전히 민생회복지원금 자체에 부정적인 모습이다."
    }
};


const wordsToHighlight = Object.values(data.summary);
const urlsToLink = Object.values(data.news).flat();

highlightAndLinkWords(wordsToHighlight, urlsToLink);
addLinkPreviewEvents();

// 링크 미리보기 창 생성
function createPreviewElement() {
    const preview = document.createElement('div');
    preview.id = 'link-preview';
    preview.style.display = 'none';
    document.body.appendChild(preview);
}

// 미리보기 상태창 구현
function showPreview(event) {
    const preview = document.getElementById('link-preview');
    const url = event.target.getAttribute('data-preview');
    if (url) {
        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'Origin': window.location.origin
            }
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.text();
            })
            .then(data => {
                const blob = new Blob([data], { type: 'text/html' });
                const previewUrl = URL.createObjectURL(blob);
                preview.innerHTML = `<iframe src="${previewUrl}" style="width:100%;height:100%;" sandbox="allow-same-origin"></iframe>`;
                preview.style.display = 'block';
                preview.style.top = `${event.pageY + 10}px`;
                preview.style.left = `${event.pageX + 10}px`;
            })
            .catch(error => {
                console.error(`Error fetching preview: ${error}`);
                preview.innerHTML = `<p>Error loading preview</p>`;
                preview.style.display = 'block';
                preview.style.top = `${event.pageY + 10}px`;
                preview.style.left = `${event.pageX + 10}px`;
            });
    }
}

// 마우스를 내리면 미리보기 사라짐
function hidePreview() {
    const preview = document.getElementById('link-preview');
    preview.style.display = 'none';
}

// 링크 요소에 이벤트 리스너 추가
function addLinkPreviewEvents() {
    const links = document.querySelectorAll('a[data-preview]');
    links.forEach(link => {
        link.addEventListener('mouseenter', showPreview);
        link.addEventListener('mouseleave', hidePreview);
    });
}

createPreviewElement();
addLinkPreviewEvents();


// 버튼 클릭이 아닌 네이버 뉴스에서 자동으로 나오게 하려면
/* DOM 변화 감지
let timeout;
const observer = new MutationObserver(() => {
    if (timeout) {
        clearTimeout(timeout);
    }
    timeout =    setTimeout(() => {
        highlightAndLinkWords(wordsToHighlight, urlsToLink);
        addLinkPreviewEvents();
    }, 300); // 응답없음을 해결하기 위한 딜레이
});

// <body> 태그 변화 감지
observer.observe(document.body, { childList: true, subtree: true });
*/
