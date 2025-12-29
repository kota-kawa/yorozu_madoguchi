let autoScroll = true;

        // チャットがスクロールされたら、自動スクロールをオフにする
        document.getElementById('chatMessages1').addEventListener('scroll', function () {
            const chatMessages = document.getElementById('chatMessages1');
            const isAtBottom = chatMessages.scrollTop + chatMessages.clientHeight >= chatMessages.scrollHeight - 10;

            if (!isAtBottom) {
                autoScroll = false;
            }
        });


        document.getElementById('chat-form').addEventListener('submit', function (event) {
            event.preventDefault(); // フォームのデフォルトの送信動作を防ぐ
            const messageInput = document.getElementById('message');
            const chatMessages = document.getElementById('chatMessages1');
            const currentPlanContainer = document.getElementById('chatMessages2');

            if (messageInput.value.trim() !== '') {
                if (messageInput.value.length > 3000) {
                    alert("入力された文字数が3000文字を超えています。3000文字以内で入力してください。");
                    return;
                }
                const userMessage = document.createElement('div');
                userMessage.classList.add('chat-message', 'user');
                userMessage.innerText = messageInput.value;
                chatMessages.appendChild(userMessage);

                setTimeout(function () {
                    const botMessage = document.createElement('div');
                    botMessage.classList.add('chat-message', 'bot');
                    botMessage.innerHTML = `
                    <div class="spinner-grow text-info" id="spiner" role="status">
                    <span class="visually-hidden">Loading...</span>
                    </div>`
                    chatMessages.appendChild(botMessage);
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                    // 自動でスクロールされるようにする
                    autoScroll = true;

                }, 100); // 1000ミリ秒（1秒）後に実行


                // タイムアウトを設定（1分）
                const timeoutId = setTimeout(function () {
                    alert("サーバーからの応答がありません。もう一度お試しください。");
                }, 60000); // 60000ミリ秒（1分）

                let worker;
                // メッセージをサーバーに送信
                fetch('/reply_send_message', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: messageInput.value })
                })
                    .then(response => response.json())
                    .then(data => {
                        clearTimeout(timeoutId); // 応答があった場合、タイムアウトをクリア

                        if (data.remaining_text != 'Empty') {
                            console.log("本来はnullの時には表示されない", data.remaining_text);
                            var spinnerElement = document.getElementById("spiner");
                            if (spinnerElement) {
                                var botMessage = spinnerElement.parentElement;
                                spinnerElement.remove();
                                botMessage.innerText = ''; // テキストを一旦クリア

                                // Web Workerの作成と処理開始
                                if (typeof (Worker) !== "undefined") {
                                    if (worker) {
                                        worker.terminate();
                                    }
                                    worker = new Worker('static/textGeneratorWorker.js');
                                    worker.postMessage({ remaining_text: data.remaining_text });

                                    worker.onmessage = function (e) {
                                        if (e.data.type === 'text') {
                                            botMessage.innerText += e.data.content; // 文字を1つずつ追加


                                            if (autoScroll) {
                                                chatMessages.scrollTop = chatMessages.scrollHeight;
                                                console.log(autoScroll);
                                            }
                                        } else if (e.data.type === 'done') {
                                            // 全ての文字が出力された後にYes/Noボタンを追加
                                            if (data.yes_no_phrase != null) {
                                                const chatMessage = document.createElement('div');
                                                chatMessage.className = 'chat-message bot';
                                                chatMessage.innerHTML = `
                                    ${data.yes_no_phrase}
                                    <div class="button-container">
                                        <button class="btn btn-yes mb-2 mx-3" onclick="handleButtonClick('はい')">はい　<i class="bi bi-hand-thumbs-up-fill"></i></button>
                                        <button class="btn btn-no mb-2 mx-3" onclick="handleButtonClick('いいえ')">いいえ <i class="bi bi-hand-thumbs-down-fill"></i></button>
                                    </div>`;
                                                chatMessages.appendChild(chatMessage);


                                                chatMessages.scrollTop = chatMessages.scrollHeight;

                                            }
                                        }
                                    };
                                } else {
                                    console.log("Web Workers are not supported.");
                                }
                            }
                        }


                        //yes/noだけが存在する時
                        if (data.remaining_text == 'Empty') {
                            var spinnerElement = document.getElementById("spiner");
                            // 要素が存在する場合に削除
                            if (spinnerElement) {
                                // スピナーの親要素を取得
                                var botMessage = spinnerElement.parentElement;
                                // スピナー要素を削除
                                spinnerElement.remove();
                                // yes/noを挿入
                                botMessage.innerHTML = `
                                    ${data.yes_no_phrase}
                                <div class="button-container">
                                    <button class="btn btn-yes mb-2 mx-3" onclick="handleButtonClick('はい')">はい　<i class="bi bi-hand-thumbs-up-fill"></i></button>
                                    <button class="btn btn-no mb-2 mx-3" onclick="handleButtonClick('いいえ')">いいえ <i class="bi bi-hand-thumbs-down-fill"></i></button>
                                </div> `
                            }
                        }

                        current_plan = data.current_plan;
                        // 決定事項のデータを表示・更新
                        currentPlanContainer.innerHTML = ''; // 既存の内容をクリア
                        const planMessage = document.createElement('p');
                        planMessage.innerText = data.current_plan;
                        // フェードイン効果を追加
                        planMessage.classList.add('fade-in');
                        currentPlanContainer.appendChild(planMessage);

                        // チャットを一番下までスクロール
                        chatMessages.scrollTop = chatMessages.scrollHeight;
                    });

                // 入力フィールドをクリアし、サイズを元に戻す
                messageInput.value = '';
                messageInput.style.height = 'auto';
                // チャットを一番下までスクロール
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        });


        //Yes/Noボタンからのデータ送信
        function handleButtonClick(response) {
            const chatMessages = document.getElementById('chatMessages1');
            const currentPlanContainer = document.getElementById('chatMessages2');

            const userMessage = document.createElement('div');
            userMessage.classList.add('chat-message', 'user');
            userMessage.innerText = response;
            chatMessages.appendChild(userMessage);

            setTimeout(function () {
                const botMessage = document.createElement('div');
                botMessage.classList.add('chat-message', 'bot');
                botMessage.innerHTML = `
            <div class="spinner-grow text-info" id="spiner" role="status">
            <span class="visually-hidden">Loading...</span>
            </div>`
                chatMessages.appendChild(botMessage);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }, 100);

            const timeoutId = setTimeout(function () {
                alert("サーバーからの応答がありません。もう一度お試しください。");
            }, 60000);

            let worker;
            fetch('/reply_send_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ message: response })
            })
                .then(response => response.json())
                .then(data => {
                    clearTimeout(timeoutId); // 応答があった場合、タイムアウトをクリア

                    if (data.remaining_text != 'Empty') {
                        var spinnerElement = document.getElementById("spiner");
                        if (spinnerElement) {
                            var botMessage = spinnerElement.parentElement;
                            spinnerElement.remove();
                            botMessage.innerText = ''; // テキストを一旦クリア

                            // Web Workerの作成と処理開始
                            if (typeof (Worker) !== "undefined") {
                                if (worker) {
                                    worker.terminate(); // 以前のWorkerが存在したら終了
                                }
                                worker = new Worker('static/textGeneratorWorker.js');
                                worker.postMessage({ remaining_text: data.remaining_text });

                                worker.onmessage = function (e) {
                                    if (e.data.type === 'text') {
                                        botMessage.innerText += e.data.content; // 1文字ずつ追加
                                        //スクロールがtrueの時にはスクロールする
                                        if (autoScroll) {
                                            chatMessages.scrollTop = chatMessages.scrollHeight;
                                            console.log(autoScroll);
                                        }
                                    } else if (e.data.type === 'done') {
                                        // 全ての文字が出力された後にYes/Noボタンを追加
                                        if (data.yes_no_phrase != null) {
                                            const chatMessage = document.createElement('div');
                                            chatMessage.className = 'chat-message bot';
                                            chatMessage.innerHTML = `
                                    ${data.yes_no_phrase}
                                    <div class="button-container">
                                        <button class="btn btn-yes mb-2 mx-3" onclick="handleButtonClick('はい')">はい　<i class="bi bi-hand-thumbs-up-fill"></i></button>
                                        <button class="btn btn-no mb-2 mx-3" onclick="handleButtonClick('いいえ')">いいえ <i class="bi bi-hand-thumbs-down-fill"></i></button>
                                    </div>`;
                                            chatMessages.appendChild(chatMessage);
                                            chatMessages.scrollTop = chatMessages.scrollHeight;
                                        }
                                    }
                                };
                            } else {
                                console.log("Web Workers are not supported.");
                            }
                        }
                    }

                    //yes/noだけが存在する時
                    if (data.remaining_text == 'Empty') {
                        var spinnerElement = document.getElementById("spiner");
                        // 要素が存在する場合に削除
                        if (spinnerElement) {
                            // スピナーの親要素を取得
                            var botMessage = spinnerElement.parentElement;
                            // スピナー要素を削除
                            spinnerElement.remove();
                            // yes/noを挿入
                            botMessage.innerHTML = `
                                    ${data.yes_no_phrase}
                                <div class="button-container">
                                    <button class="btn btn-yes mb-2 mx-3" onclick="handleButtonClick('はい')">はい　<i class="bi bi-hand-thumbs-up-fill"></i></button>
                                    <button class="btn btn-no mb-2 mx-3" onclick="handleButtonClick('いいえ')">いいえ <i class="bi bi-hand-thumbs-down-fill"></i></button>
                                </div> `
                        }
                    }

                    current_plan = data.current_plan;

                    // 決定事項のデータを表示・更新
                    currentPlanContainer.innerHTML = ''; // 既存の内容をクリア
                    const planMessage = document.createElement('p');
                    planMessage.innerText = data.current_plan;
                    // フェードイン効果を追加
                    planMessage.classList.add('fade-in');
                    currentPlanContainer.appendChild(planMessage);


                    chatMessages.scrollTop = chatMessages.scrollHeight;
                });

            chatMessages.scrollTop = chatMessages.scrollHeight;
        }


        //決定ボタンのデータ送信
        document.getElementById('sendBu').addEventListener('click', function () {
            const currentPlanContainer = document.getElementById('chatMessages2');
            const currentPlan = currentPlanContainer.innerText.trim();

            if (currentPlan !== '') {
                fetch('/reply_submit_plan', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ plan: currentPlan })
                })
                    .then(response => response.json())
                    .then(data => {
                        window.location.href = '/complete';
                    })
                    .catch(error => {
                        console.error('Error submitting plan:', error);
                    });
            } else {
                console.warn('No plan to submit.');
            }
        });

        // Enterキーを押したときに、メッセージを送信
        document.getElementById('message').addEventListener('keypress', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                document.querySelector('.btn-chat').click();
            }
        });

        //入力のテキストエリアを大きくする
        document.getElementById('message').addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });

        //iボタンを押したときに、チャット案の表示
        document.getElementById('information').addEventListener('click', function () {
            const infoOptions = document.getElementById('info-options');
            infoOptions.style.display = infoOptions.style.display === 'none' ? 'block' : 'none';
        });

        document.getElementById('sendBu').addEventListener('click', function () {
            var spinnerOverlay = document.getElementById('spinnerOverlay');
            spinnerOverlay.style.display = 'flex';
        });

        // ページを開いた直後にテキストエリアにフォーカスを当てる
        window.onload = function () {
            document.getElementById('message').focus();
        };