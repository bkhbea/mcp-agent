def get_plan():
    plan = [
  {
    "id": "create_alice",
    "type": "tool",
    "server": "db",
    "tool": "create_user",
    "arguments": {
      "name": "Alice",
      "email": "alice@example.com"
    },
    "$from": []
  },
  {
    "id": "create_bob",
    "type": "tool",
    "server": "db",
    "tool": "create_user",
    "arguments": {
      "name": "Bob",
      "email": "bon@example.com"
    },
    "$from": []
  },
  {
    "id": "create_charlie",
    "type": "tool",
    "server": "db",
    "tool": "create_user",
    "arguments": {
      "name": "Charlie",
      "email": "chuck@example.com"
    },
    "$from": []
  },
  {
    "id": "write_alice_bob_file",
    "type": "tool",
    "server": "file",
    "tool": "write_file",
    "arguments": {
      "path": "bob_alice.txt",
      "content": {}
    },
    "$from": ["create_alice", "create_bob"]
  },
  {
    "id": "write_charlie_file",
    "type": "tool",
    "server": "file",
    "tool": "write_file",
    "arguments": {
      "path": "charlie.txt",
      "content": {}
    },
    "$from": "create_charlie"
  },
  {
    "id": "list_all_users",
    "type": "tool",
    "server": "db",
    "tool": "list_users",
    "arguments": {},
    "$from": ["create_alice", "create_bob", "create_charlie"]
  },
  {
    "id": "write_user_list_file",
    "type": "tool",
    "server": "file",
    "tool": "write_file",
    "arguments": {
      "path": "user_list.json",
      "content": {}
    },
    "$from": "list_all_users"
  },
  {
    "id": "read_user_list_file",
    "type": "resource",
    "server": "file",
    "tool": "read_file",
    "arguments": {
      "uri": "file://user_list.json/"
    },
    "$from": "write_user_list_file"
  }
]






    return plan