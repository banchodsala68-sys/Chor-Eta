import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API credentials
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Admin Telegram ID
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

# Bot Settings
BOT_NAME = "Premium Adult Content"
MINIMUM_AGE = 18
