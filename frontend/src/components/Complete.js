import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useSearchParams } from 'react-router-dom';

const Complete = () => {
    const [reservationData, setReservationData] = useState([]);
    const [searchParams] = useSearchParams();
    const sessionId = searchParams.get('session_id');

    useEffect(() => {
        if (sessionId) {
            axios.get(`/api/complete?session_id=${sessionId}`)
                .then(response => {
                    setReservationData(response.data.reservation_data);
                })
                .catch(error => console.error("Error fetching reservation data:", error));
        }
    }, [sessionId]);

    return (
        <div className="container mt-5">
            <div className="row justify-content-center">
                <div className="col-md-6">
                    <div className="card text-center mt-5">
                        <div className="card-header bg-success text-white">
                            <h3>予約完了</h3>
                        </div>
                        <div className="card-body">
                            <h5 className="card-title">ご予約ありがとうございます！</h5>
                            <p className="card-text">以下の内容で予約が完了しました。</p>
                            <ul className="list-group list-group-flush">
                                {reservationData.map((detail, index) => (
                                    <li key={index} className="list-group-item">{detail}</li>
                                ))}
                            </ul>
                        </div>
                        <div className="card-footer text-muted">
                            ご不明な点がございましたら、サポートまでご連絡ください。
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Complete;
