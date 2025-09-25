import logging
import sys

#Configure logging
logger = logging.getLogger('MCPClient')
logger.setLevel(logging.DEBUG)

# File handler with Debug level
file_handler = logging.FileHandler('mcp_client.log')
file_handler.setLevel(logging.DEBUG)

# Formatter for the log messages
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)


#Console handler with Info level
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

