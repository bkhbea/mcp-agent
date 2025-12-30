from dataclasses import dataclass
from typing import Dict, Set, Type, Callable, Optional
from collections import namedtuple


@dataclass(frozen=True)
class ToolContract:
    """
    Declarative description of a tool's interaction with state.
    This is NOT execution logic.
    """
    name: str

    # State semantics
    reads: Set[str]
    writes: Set[str]

    idempotent: bool
    commutative: bool

    required_args: Dict[str, Type]
    optional_args: Dict[str, Type] = None

    # NEW: Dynamic state resolver
    # Allows reads/writes to be computed from arguments at runtime
    state_resolver: Optional[Callable[[Dict], Dict[str, Set[str]]]] = None


# =========================
# Canonical State Vocabulary
# =========================

DB_USERS = "db.users"

# NEW: File-level granularity (NOT directories)
FS_FILE_PREFIX = "fs.file:"


def fs_file_state(path: str) -> str:
    """
    NEW: Convert a file path into a canonical file state key.
    """
    return f"{FS_FILE_PREFIX}{path}"


# =========================
# Database Contracts
# =========================

CREATE_USER = ToolContract(
    name="create_user",
    reads=set(),
    writes={DB_USERS},
    idempotent=False,
    commutative=True,   # NEW: safe to parallelize
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
    required_args={"id": int},
)

DELETE_USER = ToolContract(
    name="delete_user",
    reads={DB_USERS},
    writes={DB_USERS},
    idempotent=False,
    commutative=False,
    required_args={"id": int},
)

LIST_USERS = ToolContract(
    name="list_users",
    reads={DB_USERS},
    writes=set(),
    idempotent=True,
    commutative=True,
    required_args={},
)

GET_USER_BY_ID = ToolContract(
    name="get_user_by_id",
    reads={DB_USERS},
    writes=set(),
    idempotent=True,
    commutative=True,
    required_args={"id": int},
)


# =========================
# File Tool Contracts
# =========================

# NEW: write_file dynamically depends on DB_USERS *if content references users*
def write_file_state_resolver(args: Dict) -> Dict[str, Set[str]]:
    """
    NEW:
    - Writes exactly ONE file
    - Reads db.users IF content originated from list_users
    """
    path = args["path"]
    content = args.get("content", "")

    reads = set()

    # NEW: Heuristic — writing derived user data requires db.users
    if "user" in content or "users" in content:
        reads.add(DB_USERS)

    return {
        "reads": reads,
        "writes": {fs_file_state(path)},
    }


WRITE_FILE = ToolContract(
    name="write_file",
    reads=set(),     # NEW: resolved dynamically
    writes=set(),    # NEW: resolved dynamically
    idempotent=True,
    commutative=False,   # NEW: two writes to same file must serialize
    required_args={
        "path": str,
        "content": str,
    },
    state_resolver=write_file_state_resolver,
)


# NEW: read_file depends on the last writer of the file
def read_file_state_resolver(args: Dict) -> Dict[str, Set[str]]:
    uri = args["uri"]
    path = uri.replace("file://", "").rstrip("/")

    return {
        "reads": {fs_file_state(path)},
        "writes": set(),
    }


READ_FILE = ToolContract(
    name="read_file",
    reads=set(),   # NEW: resolved dynamically
    writes=set(),
    idempotent=True,
    commutative=True,
    required_args={"uri": str},
    state_resolver=read_file_state_resolver,
)


# =========================
# Contract Registry
# =========================

TOOL_CONTRACTS = {
    c.name: c
    for c in [
        CREATE_USER,
        UPDATE_USER,
        DELETE_USER,
        LIST_USERS,
        GET_USER_BY_ID,
        WRITE_FILE,
        READ_FILE,
    ]
}
