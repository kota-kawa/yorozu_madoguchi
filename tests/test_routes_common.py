"""
`backend.routes.common` の共通ルート生成ロジックを検証するテスト。
Tests for shared route factories in `backend.routes.common`.
"""

import unittest
from unittest.mock import patch

from flask import Blueprint, Flask

from backend.routes.common import make_chat_send_message_route, make_complete_route


class RoutesCommonTests(unittest.TestCase):
    """
    共通ルートファクトリの主要な分岐を確認するテストケース群
    Test cases for key branches in shared route factories.
    """

    def setUp(self):
        self.app = Flask(__name__)

    def test_make_chat_send_message_route_returns_rich_error_payload(self):
        """
        EN: Chat route factory should use rich error payload on failure.
        JP: チャットルートファクトリは失敗時にリッチなエラーペイロードを返すこと。
        """
        blueprint = Blueprint("chat_test_bp", __name__)

        make_chat_send_message_route(
            blueprint=blueprint,
            route_path="/chat",
            mode="chat_test",
            endpoint_name="chat",
            check_and_increment_limit=lambda *_args, **_kwargs: (
                True,
                1,
                10,
                "normal",
                False,
                None,
            ),
            resolve_user_language=lambda *_args, **_kwargs: "ja",
            get_user_language=lambda *_args, **_kwargs: "ja",
            save_user_language=lambda *_args, **_kwargs: None,
            chat_with_llama=lambda *_args, **_kwargs: (
                "ok",
                "",
                None,
                None,
                False,
                "",
                False,
            ),
            stream_chat_with_llama=lambda *_args, **_kwargs: iter(()),
            logger=self.app.logger,
        )
        self.app.register_blueprint(blueprint)
        client = self.app.test_client()

        headers = {"Origin": "http://localhost:5173"}
        with patch("backend.routes.common.security.is_csrf_valid", return_value=False):
            response = client.post(
                "/chat",
                json={"message": "hello", "user_type": "normal"},
                headers=headers,
            )

        self.assertEqual(response.status_code, 403)
        payload = response.get_json()
        self.assertIsInstance(payload, dict)
        self.assertIn("error", payload)
        self.assertIn("response", payload)
        self.assertIn("error_type", payload)
        self.assertIn("error_code", payload)
        self.assertIn("current_plan", payload)
        self.assertIn("yes_no_phrase", payload)
        self.assertIn("choices", payload)
        self.assertIn("is_date_select", payload)
        self.assertIn("remaining_text", payload)
        self.assertIn("used_web_search", payload)

    def test_make_complete_route_formats_and_returns_json(self):
        """
        EN: Complete route factory should format loader result and return JSON.
        JP: 完了ルートファクトリはローダー結果を整形してJSONで返すこと。
        """
        blueprint = Blueprint("complete_test_bp", __name__)

        make_complete_route(
            blueprint=blueprint,
            route_path="/complete",
            mode="complete_test",
            endpoint_name="complete",
            load_reservation_data=lambda session_id: [
                {"id": 1, "session_id": session_id, "destinations": "東京"}
            ],
            formatter=lambda items: [
                f"目的地：{items[0]['destinations']}" if items else "empty"
            ],
            logger=self.app.logger,
        )
        self.app.register_blueprint(blueprint)
        client = self.app.test_client()

        client.set_cookie("session_id", "session-complete")
        response = client.get("/complete", headers={"Accept": "application/json"})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload, {"reservation_data": ["目的地：東京"]})


if __name__ == "__main__":
    unittest.main()
