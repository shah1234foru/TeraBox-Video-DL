import os
import re
import requests
import telebot
from time import time, sleep
from flask import Flask, jsonify
from threading import Thread
import pymongo
from datetime import datetime, timedelta

# DB Connection
mongo_client = pymongo.MongoClient(os.getenv('mongodb+srv://ankitpatni95:ankitpatni95@cluster0.jberr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'))
db = mongo_client['powerful_web_scraping_tool_bot']
users_collection = db['users']
banned_users_collection = db['banned_users']
print('DB Connected')

# Bot Connection
bot = telebot.TeleBot(os.getenv('BOT_TOKEN'))
print(f"@{bot.get_me().username} Connected")
print("\n╭─── [ LOG ]")
app = Flask(__name__)

# Channel ID
CHANNEL_ID = '-1002363544218'  # Replace with your channel ID

# Dictionary to store invite links and their expiration times
invite_links = {}

# Functions
# Fetch User Member or Not
def is_member(user_id):
    try:
        member_status = bot.get_chat_member(CHANNEL_ID, user_id)
        return member_status.status in ['member', 'administrator', 'creator']
    except:
        return False

# Function to generate an invite link
def generate_invite_link():
    expire_date = datetime.now() + timedelta(minutes=5)
    invite_link = bot.create_chat_invite_link(CHANNEL_ID, expire_date.timestamp(), member_limit=1)
    return invite_link.invite_link

# Function to delete an invite link
def delete_invite_link(invite_link):
    bot.delete_chat_invite_link(CHANNEL_ID, invite_link)

# Function to format the progress bar
def format_progress_bar(filename, percentage, done, total_size, status, speed, user_mention, user_id):
    bar_length = 10
    filled_length = int(bar_length * percentage / 100)
    bar = '⬤' * filled_length + '⊙' * (bar_length - filled_length)

    def format_size(size):
        size = int(size)
        if size < 1024:
            return f"{size} B"
        elif size < 1024 ** 2:
            return f"{size / 1024:.2f} KB"
        elif size < 1024 ** 3:
            return f"{size / 1024 ** 2:.2f} MB"
        else:
            return f"{size / 1024 ** 3:.2f} GB"

    return (
        f"┏ 𝐅𝐢𝐥𝐞𝐍𝐚𝐦𝐞: <b>{filename}</b>\n"
        f"┠ [{bar}] {percentage:.2f}%\n"
        f"┠ 𝐏𝐫𝐨𝐜𝐞𝐬𝐬𝐞𝐝: {format_size(done)} ᴏғ {format_size(total_size)}\n"
        f"┠ 𝐒𝐭𝐚𝐭𝐮𝐬: <b>{status}</b>\n"
        f"┠ 𝐒𝐩𝐞𝐞𝐝: <b>{format_size(speed)}/s</b>\n"
        f"┖ 𝐔𝐬𝐞𝐫: {user_mention} | ɪᴅ: <code>{user_id}</code>"
    )

# Function to download video
def download_video(url, chat_id, message_id, user_mention, user_id):
    response = requests.get(f'https://teraboxvideodownloader.nepcoderdevs.workers.dev/?url={url}')
    data = response.json()

    if not data['response'] or len(data['response']) == 0:
        raise Exception('No response data found')

    resolutions = data['response'][0]['resolutions']
    fast_download_link = resolutions['Fast Download']
    video_title = re.sub(r'[<>:"/\\|?*]+', '', data['response'][0]['title'])
    video_path = os.path.join('Videos', f"{video_title}.mp4")

    with open(video_path, 'wb') as video_file:
        video_response = requests.get(fast_download_link, stream=True)

        total_length = video_response.headers.get('content-length')
        if total_length is None:  # no content length header
            video_file.write(video_response.content)
        else:
            downloaded_length = 0
            total_length = int(total_length)
            start_time = time()
            last_percentage_update = 0
            for chunk in video_response.iter_content(chunk_size=4096):
                downloaded_length += len(chunk)
                video_file.write(chunk)
                elapsed_time = time() - start_time
                percentage = 100 * downloaded_length / total_length
                speed = downloaded_length / elapsed_time

                if percentage - last_percentage_update >= 7:  # update every 7%
                    progress = format_progress_bar(
                        video_title,
                        percentage,
                        downloaded_length,
                        total_length,
                        'Downloading',
                        speed,
                        user_mention,
                        user_id
                    )
                    bot.edit_message_text(progress, chat_id, message_id, parse_mode='HTML')
                    last_percentage_update = percentage

    return video_path, video_title, total_length

