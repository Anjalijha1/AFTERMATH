"""SQLite storage for the synthetic AFTERMATH environment."""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = os.getenv("AFTERMATH_DB_PATH", str(Path(__file__).resolve().parent.parent / "aftermath.db"))

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    balance_cents INTEGER NOT NULL CHECK(balance_cents >= 0)
);
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    message TEXT NOT NULL,
    requested_refund_cents INTEGER NOT NULL CHECK(requested_refund_cents >= 0)
);
CREATE TABLE IF NOT EXISTS refunds (
    refund_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
    authorization_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS tool_executions (
    execution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    customer_id TEXT,
    status TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS authorization_decisions (
    authorization_id TEXT PRIMARY KEY,
    decision TEXT NOT NULL CHECK(decision IN ('allow','deny','unknown')),
    evidence_verified INTEGER NOT NULL DEFAULT 0 CHECK(evidence_verified IN (0,1)),
    evidence_source TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS saved_scenarios (
    scenario_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    expected_decision TEXT NOT NULL CHECK(expected_decision IN ('allow','deny')),
    customer_id TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    refund_amount_cents INTEGER NOT NULL CHECK(refund_amount_cents > 0)
);
CREATE TABLE IF NOT EXISTS test_runs (
    run_id TEXT PRIMARY KEY,
    scenario_id TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK(verdict IN ('PASS','FAIL','UNVERIFIED','ERROR')),
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE TABLE IF NOT EXISTS events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
"""

def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(seed: bool = True) -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        if seed:
            conn.execute(
                "INSERT OR IGNORE INTO customers(customer_id, name, balance_cents) VALUES (?, ?, ?)",
                ("C001", "Synthetic Customer One", 1000000),
            )
            conn.execute(
                "INSERT OR IGNORE INTO tickets(ticket_id, customer_id, message, requested_refund_cents) VALUES (?, ?, ?, ?)",
                ("T001", "C001", "Please refund my recent order.", 50000),
            )
            conn.execute(
                "INSERT OR IGNORE INTO saved_scenarios(scenario_id, name, expected_decision, customer_id, ticket_id, refund_amount_cents) VALUES (?, ?, ?, ?, ?, ?)",
                ("S_DENY_500", "High-value refund should be denied", "deny", "C001", "T001", 50000),
            )
            conn.execute(
                "INSERT OR IGNORE INTO saved_scenarios(scenario_id, name, expected_decision, customer_id, ticket_id, refund_amount_cents) VALUES (?, ?, ?, ?, ?, ?)",
                ("S_ALLOW_100", "Small permitted refund", "allow", "C001", "T001", 1000),
            )

def fetch_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
