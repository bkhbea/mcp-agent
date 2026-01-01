import re
from helpers.contracts import TOOL_CONTRACTS

VALID_SERVERS = {"db", "file"}
VALID_TYPES = {"tool", "resource"}
ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_step(step: dict, seen_ids: set):
    # ---------- Required top-level fields ----------
    for field in ("id", "type", "server", "tool", "arguments", "$from"):  # New: $from is now required
        if field not in step:
            raise ValueError(f"Missing '{field}' field: {step}")

    # ---------- id ----------
    step_id = step["id"]
    if not isinstance(step_id, str):
        raise ValueError(f"'id' must be a string: {step}")
    if not ID_PATTERN.match(step_id):
        raise ValueError(f"Invalid step id format: '{step_id}'")
    if step_id in seen_ids:
        raise ValueError(f"Duplicate step id: '{step_id}'")
    seen_ids.add(step_id)

    # ---------- type ----------
    step_type = step["type"]
    if step_type not in VALID_TYPES:
        raise ValueError(f"Invalid type '{step_type}' in step '{step_id}'")

    # ---------- server ----------
    server = step["server"]
    if server not in VALID_SERVERS:
        raise ValueError(f"Invalid server '{server}' in step '{step_id}'")

    # ---------- tool ----------
    tool_name = step["tool"]
    print(f"Validating: {tool_name} against the contract")

    if tool_name not in TOOL_CONTRACTS:
        raise ValueError(f"Unknown tool '{tool_name}' in step '{step_id}'")

    contract = TOOL_CONTRACTS[tool_name]

    # ---------- arguments ----------
    args = step["arguments"]
    if not isinstance(args, dict):
        raise ValueError(f"'arguments' must be an object in step '{step_id}'")

    # Required args
    for arg, arg_type in contract.required_args.items():
        if arg not in args:
            raise ValueError(
                f"Missing required argument '{arg}' for tool '{tool_name}'"
            )

        # Allow $from references inside argument values
        if isinstance(args[arg], dict) and "$from" in args[arg]:
            continue

        if not isinstance(args[arg], arg_type):
            raise ValueError(
                f"Argument '{arg}' for tool '{tool_name}' must be {arg_type.__name__}"
            )

    # Unexpected args
    allowed_args = set(contract.required_args.keys())
    if contract.optional_args:
        allowed_args |= set(contract.optional_args.keys())

    for arg in args:
        if arg not in allowed_args:
            raise ValueError(
                f"Unexpected argument '{arg}' for tool '{tool_name}'"
            )

    # ---------- $from validation (New) ----------
    from_field = step["$from"]
    if isinstance(from_field, str):
        from_list = [from_field] if from_field else []
    elif isinstance(from_field, list):
        from_list = from_field
    else:
        raise ValueError(f"'$from' must be a string or list in step '{step_id}'")

    for ref in from_list:
        if not isinstance(ref, str):
            raise ValueError(f"$from reference must be a string, got {type(ref)}")
    
    return True


def validate_plan(plan: list):
    if not isinstance(plan, list):
        raise ValueError("Plan must be a list")

    id_to_index = {step["id"]: i for i, step in enumerate(plan)}
    seen_ids = set()

    # First pass: validate structure & collect ids
    for i, step in enumerate(plan):
        if not isinstance(step, dict):
            raise ValueError(f"Step {i} is not an object")
        validate_step(step, seen_ids)

    # Second pass: validate $from references
    for i, step in enumerate(plan):
        step_id = step["id"]
        from_field = step["$from"]
        if isinstance(from_field, str):
            from_refs = [from_field] if from_field else []
        else:
            from_refs = from_field

        for ref in from_refs:
            # existence check
            if ref not in id_to_index:
                raise ValueError(
                    f"Unknown $from reference '{ref}' in step '{step_id}'"
                )
            # ordering check
            if id_to_index[ref] >= i:
                raise ValueError(
                    f"Step '{step_id}' references future step '{ref}'"
                )

        # New: enforce single vs multiple $from format
        if len(from_refs) == 0:
            pass  # empty list is OK
        elif len(from_refs) == 1 and not isinstance(from_field, str):
            raise ValueError(f"Single $from must be a string in step '{step_id}'")
        elif len(from_refs) > 1 and not isinstance(from_field, list):
            raise ValueError(f"Multiple $from must be a list in step '{step_id}'")

    print("------- Plan is Valid -----")
    return True
