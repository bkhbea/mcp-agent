from dataclasses import dataclass
from typing import Dict, Set, Type

@dataclass(frozen=True)
class ToolContract:
    """
    Declarative description of a tool's interaction with state.
    This is NOT execution logic.
    """
    name: str
    
    # State semantics
    # State this tool reads
    reads: Set[str]

    # State this tool writes / mutates
    writes: Set[str]

    # Safe to retry without changing outcome?
    idempotent: bool

    # Can run concurrently with same tool type?
    commutative: bool

    # NEW: argument schema
    required_args: Dict[str, Type]
    optional_args: Dict[str, Type] = None

    """Now we need shared vocabulary."""
    # ---- Canonical state identifiers ----

DB_USERS = "db.users"



# ---- Database tool contracts ----

CREATE_USER = ToolContract(
    name="create_user",
    reads=set(),
    writes={DB_USERS},
    idempotent=False,
    commutative=True,
    required_args={
        "name": str,
        "email": str,
    },
)

UPDATE_USER = ToolContract(
    name="update_user",
    reads={DB_USERS},
    writes={DB_USERS},
    idempotent=False,
    commutative=False,
    required_args={
        "id" : int,
    }
)

DELETE_USER = ToolContract(
    name="delete_user",
    reads={DB_USERS},
    writes={DB_USERS},
    idempotent=False,
    commutative=False,
    required_args={
        "id" : int,
    }
)

LIST_USERS = ToolContract(
    name="list_users",
    reads={DB_USERS},
    writes=set(),
    idempotent=True,
    commutative=True,
    required_args={},  # ← explicitly empty
)

GET_USER_BY_ID = ToolContract(
    name="get_user_by_id",
    reads={DB_USERS},
    writes=set(),
    idempotent=True,
    commutative=True,
    required_args={
        "id" : int,
    }
)   
# ---- Contract registry ----

TOOL_CONTRACTS = {
    c.name: c
    for c in [
        CREATE_USER,
        UPDATE_USER,
        DELETE_USER,
        LIST_USERS,
		GET_USER_BY_ID
    ]
}