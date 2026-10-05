from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sqlite3
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

import psycopg
from pydantic import BaseModel, Field


ConversationStatus = Literal["active", "awaiting_clarification", "completed"]


class ConversationState(BaseModel):
    conversation_id: UUID
    status: ConversationStatus = "active"
    original_question: str | None = None
    clarification_question: str | None = None
    relevant_context: dict[str, Any] = Field(default_factory=dict)


class ConversationStore(Protocol):
    async def get(self, conversation_id: UUID) -> ConversationState | None: ...
    async def ensure(self, conversation_id: UUID, locale: str) -> None: ...
    async def add_message(self, conversation_id: UUID, role: str, content: str, state: str | None) -> None: ...
    async def set_awaiting(
        self,
        conversation_id: UUID,
        original_question: str,
        clarification_question: str,
        relevant_context: dict[str, Any],
    ) -> None: ...
    async def complete(self, conversation_id: UUID, relevant_context: dict[str, Any]) -> None: ...


class PostgresConversationStore:
    def __init__(self, database_url: str) -> None:
        self.dsn = database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    async def get(self, conversation_id: UUID) -> ConversationState | None:
        return await asyncio.to_thread(self._get, conversation_id)

    def _get(self, conversation_id: UUID) -> ConversationState | None:
        with psycopg.connect(self.dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, status, original_question, clarification_question, relevant_context
                FROM conversations WHERE id = %s
                """,
                (conversation_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return ConversationState(
            conversation_id=row[0],
            status=row[1],
            original_question=row[2],
            clarification_question=row[3],
            relevant_context=row[4] or {},
        )

    async def ensure(self, conversation_id: UUID, locale: str) -> None:
        await asyncio.to_thread(self._ensure, conversation_id, locale)

    def _ensure(self, conversation_id: UUID, locale: str) -> None:
        with psycopg.connect(self.dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO conversations (id, locale, status)
                VALUES (%s, %s, 'active')
                ON CONFLICT (id) DO NOTHING
                """,
                (conversation_id, locale),
            )

    async def add_message(self, conversation_id: UUID, role: str, content: str, state: str | None) -> None:
        await asyncio.to_thread(self._add_message, conversation_id, role, content, state)

    def _add_message(self, conversation_id: UUID, role: str, content: str, state: str | None) -> None:
        with psycopg.connect(self.dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO messages (id, conversation_id, role, content, state)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (uuid4(), conversation_id, role, content, state),
            )
            cursor.execute(
                "UPDATE conversations SET updated_at = now() WHERE id = %s",
                (conversation_id,),
            )

    async def set_awaiting(
        self,
        conversation_id: UUID,
        original_question: str,
        clarification_question: str,
        relevant_context: dict[str, Any],
    ) -> None:
        await asyncio.to_thread(
            self._set_awaiting,
            conversation_id,
            original_question,
            clarification_question,
            relevant_context,
        )

    def _set_awaiting(
        self,
        conversation_id: UUID,
        original_question: str,
        clarification_question: str,
        relevant_context: dict[str, Any],
    ) -> None:
        with psycopg.connect(self.dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE conversations
                SET status = 'awaiting_clarification', original_question = %s,
                    clarification_question = %s, relevant_context = %s::jsonb,
                    completed_at = NULL, updated_at = now()
                WHERE id = %s
                """,
                (original_question, clarification_question, json.dumps(relevant_context), conversation_id),
            )

    async def complete(self, conversation_id: UUID, relevant_context: dict[str, Any]) -> None:
        await asyncio.to_thread(self._complete, conversation_id, relevant_context)

    def _complete(self, conversation_id: UUID, relevant_context: dict[str, Any]) -> None:
        with psycopg.connect(self.dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE conversations
                SET status = 'completed', relevant_context = %s::jsonb,
                    completed_at = now(), updated_at = now()
                WHERE id = %s
                """,
                (json.dumps(relevant_context), conversation_id),
            )


