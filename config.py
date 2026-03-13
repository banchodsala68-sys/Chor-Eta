import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API credentials
API_ID = os.getenv('27099161')
API_HASH = os.getenv('4ebbba630c8da1e27875ba399ae78a7f')
BOT_TOKEN = os.getenv('7907973008:AAH6M39DXNRS8O0auaZbwFH7wkT19AC5Gw8')

# Admin Telegram ID
ADMIN_ID = int(os.getenv('5340147496', '0'))

# Bot Settings
BOT_NAME = "Premium Adult Content"
MINIMUM_AGE = 18
