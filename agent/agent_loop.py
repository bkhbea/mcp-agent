import asyncio
import json

from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

# ----------------- Database server parameters -----------------
DB_PARAMS = StdioServerParameters(
    name="db",
    command="python3",
    args=["servers/updated_db_server.py"]
)
# ----------------- File server parameters -----------------
FILE_PARAMS = StdioServerParameters(
    name="file",
    command="python3",
    args=["servers/file_server.py"]
)
# ------------------- DB SERVER -------------------
async def main():
    print("STEP 1: entering stdio_client context")
    async with stdio_client(DB_PARAMS) as (reader, writer):
        print("STEP 2: stdio_client entered (server started)")
        print("STEP 3: entering ClientSession context")
        async with ClientSession(reader, writer) as session:
            print("STEP 4: ClientSession entered")
            metadata = await session.initialize()
            print(f"Meta_data: {metadata}")
            print()
            print("STEP 5: session initialized")
            result = await session.call_tool("list_users", arguments={"query": "SELECT * FROM users"})
            #user = await session.call_tool("get_user_by_id", arguments={"id": 2})
            #print(f"User; {user}")
            if result.isError:
              # Handle the error explicitly
              print("Server-side error:", result.content[0].text)
            else:
              print("STEP 6: tool call completed")
              print("Result contents:", result.content)
        print("STEP 7: exited ClientSession context")    
    print("STEP 8: exited stdio_client context (server stopped)")
            # MCP always returns a list of content blocks
    print(f"\nObservation: Found {len(result.content)} users in DB\n")
    for i in range (len(result.content)):
        rows = json.loads(result.content[i].text)
        print(json.dumps(rows, indent=2))

 # ------------------- FILE SERVER -------------------
    print("\nSTEP 9: entering stdio_client context for file server")
    async with stdio_client(FILE_PARAMS) as (file_reader, file_writer):
        print("STEP 10: stdio_client for file server entered")
        async with ClientSession(file_reader, file_writer) as file_session:
            print("STEP 11: ClientSession for file server entered")
            await file_session.initialize()
            print("STEP 12: file server session initialized")
            # Read a file resource (adjust path as needed)
            file_path = "readme.txt"
            file_blocks = await file_session.read_resource(f"file://{file_path}")
            print("STEP 13: file resource read completed")
            print("\nFile Content Preview :")
            contents_list = None
            for key, value in file_blocks:
              if key == 'contents':
                contents_list = value
            if contents_list:
               for block in contents_list:
                  print(block.text)    
            else:
               print("No file contents returned")
        print("STEP 14: exited ClientSession for file server")    
    print("STEP 15: exited stdio_client context for file server (server stopped)")            

if __name__ == "__main__":
    asyncio.run(main())

# Breakdown:
#------------- Transport-level setup------------
# 1.stdio_client(...)
    #Spawns the server process
    #Creates pipes
        #agent → server (stdin)
        #server → agent (stdout)
    #Exposes them as:
        # reader, writer

#----------- Protocol-level setup.---------
# 2. ClientSession(reader, writer)
    #Wraps those pipes in:
        #JSON-RPC framing
        #Request/response correlation
        #Background task group         
    #Manages:
        #Tool calls
        #Resource reads
        #Notifications    

#---------- handshake & discovery ------
# 3. await session.initialize()
    #Sends an MCP initialize request
    #Server responds with:
        #Available tools
        #Resources
        #Capabilities
    #Session caches this metadata 

#----------- agent action → environment effect → observation-----------
# 4. session.call_tool("query_db", ...)
    #Agent sends:
        #{
        #    "method": "tools/call",
        #     "params": { ... }
        #}
    #Server executes:
        #cursor.execute(query)
    #Server returns structured content
    #Agent receives and processes it  
    