class SQLiteConversationStore:
    """Persistent single-host conversation state for the production API."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    locale TEXT NOT NULL DEFAULT 'ar',
                    status TEXT NOT NULL DEFAULT 'active',
                    original_question TEXT,
                    clarification_question TEXT,
                    relevant_context TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    state TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    async def get(self, conversation_id: UUID) -> ConversationState | None:
        return await asyncio.to_thread(self._get, conversation_id)

    def _get(self, conversation_id: UUID) -> ConversationState | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT id, status, original_question, clarification_question, relevant_context
                FROM conversations WHERE id = ?
                """,
                (str(conversation_id),),
            ).fetchone()
        if row is None:
            return None
        return ConversationState(
            conversation_id=UUID(row["id"]),
            status=row["status"],
            original_question=row["original_question"],
            clarification_question=row["clarification_question"],
            relevant_context=json.loads(row["relevant_context"] or "{}"),
        )

    async def ensure(self, conversation_id: UUID, locale: str) -> None:
        await asyncio.to_thread(self._ensure, conversation_id, locale)

    def _ensure(self, conversation_id: UUID, locale: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO conversations (id, locale) VALUES (?, ?)",
                (str(conversation_id), locale),
            )

    async def add_message(self, conversation_id: UUID, role: str, content: str, state: str | None) -> None:
        await asyncio.to_thread(self._add_message, conversation_id, role, content, state)

    def _add_message(self, conversation_id: UUID, role: str, content: str, state: str | None) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO messages (id, conversation_id, role, content, state) VALUES (?, ?, ?, ?, ?)",
                (str(uuid4()), str(conversation_id), role, content, state),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (str(conversation_id),),
            )

    async def set_awaiting(
        self,
        conversation_id: UUID,
        original_question: str,
        clarification_question: str,
        relevant_context: dict[str, Any],
    ) -> None:
        await asyncio.to_thread(
            self._set_awaiting,
            conversation_id,
            original_question,
            clarification_question,
            relevant_context,
        )

    def _set_awaiting(
        self,
        conversation_id: UUID,
        original_question: str,
        clarification_question: str,
        relevant_context: dict[str, Any],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE conversations
                SET status = 'awaiting_clarification', original_question = ?,
                    clarification_question = ?, relevant_context = ?, completed_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    original_question,
                    clarification_question,
                    json.dumps(relevant_context, ensure_ascii=False),
                    str(conversation_id),
                ),
            )

    async def complete(self, conversation_id: UUID, relevant_context: dict[str, Any]) -> None:
        await asyncio.to_thread(self._complete, conversation_id, relevant_context)

    def _complete(self, conversation_id: UUID, relevant_context: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE conversations
                SET status = 'completed', relevant_context = ?,
                    completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (json.dumps(relevant_context, ensure_ascii=False), str(conversation_id)),
            )


class InMemoryConversationStore:
    """Deterministic server-side store used only by endpoint integration tests."""

    def __init__(self) -> None:
        self.states: dict[UUID, ConversationState] = {}
        self.messages: dict[UUID, list[dict[str, str | None]]] = {}

    async def get(self, conversation_id: UUID) -> ConversationState | None:
        return self.states.get(conversation_id)

    async def ensure(self, conversation_id: UUID, locale: str) -> None:
        self.states.setdefault(conversation_id, ConversationState(conversation_id=conversation_id))
        self.messages.setdefault(conversation_id, [])

    async def add_message(self, conversation_id: UUID, role: str, content: str, state: str | None) -> None:
        self.messages.setdefault(conversation_id, []).append(
            {"role": role, "content": content, "state": state}
        )

    async def set_awaiting(
        self,
        conversation_id: UUID,
        original_question: str,
        clarification_question: str,
        relevant_context: dict[str, Any],
    ) -> None:
        self.states[conversation_id] = ConversationState(
            conversation_id=conversation_id,
            status="awaiting_clarification",
            original_question=original_question,
            clarification_question=clarification_question,
            relevant_context=relevant_context,
        )

    async def complete(self, conversation_id: UUID, relevant_context: dict[str, Any]) -> None:
        current = self.states[conversation_id]
        self.states[conversation_id] = current.model_copy(
            update={"status": "completed", "relevant_context": relevant_context}
        )
