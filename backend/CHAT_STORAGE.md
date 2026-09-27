# Redis conversation storage

This stage exposes a Python service, with no HTTP endpoint or Agent execution.
Install `backend/requirements-api.txt` and run Redis at `localhost:6378`, or set
`CHAT_REDIS_URL`. The service calls `PING` when constructed and raises a Redis
connection error if storage is unavailable.

```python
from backend.app.chat import ChatService, RedisConversationRepository

service = ChatService(RedisConversationRepository.from_config())
conversation = service.create_conversation("trusted_user_id")
turn = service.begin_turn("trusted_user_id", conversation.conversation_id, "request_1", "Hello")

# A future Agent runner must keep the lease alive while it works.
service.renew_turn("trusted_user_id", conversation.conversation_id, "request_1", turn.lock_token)
service.complete_turn("trusted_user_id", conversation.conversation_id, "request_1", turn.lock_token, "Hi")
messages = service.list_messages("trusted_user_id", conversation.conversation_id)
```

Only a newly accepted turn has `lock_token`. Duplicate requests return their
existing state or result without a token. An expired lease reports `UNKNOWN`;
the caller must inspect external side effects before any manual retry with a
new request ID. Accepted user messages remain in history if `fail_turn` is
called. Completed and failed request records expire after 24 hours by default;
conversation and message records do not expire. Redis keys are grouped into a
single hash slot per user for multi-key scripts.

The `user_id` argument must come from a trusted caller. The later API layer
will map configured Bearer tokens to user IDs and never accept a client-supplied
owner ID. This stage does not configure Redis persistence; production durability
depends on the Redis server's AOF/backup settings.

Run the local integration tests with:

```powershell
python -m unittest discover -s backend/tests -v
```
