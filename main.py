import os
from dotenv import load_dotenv
print("place holder to check git")

# Load variables from the .env file
load_dotenv(dotenv_path=".venv/.env")

# Retrieve the token safely
token = os.getenv("TEST")

print(token)  # Use your token with your API requests
