// worker.js
onmessage = function (e) {
    let remainingText = e.data.remaining_text;
    let index = 0;
    let interval = setInterval(function () {
        if (index < remainingText.length) {
            postMessage({ type: 'text', content: remainingText.charAt(index) }); // 文字を1つずつ送る
            index++;
        } else {
            clearInterval(interval);
            postMessage({ type: 'done' }); // 文字生成が完了したら通知
        }
    }, 40); // 40ミリ秒ごとに1文字を送信
};