# Start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user

    bot.send_chat_action(message.chat.id, 'typing')

    # Store User To DB
    if not users_collection.find_one({'user_id': user.id}):
        users_collection.insert_one({
            'user_id': user.id,
            'first_name': user.first_name,
            'downloads': 0
        })

    inline_keyboard = telebot.types.InlineKeyboardMarkup()
    inline_keyboard.row(
        telebot.types.InlineKeyboardButton("🫧 Naruto 🫧", url="https://telegram.me/Naruto_Owner_bot")
    )

    welcome_message = (
        f"ᴡᴇʟᴄᴏᴍᴇ, <a href='tg://user?id={user.id}'>{user.first_name}</a>.\n\n"
        "🔄 ɪ ᴀᴍ ᴀ ᴛᴇʀᴀʙᴏx ᴅᴏᴡɴʟᴏᴀᴅᴇʀ ʙᴏᴛ.\n"
        "sᴇɴᴅ ᴍᴇ ᴀɴʏ ᴛᴇʀᴀʙᴏx ʟɪɴᴋ ɪ ᴡɪʟʟ ᴅᴏᴡɴʟᴏᴀᴅ ᴡɪᴛʜɪɴ ғᴇᴡ sᴇᴄᴏɴᴅs\n"
        "ᴀɴᴅ sᴇɴᴅ ɪᴛ ᴛᴏ ʏᴏᴜ ✨"
    )

    # Send the welcome photo first
    bot.send_photo(
        message.chat.id,
        photo="https://envs.sh/tJZ.jpg",
        caption=welcome_message,
        parse_mode='HTML',
        reply_markup=inline_keyboard
    )

# Handle messages
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user = message.from_user

    # Ignore
    if message.text.startswith('/'):
        return

    bot.send_chat_action(message.chat.id, 'typing')

    # Check if user is banned
    if banned_users_collection.find_one({'user_id': user.id}):
        bot.send_message(message.chat.id, "You are banned from using this bot.")
        return

    # Check User Member or Not
    if not is_member(user.id):
        # Generate a new invite link
        invite_link = generate_invite_link()
        invite_links[user.id] = invite_link

        # Send the invite link to the user
        bot.send_message(
            message.chat.id,
            "ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ ᴍʏ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴜsᴇ ᴍᴇ.",
            reply_markup=telebot.types.InlineKeyboardMarkup().add(
                telebot.types.InlineKeyboardButton("〇 𝐉𝐨𝐢𝐧𝐞 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 〇", url=invite_link)
            )
        )

        # Schedule the deletion of the invite link after 5 minutes
        def delete_link_after_5_minutes(user_id, invite_link):
            sleep(300)  # 5 minutes
            if user_id in invite_links:
                delete_invite_link(invite_link)
                del invite_links[user_id]

        Thread(target=delete_link_after_5_minutes, args=(user.id, invite_link)).start()
        return

    video_url = message.text
    chat_id = message.chat.id
    user_mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
    user_id = user.id

    if re.match(r'http[s]?://.*tera', video_url):
        progress_msg = bot.send_message(chat_id, '⎋ ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ʏᴏᴜʀ ᴠɪᴅᴇᴏ...')
        try:
            video_path, video_title, video_size = download_video(video_url, chat_id, progress_msg.message_id, user_mention, user_id)
            bot.edit_message_text('sᴇɴᴅɪɴɢ ʏᴏᴜ ᴛʜᴇ ᴍᴇᴅɪᴀ...🤤', chat_id, progress_msg.message_id)

            video_size_mb = video_size / (1024 * 1024)

            dump_channel_video = bot.send_video(os.getenv('DUMP_CHAT_ID'), open(video_path, 'rb'), caption=f"📂 {video_title}\n📦 {video_size_mb:.2f} MB\n🪪 𝐔𝐬𝐞𝐫 𝐁𝐲 : {user_mention}\n♂️ 𝐔𝐬𝐞𝐫 𝐋𝐢𝐧𝐤: tg://user?id={user_id}", parse_mode='HTML')
            bot.copy_message(chat_id, os.getenv('DUMP_CHAT_ID'), dump_channel_video.message_id)

            bot.send_sticker(chat_id, "CAACAgIAAxkBAAEM0yZm6Xz0hczRb-S5YkRIck7cjvQyNQACCh0AAsGoIEkIjTf-YvDReDYE")
            users_collection.update_one(
                {'user_id': user.id},
                {'$inc': {'downloads': 1}},
                upsert=True
            )
            bot.delete_message(chat_id, progress_msg.message_id)
            bot.delete_message(chat_id, message.message_id)
            os.remove(video_path)
        except Exception as e:
            bot.edit_message_text(f'Download failed: {str(e)}', chat_id, progress_msg.message_id)
    else:
        bot.send_message(chat_id, 'ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴀ ᴠᴀʟɪᴅ ᴛᴇʀᴀʙᴏx ʟɪɴᴋ.')

# Home
@app.route('/')
def index():
    return 'Bot Is Alive'

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify(status='OK'), 200

if __name__ == "__main__":
    # Start Flask app in a separate thread
    def run_flask():
        app.run(host='0.0.0.0', port=8000)

    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # Start polling for Telegram updates
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Error in bot polling: {str(e)}")
