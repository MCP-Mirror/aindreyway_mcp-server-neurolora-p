import json
import time

# Initialize request
init_request = {
    "jsonrpc": "2.0",
    "method": "initialize",
    "id": 1,
    "params": {
        "name": "test-client",
        "version": "1.0.0",
        "capabilities": {},
        "protocolVersion": "1.0",
        "clientInfo": {"name": "test", "version": "1.0"},
    },
}

# Send initialize request and wait for response
print(json.dumps(init_request), flush=True)
time.sleep(3)  # Wait longer for initialization

# List tools request
list_tools_request = {"jsonrpc": "2.0", "method": "tools/list", "id": 2}
print(json.dumps(list_tools_request), flush=True)

# Keep the script running to receive responses
time.sleep(3)
