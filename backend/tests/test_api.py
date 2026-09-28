"""Integration tests for MangataAgent FastAPI HTTP API."""

import unittest
from fastapi.testclient import TestClient

from backend.app.main import app


class APIRouteTests(unittest.TestCase):
    def test_root_redirects_to_docs(self):
        with TestClient(app) as client:
            response = client.get("/", follow_redirects=False)
            self.assertEqual(response.status_code, 307)
            self.assertEqual(response.headers["location"], "/docs")

    def test_health_check(self):
        with TestClient(app) as client:
            response = client.get("/api/v1/health")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "ok")
            self.assertTrue(data["redis"])

    def test_conversations_api_lifecycle(self):
        with TestClient(app) as client:
            headers = {"Authorization": "Bearer test-token"}
            # 1. Create conversation
            res = client.post("/api/v1/conversations", headers=headers)
            self.assertEqual(res.status_code, 201)
            conv = res.json()
            conv_id = conv["conversation_id"]
            self.assertTrue(conv_id)

            # 2. Get conversation
            res = client.get(f"/api/v1/conversations/{conv_id}", headers=headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["conversation_id"], conv_id)

            # 3. List conversations
            res = client.get("/api/v1/conversations", headers=headers)
            self.assertEqual(res.status_code, 200)
            items = res.json()["items"]
            self.assertTrue(any(c["conversation_id"] == conv_id for c in items))

            # 4. List messages (empty initially)
            res = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["items"], [])


if __name__ == "__main__":
    unittest.main()
