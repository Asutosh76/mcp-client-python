import os
import traceback
from mcp import ClientSession, StdioServerParameters, stdio_client
from typing import Optional
from contextlib import AsyncExitStack
from anthropic import Anthropic
from log.logger import logger


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm = Anthropic()
        self.tools = []
        self.messages = []
        self.logger = logger

    # connect to the mcp server
    async def connect(self, server_script_path: str):
        # Logic to establish a connection to the server
        try:
            is_python = server_script_path.endswith('.py')
            is_js = server_script_path.endswith('.js')
            if not (is_python or is_js):
                raise ValueError("Server script must be a .py or .js file")
            
            command = "python" if is_python else "node"
            server_params = StdioServerParameters(command=command, args=[server_script_path], env = None)


            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

            await self.session.initialize()
            self.logger.info("Connected to MCP server successfully.")

            ms_tool = await self.get_mcp_tools()
            self.tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                } for tool in ms_tool
            ]

            self.logger.info(f"MCP available tools : {self.tools}")

        except Exception as e:
            self.logger.error(f"Failed to connect to MCP server: {e}")
            traceback.print_exc()
            raise

    # call a mcp tool

    # get a mcp tool list
    async def get_mcp_tools(self):
        try:
            if not self.session:
                raise RuntimeError("Not connected to MCP server.")
            tools = await self.session.get_tools()
            return tools
        except Exception as e:
            self.logger.error(f"Failed to get tools from MCP server: {e}")
            traceback.print_exc()
            raise

    # process query
    async def process_query(self, query: str):
        try:
            if not self.session:
                raise RuntimeError("Not connected to MCP server.")
            
            self.logger.info(f"Processing query: {query}")
            user_message = {"role": "user", "content": query}
            self.messages = [user_message]

            while True:
                response = await self.call_llm()
                # If response is having only text response
                if(response.content[0].type == "text" and len(response.content) == 1):
                    assistant_message = {
                        "role": "assistant", 
                        "content": response.content[0].text
                    }
                    self.messages.append(assistant_message)
                    break

                # If response is having tool call
                assistant_message = {
                    "role": "assistant",
                    "content": response.to_dict()["content"]
                }   
                self.messages.append(assistant_message)

                for content in response.content:
                    if content.type == "text":
                        self.messages.append({
                            "role": "assistant",
                            "content": content.text
                        })
                        
                    if(content.type == "tool_call"):
                        tool_name = content.name
                        tool_args = content.input
                        tool_use_id = content.id
                        self.logger.info(f"Invoking tool: {tool_name} with args: {tool_args}")

                        try:
                            tool_response = await self.session.call_tool(tool_name, tool_args)
                            self.logger.info(f"Tool {tool_name} response: {tool_response}")
                            self.messages.append({
                                "role": "tool",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_name": tool_name,
                                        "tool_use_id": tool_use_id,
                                        "content": tool_response.content
                                    }
                                ],
                            })
                        except Exception as e:
                            self.logger.error(f"Failed to call tool {tool_name}: {e}")
                            raise

                        
                       
                \        

            return self.messages
        
        except Exception as e:
            self.logger.error(f"Failed to process query: {e}")
            traceback.print_exc()
            raise
        

        # Here you would typically call the LLM with the query and tools

    # call the llm 
    async def call_llm(self):
        try:
            response = await self.llm.messages.create(
                model="claude-2",
                messages=self.messages,
                tools=self.tools,
                max_tokens=1000
            )
            self.logger.info(f"LLM response: {response}")
            return response
        except Exception as e:
            self.logger.error(f"Failed to call LLM: {e}")
            traceback.print_exc()
            raise

    # clean up resources
    async def cleanup(self):
        try:
            if self.session:
                await self.session.close()
        except Exception as e:
            self.logger.error(f"Failed to close session: {e}")
            traceback.print_exc()
        finally:
            await self.exit_stack.aclose()
            self.logger.info("Disconnected from MCP server.")

    # log conversation
