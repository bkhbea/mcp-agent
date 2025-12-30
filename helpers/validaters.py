from helpers.contracts import TOOL_CONTRACTS

def validate_step(step:dict):
    if "tool" not in step:
        raise ValueError(f"Missing 'tool' field: {step}")
    
    tool_name = step["tool"]
    print(f"Validating:{tool_name} against the contract")
    if tool_name not in TOOL_CONTRACTS:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    contract = TOOL_CONTRACTS[tool_name]
    args = step.get("arguments", {})  # <-- default empty dict, i.e. list_user
    if not isinstance(args, dict):
        raise ValueError(f"'arguments' must be an object for tool {tool_name}")
    
    # 1. Check required arguments
    for arg, arg_type in contract.required_args.items():
        if arg not in args:
            raise ValueError(
                f"Missing required argument '{arg}' for tool '{tool_name}'"
            )
        if not isinstance(args[arg], arg_type):
            raise ValueError(
                f"Argument '{arg}' for tool '{tool_name}' must be {arg_type.__name__}"
            )
        # 2. Check unexpected arguments
    allowed_args = set(contract.required_args.keys())
    if contract.optional_args:
        allowed_args |= set(contract.optional_args.keys())

    for arg in args:
        if arg not in allowed_args:
            raise ValueError(
                f"Unexpected argument '{arg}' for tool '{tool_name}'"
            )


    # Check arguments exist (optional deeper validation here)
    #if "arguments" not in step:
    #    raise ValueError(f"Missing arguments for tool: {tool_name}")

    # Further argument type validation could be added
    return True

def validate_plan(plan:list):
    if not isinstance(plan, list):
        raise ValueError("Plan must be a list")
    for i, step in enumerate(plan):
        if not isinstance(step, dict):
            raise ValueError(f"Step {i} is not an object")
    #for step in plan:
        validate_step(step)
    print("------- Plan is Valid -----")    
    return True
