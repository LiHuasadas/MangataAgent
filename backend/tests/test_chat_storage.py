"""Storage contracts against a dedicated test namespace on local Redis."""

import unittest
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from time import sleep
from uuid import uuid4

from pydantic import ValidationError
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from backend.app.chat.config import ChatRedisConfig
from backend.app.chat.models import (
    ConversationBusy, ConversationNotFound, LeaseLost, MessageNotFound, RequestConflict,
    TurnStatus,
)
from backend.app.chat.repository import RedisConversationRepository
from backend.app.chat.service import ChatService
from backend.app.core.message import ChatMessage, Message
from backend.app.memory.manager import MemoryManager
from backend.app.memory.base import MemoryItem
from backend.app.tools.builtin import MemoryTool
from backend.app.protocols.types import Task, TaskStatus, TaskState, TaskTenantContext


class ModelTests(unittest.TestCase):
    def test_task_tenant_context_preserves_legacy_tasks(self):
        old = Task(id="task1", status=TaskStatus(state=TaskState.SUBMITTED))
        self.assertIsNone(Task.model_validate_json(old.model_dump_json()).tenant_context)
        context = TaskTenantContext(user_id="u1", conversation_id="c1", request_id="r1",
                                    workspace_id="w1")
        new = old.model_copy(update={"tenant_context": context})
        self.assertEqual(Task.model_validate_json(new.model_dump_json()).tenant_context, context)

    def test_host_passes_extracted_text_to_context_builder(self):
        source = Path(__file__).parents[1] / "app" / "agents" / "host_agent.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and node.func.attr == "build" and isinstance(node.func.value, ast.Attribute)
                 and node.func.value.attr == "context_builder"]
        self.assertEqual(len(calls), 1)
        query = next(keyword.value for keyword in calls[0].keywords if keyword.arg == "user_query")
        self.assertIsInstance(query, ast.Name)
        self.assertEqual(query.id, "message_text")

    def test_chat_message_round_trip_and_llm_conversion(self):
        message = ChatMessage(message_id="m1", conversation_id="c1", user_id="u1",
                              request_id="r1", role="user", content="hello", sequence=1)
        restored = ChatMessage.model_validate_json(message.model_dump_json())
        self.assertEqual(restored, message)
        self.assertEqual(restored.created_at.utcoffset().total_seconds(), 0)
        self.assertEqual(restored.to_llm_message().to_dict(), {"role": "user", "content": "hello"})
        self.assertEqual(Message("hello", "user").timestamp.utcoffset().total_seconds(), 0)
        with self.assertRaises(ValidationError):
            ChatMessage.model_validate({**message.model_dump(), "created_at": datetime(2026, 1, 1)})

    def test_working_memory_is_scoped_but_long_term_is_user_wide(self):
        manager = MemoryManager(user_id="u1", conversation_id="c1", enable_episodic=False,
                                enable_semantic=False)
        manager.add_memory("private marker", memory_type="working")
        self.assertEqual(len(manager.retrieve_memories("private marker", ["working"])), 1)
        manager.conversation_id = "c2"
        self.assertEqual(manager.retrieve_memories("private marker", ["working"]), [])
        class LongTermProbe:
            def retrieve(self, **kwargs):
                assert kwargs["user_id"] == "u1"
                assert kwargs["conversation_id"] is None
                return [MemoryItem(id="long", content="shared preference", memory_type="semantic",
                                   user_id="u1", conversation_id="c1", timestamp=datetime.now())]

        manager.memory_types["semantic"] = LongTermProbe()
        self.assertEqual(manager.retrieve_memories("shared preference", ["semantic"])[0].id, "long")
        manager.conversation_id = None
        with self.assertRaises(ValueError):
            manager.add_memory("other", memory_type="working")

    def test_memory_tool_uses_supplied_conversation_scope(self):
        tool = MemoryTool(user_id="u1", conversation_id="c1", memory_types=["working"])
        tool.memory_manager.add_memory("secret", memory_type="working")
        tool.memory_manager.conversation_id = "c2"
        self.assertEqual(tool.memory_manager.retrieve_memories("secret", ["working"]), [])


class RedisStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.redis = Redis.from_url("redis://localhost:6378/0", decode_responses=True)
        cls.redis.ping()

    def setUp(self):
        self.user = "test_" + uuid4().hex
        self.other_user = "test_" + uuid4().hex
        self.config = ChatRedisConfig(lock_ttl_ms=250, result_ttl_seconds=86400)
        self.service = ChatService(RedisConversationRepository(self.redis, self.config))
        self.conversation = self.service.create_conversation(self.user)

    def tearDown(self):
        # Only remove keys belonging to the two random users created by this test.
        for uid in (self.user, self.other_user):
            keys = list(self.redis.scan_iter(match=f"chat:{{{uid}}}:*"))
            if keys:
                self.redis.delete(*keys)

    def test_owner_message_lookup_and_pagination(self):
        first = self.service.begin_turn(self.user, self.conversation.conversation_id, "r1", "one")
        second = self.service.complete_turn(self.user, self.conversation.conversation_id,
                                            "r1", first.lock_token, "answer")
        self.assertEqual(first.status, TurnStatus.PROCESSING)
        self.assertEqual(second.status, TurnStatus.COMPLETED)
        page = self.service.list_messages(self.user, self.conversation.conversation_id, limit=1)
        self.assertEqual(len(page), 1)
        self.assertEqual(page[0].sequence, 1)
        next_page = self.service.list_messages(self.user, self.conversation.conversation_id,
                                               after_sequence=1)
        self.assertEqual(next_page[0].sequence, 2)
        self.assertEqual(next_page[0].reply_to_message_id, first.user_message_id)
        self.assertEqual(self.service.get_message(self.user, self.conversation.conversation_id,
                                                  second.assistant_message_id).content, "answer")
        self.assertEqual(self.service.list_conversations(self.user)[0].conversation_id,
                         self.conversation.conversation_id)
        with self.assertRaises(ConversationNotFound):
            self.service.list_messages(self.other_user, self.conversation.conversation_id)
        with self.assertRaises(MessageNotFound):
            self.service.get_message(self.user, self.conversation.conversation_id, "missing")

    def test_duplicate_and_conflicting_request(self):
        cid = self.conversation.conversation_id
        with ThreadPoolExecutor(max_workers=2) as pool:
            turns = list(pool.map(lambda _: self.service.begin_turn(self.user, cid, "same", "hello"), range(2)))
        self.assertEqual(sum(turn.lock_token is not None for turn in turns), 1)
        self.assertEqual(len(self.service.list_messages(self.user, cid)), 1)
        owner = next(turn for turn in turns if turn.lock_token)
        with self.assertRaises(RequestConflict):
            self.service.begin_turn(self.user, cid, "same", "changed")
        self.service.complete_turn(self.user, cid, "same", owner.lock_token, "done")
        repeated = self.service.begin_turn(self.user, cid, "same", "hello")
        self.assertEqual(repeated.status, TurnStatus.COMPLETED)
        self.assertIsNotNone(repeated.assistant_message_id)
        self.assertEqual(len(self.service.list_messages(self.user, cid)), 2)
        another = self.service.create_conversation(self.user)
        with self.assertRaises(RequestConflict):
            self.service.begin_turn(self.user, another.conversation_id, "same", "hello")

    def test_failure_keeps_input_and_releases_lock(self):
        cid = self.conversation.conversation_id
        started = self.service.begin_turn(self.user, cid, "fail", "help")
        failed = self.service.fail_turn(self.user, cid, "fail", started.lock_token, "tool failed")
        self.assertEqual(failed.status, TurnStatus.FAILED)
        self.assertEqual(len(self.service.list_messages(self.user, cid)), 1)
        next_turn = self.service.begin_turn(self.user, cid, "new", "retry manually")
        self.assertIsNotNone(next_turn.lock_token)
        self.service.fail_turn(self.user, cid, "new", next_turn.lock_token, "cancelled")

    def test_lost_lease_cannot_commit(self):
        cid = self.conversation.conversation_id
        started = self.service.begin_turn(self.user, cid, "old", "old input")
        sleep(0.35)
        with self.assertRaises(LeaseLost):
            self.service.complete_turn(self.user, cid, "old", started.lock_token, "stale answer")
        self.assertEqual(self.service.get_turn(self.user, cid, "old").status, TurnStatus.UNKNOWN)
        self.assertEqual(len(self.service.list_messages(self.user, cid)), 1)
        new = self.service.begin_turn(self.user, cid, "new", "new input")
        self.assertIsNotNone(new.lock_token)
        self.service.fail_turn(self.user, cid, "new", new.lock_token, "cancelled")
        with self.assertRaises(LeaseLost):
            self.service.fail_turn(self.user, cid, "old", started.lock_token, "too late")

    def test_redis_unavailable_fails_without_fallback(self):
        class UnavailableRedis:
            def ping(self):
                raise RedisConnectionError("offline")

        with self.assertRaises(RedisConnectionError):
            RedisConversationRepository(UnavailableRedis(), self.config)


if __name__ == "__main__":
    unittest.main()
