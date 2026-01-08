import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import './Chat.css';

const Chat = () => {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [currentPlan, setCurrentPlan] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [showInfo, setShowInfo] = useState(false);
    const messagesEndRef = useRef(null);
    const [sessionId, setSessionId] = useState(null);
    const navigate = useNavigate();

    useEffect(() => {
        // Initialize session
        axios.post('/api/init')
            .then(response => {
                setSessionId(response.data.session_id);
                // Initial bot message
                setMessages([{ type: 'bot', content: 'どんな旅行の計画を一緒に立てますか？😊' }]);
            })
            .catch(error => console.error("Session init error:", error));
    }, []);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const handleSendMessage = async (text) => {
        if (!text.trim()) return;

        const userMessage = { type: 'user', content: text };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await axios.post('/travel_send_message', {
                message: text,
                session_id: sessionId
            });

            const data = response.data;
            setIsLoading(false);

            if (data.remaining_text && data.remaining_text !== 'Empty') {
                // Simulate typing effect
                const botMessageId = Date.now();
                setMessages(prev => [...prev, { type: 'bot', content: '', id: botMessageId }]);

                let i = 0;
                const interval = setInterval(() => {
                    setMessages(prev => prev.map(msg =>
                        msg.id === botMessageId
                        ? { ...msg, content: msg.content + data.remaining_text.charAt(i) }
                        : msg
                    ));
                    i++;
                    if (i >= data.remaining_text.length) {
                        clearInterval(interval);
                        // Add Yes/No buttons if needed
                        if (data.yes_no_phrase) {
                            setMessages(prev => [...prev, {
                                type: 'bot',
                                content: data.yes_no_phrase,
                                isYesNo: true
                            }]);
                        }
                    }
                }, 40);
            } else if (data.yes_no_phrase) {
                setMessages(prev => [...prev, {
                    type: 'bot',
                    content: data.yes_no_phrase,
                    isYesNo: true
                }]);
            } else if (data.response) {
                 setMessages(prev => [...prev, { type: 'bot', content: data.response }]);
            }

            if (data.current_plan) {
                setCurrentPlan(data.current_plan);
            }

        } catch (error) {
            console.error("Error sending message:", error);
            setIsLoading(false);
            setMessages(prev => [...prev, { type: 'bot', content: "エラーが発生しました。もう一度お試しください。" }]);
        }
    };

    const handleYesNo = (answer) => {
        handleSendMessage(answer);
    };

    const handleSubmitPlan = async () => {
        if (!currentPlan) return;
        setIsLoading(true);
        try {
            await axios.post('/travel_submit_plan', {
                plan: currentPlan,
                session_id: sessionId
            });
            navigate(`/complete?session_id=${sessionId}`);
        } catch (error) {
            console.error("Error submitting plan:", error);
            setIsLoading(false);
        }
    };

    return (
        <div className="chat-container-wrapper">
            <div className="chat-container">
                <div className="card chat-card">
                    <div className="card-body chat-messages" id="chatMessages1">
                        {messages.map((msg, index) => (
                            <div key={index} className={`chat-message ${msg.type}`}>
                                {msg.content}
                                {msg.isYesNo && (
                                    <div className="button-container">
                                        <button className="btn btn-yes mb-2 mx-3" onClick={() => handleYesNo('はい')}>はい <i className="bi bi-hand-thumbs-up-fill"></i></button>
                                        <button className="btn btn-no mb-2 mx-3" onClick={() => handleYesNo('いいえ')}>いいえ <i className="bi bi-hand-thumbs-down-fill"></i></button>
                                    </div>
                                )}
                            </div>
                        ))}
                        {isLoading && (
                            <div className="chat-message bot">
                                <div className="spinner-grow text-info" role="status">
                                    <span className="visually-hidden">Loading...</span>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>
                    <div className="card-footer">
                         {showInfo && (
                            <div id="info-options" className="info-text" style={{width: '90%'}}>
                                <h1 style={{textAlign: 'center'}}>*** 入力の例 ***</h1>
                                <div className="option">・どこに行くのがおすすめ？</div>
                                <div className="option">・どんな有名スポットがある？</div>
                                <div className="option">・落ち着ける場所はある？</div>
                                <div className="option">・ご飯に行くならどこ？</div>
                            </div>
                        )}
                        <div className="chat-input">
                            <button type="button" className="btn-info original-btn" onClick={() => setShowInfo(!showInfo)}>
                                <i className="bi bi-info-circle-fill"></i>
                            </button>
                            <form className="d-flex flex-grow-1" onSubmit={(e) => { e.preventDefault(); handleSendMessage(input); }}>
                                <textarea
                                    className="form-control"
                                    placeholder="メッセージを入力．．．"
                                    rows="1"
                                    maxLength="3000"
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter' && !e.shiftKey) {
                                            e.preventDefault();
                                            handleSendMessage(input);
                                        }
                                    }}
                                ></textarea>
                                <button type="submit" className="btn-chat original-btn rounded">
                                    <i className="bi bi-chat-dots-fill"></i>
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
                <div className="card chat-card">
                    <div className="card-header">
                        <h1>決定している状況</h1>
                    </div>
                    <div className="card-body chat-messages" id="chatMessages2">
                        <p className="fade-in">{currentPlan}</p>
                    </div>
                    <div className="card-footer">
                        <div className="bottom-right-content">
                            <button className="btn-decide rounded" onClick={handleSubmitPlan}>
                                <i className="bi bi-hand-thumbs-up-fill"></i>決定
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            {isLoading && (
                 <div id="spinnerOverlay" style={{display: 'flex'}}>
                    <div className="spinner-border" role="status" style={{width: '10rem', height: '10rem'}}>
                        <span className="visually-hidden">Loading...</span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Chat;
