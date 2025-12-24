from dataclasses import dataclass
from typing import Set

"""
@dataclass(frozen=True)

    Immutable by design
    Contracts should never change at runtime
    This prevents subtle bugs later
reads / writes
    These are abstract state keys, not variables.
        Examples:
            "db.users"
            "file.users_list.json"

They are names, not objects.
This abstraction is what enables dependency inference later.
"""

@dataclass(frozen=True)
class ToolContract:
    """
    Declarative description of a tool's interaction with state.
    This is NOT execution logic.
    """
    name: str

    # State this tool reads
    reads: Set[str]

    # State this tool writes / mutates
    writes: Set[str]

    # Safe to retry without changing outcome?
    idempotent: bool

    # Can run concurrently with same tool type?
    commutative: bool

    """Now we need shared vocabulary."""
    # ---- Canonical state identifiers ----

DB_USERS = "db.users"

FILE_SYSTEM = "file.system"

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
"""Lets examine one carefully.
create_user
reads = ∅
Does not depend on existing users to function
writes = {db.users}
Mutates the users table
idempotent = False - Re-running creates duplicates
commutative = True - Order of creates doesn’t matter
"""

# ---- File tool contracts ----

WRITE_FILE = ToolContract(
    name="write_file",
    reads=set(),
    writes={FILE_SYSTEM},
    idempotent=False,
    commutative=False,
)

READ_FILE = ToolContract(
    name="read_file",
    reads={FILE_SYSTEM},
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
        WRITE_FILE,
        READ_FILE,
    ]
}

#This gives us:
#contract = TOOL_CONTRACTS["create_user"]
# Optional: helper function to classify server
def get_server_for_tool(tool_name: str) -> str:
    if tool_name in {"create_user", "update_user", "delete_user", "list_users", "get_user_by_id"}:
        return "db"
    return "file"


