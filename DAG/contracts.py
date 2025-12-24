# DAG/contracts.py
from dataclasses import dataclass
from typing import Set

@dataclass(frozen=True)
class ToolContract:
    """
    Declarative description of a tool's interaction with state.
    This is NOT execution logic.
    """
    name: str
    reads: Set[str]
    writes: Set[str]
    idempotent: bool
    commutative: bool


# ---- Canonical state identifiers ----
DB_USERS = "db.users"


# ---- Database tool contracts ----

CREATE_USER = ToolContract(
    name="create_user",
    reads=set(),
    writes={DB_USERS},
    idempotent=False,
    commutative=True,
)

UPDATE_USER = ToolContract(
    name="update_user",
    reads={DB_USERS},
    writes={DB_USERS},
    idempotent=False,
    commutative=False,
)

DELETE_USER = ToolContract(
    name="delete_user",
    reads={DB_USERS},
    writes={DB_USERS},
    idempotent=False,
    commutative=False,
)

LIST_USERS = ToolContract(
    name="list_users",
    reads={DB_USERS},
    writes=set(),
    idempotent=True,
    commutative=True,
)

GET_USER_BY_ID = ToolContract(
    name="get_user_by_id",
    reads={DB_USERS},
    writes=set(),
    idempotent=True,
    commutative=True,
)

# ---- Contract registry ----

TOOL_CONTRACTS = {
    c.name: c
    for c in [
        CREATE_USER,
        UPDATE_USER,
        DELETE_USER,
        LIST_USERS,
        GET_USER_BY_ID,
    ]
}
