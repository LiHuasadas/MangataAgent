"""Unit and integration tests for User Registration, Login, and Session Authentication using Redis."""

import unittest
from uuid import uuid4
from fastapi.testclient import TestClient
from redis import Redis

from backend.app.chat.config import ChatRedisConfig
from backend.app.core.auth_service import (
    AuthError,
    AuthService,
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from backend.app.main import app


class AuthServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = ChatRedisConfig.from_env()
        cls.redis = Redis.from_url(config.url, decode_responses=True)
        cls.redis.ping()

    def setUp(self):
        self.auth = AuthService(self.redis)
        self.test_username = f"user_{uuid4().hex[:8]}"
        self.test_password = "SecurePassword123!"
        self.created_keys = []

    def tearDown(self):
        # Cleanup test keys created during tests
        username_key = f"user:by_username:{self.test_username}"
        user_id = self.redis.get(username_key)
        if user_id:
            profile_key = f"user:profile:{user_id}"
            user_sessions_key = f"user:sessions_of:{user_id}"
            active_tokens = self.redis.smembers(user_sessions_key)
            for tok in active_tokens:
                self.redis.delete(f"user:session:{tok}")
            self.redis.delete(profile_key, user_sessions_key)
        self.redis.delete(username_key)

    def test_register_and_login_flow(self):
        # 1. Register
        res = self.auth.register(self.test_username, self.test_password, display_name="Test User")
        self.assertEqual(res["username"], self.test_username)
        self.assertEqual(res["display_name"], "Test User")
        self.assertTrue(res["token"])
        self.assertTrue(res["user_id"])

        # 2. Duplicate registration fails
        with self.assertRaises(UserAlreadyExistsError):
            self.auth.register(self.test_username, "AnotherPassword")

        # 3. Validate token
        user = self.auth.get_user_by_token(res["token"])
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], self.test_username)

        # 4. Login with correct password
        login_res = self.auth.login(self.test_username, self.test_password)
        self.assertEqual(login_res["username"], self.test_username)
        self.assertTrue(login_res["token"])

        # 5. Login with incorrect password
        with self.assertRaises(InvalidCredentialsError):
            self.auth.login(self.test_username, "WrongPassword")

        # 6. Logout
        logged_out = self.auth.logout(res["token"])
        self.assertTrue(logged_out)
        self.assertIsNone(self.auth.get_user_by_token(res["token"]))

    def test_invalid_username_or_short_password(self):
        with self.assertRaises(AuthError):
            self.auth.register("a", "123456")  # too short username

        with self.assertRaises(AuthError):
            self.auth.register("valid_user", "123")  # too short password


class AuthApiEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = ChatRedisConfig.from_env()
        cls.redis = Redis.from_url(config.url, decode_responses=True)
        cls.redis.ping()
        cls.client = TestClient(app)

    def setUp(self):
        self.username = f"api_user_{uuid4().hex[:8]}"
        self.password = "MyStrongPwd999"

    def tearDown(self):
        username_key = f"user:by_username:{self.username}"
        user_id = self.redis.get(username_key)
        if user_id:
            profile_key = f"user:profile:{user_id}"
            user_sessions_key = f"user:sessions_of:{user_id}"
            active_tokens = self.redis.smembers(user_sessions_key)
            for tok in active_tokens:
                self.redis.delete(f"user:session:{tok}")
            self.redis.delete(profile_key, user_sessions_key)
        self.redis.delete(username_key)

    def test_auth_api_lifecycle(self):
        # 1. Register API
        reg_resp = self.client.post(
            "/api/v1/auth/register",
            json={
                "username": self.username,
                "password": self.password,
                "display_name": "API Developer",
            },
        )
        self.assertEqual(reg_resp.status_code, 201)
        reg_data = reg_resp.json()
        self.assertTrue(reg_data["success"])
        token = reg_data["token"]
        self.assertTrue(token)
        self.assertEqual(reg_data["user"]["username"], self.username)

        # 2. /me API with Bearer token
        me_resp = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me_resp.status_code, 200)
        self.assertEqual(me_resp.json()["username"], self.username)

        # 3. Login API
        login_resp = self.client.post(
            "/api/v1/auth/login",
            json={
                "username": self.username,
                "password": self.password,
            },
        )
        self.assertEqual(login_resp.status_code, 200)
        new_token = login_resp.json()["token"]
        self.assertTrue(new_token)

        # 4. Logout API
        logout_resp = self.client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        self.assertEqual(logout_resp.status_code, 200)

        # 5. /me after logout should return 401
        revoked_me_resp = self.client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        self.assertEqual(revoked_me_resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
