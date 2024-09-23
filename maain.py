from pyrogram import Client, filters
from pyrogram.types import Message
import pymongo
from datetime import datetime
import random
import string
import openai

# MongoDB setup using your provided URI
client = pymongo.MongoClient("mongodb+srv://AskIQ:AskIQ@cluster0.z0asv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["askiq_db"]
users_col = db["users"]
redeem_codes_col = db["redeem_codes"]
conversations_col = db["conversations"]
blocked_users_col = db["blocked_users"]

# Telegram Bot setup with provided API credentials
app = Client(
    "AskIQ_Bot",
    api_id=28731539,
    api_hash="7501dd35f99436e403118ac545d50b4b",
    bot_token="7054201917:AAHdcScMDGs0OuRpwygitBbgOv2I_u5kRQ4"
)

# OpenAI API Setup
openai.api_key = "o_BR777t.CAVlZfYgFOzhOYi_mw87V"  # Replace with your actual secret key
openai.api_base = "https://cloud.olakrutrim.com/v1"  # Krutrim API endpoint

# Constants
OWNER_ID = 7005020577
LOG_CHANNEL_USERNAME = "@loggerxnnk"  # Use your channel's username

# Helper function to check if user is blocked
def is_user_blocked(user_id):
    return blocked_users_col.find_one({"user_id": user_id}) is not None

# Helper function to check if user is Pro
def is_user_pro(user_id):
    user = users_col.find_one({"user_id": user_id})
    return user and user.get("pro", False)

# Helper function to log messages and responses to a log channel
async def log_to_channel(bot: Client, user_name: str, user_id: int, command: str, response: str):
    log_message = (
        f"UserName: {user_name}\n"
        f"UserID: {user_id}\n"
        f"Command: {command}\n"
        f"Response: {response}\n"
    )
    try:
        await bot.send_message(chat_id=LOG_CHANNEL_USERNAME, text=log_message)
    except Exception as e:
        print(f"Failed to send log message: {e}")

# Function to call OpenAI API and get a response
async def call_openai_api(user_question):
    try:
        chat_completion = openai.ChatCompletion.create(
            model="Meta-Llama-3-8B-Instruct",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_question}
            ],
            max_tokens=8000,
            temperature=0.7,
        )
        answer = chat_completion.choices[0].message['content']
        return answer
    except Exception as e:
        return f"An error occurred: {e}"

# /start command
@app.on_message(filters.command("start"))
async def start(bot: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name

    if is_user_blocked(user_id):
        response = "You are blocked from using this bot."
        await message.reply(response)
        await log_to_channel(bot, user_name, user_id, "/start", response)
        return

    user = users_col.find_one({"user_id": user_id})
    
    if not user:
        users_col.insert_one({"user_id": user_id, "credits": 5, "joined": datetime.utcnow()})
    
    conversations_col.delete_many({"user_id": user_id})

    response = ("Welcome to Ask IQ! 🤖 Your smart companion for quick answers and insights. "
                "Whether it’s a tricky problem or a curious question, I’m here to help. "
                "Just ask, and let’s unlock knowledge together! 🚀")
    await message.reply(response)
    await log_to_channel(bot, user_name, user_id, "/start", response)

# /ask command
@app.on_message(filters.command("ask"))
async def ask_command(bot: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name
    user_question = ' '.join(message.command[1:])

    # Check if user is blocked
    if is_user_blocked(user_id):
        response = "You are blocked from using this bot."
        await message.reply(response)
        await log_to_channel(bot, user_name, user_id, "/ask", response)
        return

    # Validate the question
    if not user_question:
        response = "Please provide a question to ask."
        await message.reply(response)
        return

    # Check user credits
    user = users_col.find_one({"user_id": user_id})
    if user and (is_user_pro(user_id) or user["credits"] > 0):
        # Send initial heart emoji
        sent_message = await message.reply("❤️")

        # Call the OpenAI API with the user's question
        openai_response = await call_openai_api(user_question)

        # Edit the original heart emoji message with the actual response
        await sent_message.edit_text(openai_response)

        # Decrement user credits if not Pro
        if not is_user_pro(user_id):
            users_col.update_one({"user_id": user_id}, {"$inc": {"credits": -1}})
        await log_to_channel(bot, user_name, user_id, "/ask", openai_response)
    else:
        response = "Your credits are exhausted. Contact @AskIQSupport to upgrade to premium."
        await message.reply(response)
        await log_to_channel(bot, user_name, user_id, "/ask", response)

# /clear command
@app.on_message(filters.command("clear"))
async def clear_conversation(bot: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name

    if is_user_blocked(user_id):
        response = "You are blocked from using this bot."
        await message.reply(response)
        await log_to_channel(bot, user_name, user_id, "/clear", response)
        return

    conversations_col.delete_many({"user_id": user_id})

    response = "Your conversation history has been cleared. Let's start fresh! 🚀"
    await message.reply(response)
    await log_to_channel(bot, user_name, user_id, "/clear", response)

# /help command
@app.on_message(filters.command("help"))
async def help_command(bot: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name

    if user_id == OWNER_ID:
        help_text = (
            "👋 Ask IQ Bot Help\n\n"
            "Here are all available commands:\n\n"
            "/start - Register and start using the bot\n"
            "/ask <question> - Ask a question and get an answer\n"
            "/clear - Clear your conversation history\n"
            "/credits - Check your current credits\n"
            "/gen - Generate a redeem code (owner only)\n"
            "/stats - View bot statistics (owner only)\n"
            "/broadcast <message> - Send a broadcast message to all users (owner only)\n"
            "/bblock <user_id> - Block a user from the bot (owner only)\n"
            "/unblock <user_id> - Unblock a user (owner only)\n"
            "/subscription - Check your subscription status and credits\n"
            "/addpre <id or username> - Add a user to Pro status (owner only)\n"
        )
    else:
        help_text = (
            "👋 Ask IQ Bot Help\n\n"
            "Here are the available commands for you:\n\n"
            "/start - Register and start using the bot\n"
            "/ask <question> - Ask a question and get an answer\n"
            "/clear - Clear your conversation history\n"
            "/credits - Check your current credits\n"
            "/subscription - Check your subscription status and credits\n"
        )

    await message.reply(help_text)
    await log_to_channel(bot, user_name, user_id, "/help", help_text)

# /credits command
@app.on_message(filters.command("credits"))
async def credits_command(bot: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name
    user = users_col.find_one({"user_id": user_id})

    if is_user_blocked(user_id):
        response = "You are blocked from using this bot."
        await message.reply(response)
        await log_to_channel(bot, user_name, user_id, "/credits", response)
        return

    credits = user["credits"] if user else 0
    response = f"Your current credits are: {credits}"
    await message.reply(response)
    await log_to_channel(bot, user_name, user_id, "/credits", response)

# /gen command (Owner-only)
@app.on_message(filters.command("gen"))
async def gen_command(bot: Client, message: Message):
    user_id = message.from_user.id

    if user_id != OWNER_ID:
        response = "You are not authorized to use this command."
        await message.reply(response)
        return

    code = "Pragal" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    redeem_codes_col.insert_one({"code": code, "status": "unused"})
    response = f"Generated redeem code: {code}"
    await message.reply(response)
    await log_to_channel(bot, "Bot Owner", user_id, "/gen", response)

# Redeem command
@app.on_message(filters.command("redeem"))
async def redeem_command(bot: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name

    if is_user_blocked(user_id):
        response = "You are blocked from using this bot."
        await message.reply(response)
        await log_to_channel(bot, user_name, user_id, "/redeem", response)
        return

    code = ' '.join(message.command[1:]).strip()
    if not code:
        response = "Please provide a redeem code."
        await message.reply(response)
        return

    redeem_code_entry = redeem_codes_col.find_one({"code": code, "status": "unused"})
    if redeem_code_entry:
        users_col.update_one({"user_id": user_id}, {"$inc": {"credits": 30}})
        redeem_codes_col.update_one({"code": code}, {"$set": {"status": "used"}})
        response = "Redeem code applied! You have received 30 credits."
    else:
        response = "Invalid or already used redeem code."

    await message.reply(response)
    await log_to_channel(bot, user_name, user_id, "/redeem", response)

# /stats command (Owner-only)
@app.on_message(filters.command("stats"))
async def stats_command(bot: Client, message: Message):
    user_id = message.from_user.id

    if user_id != OWNER_ID:
        response = "You are not authorized to use this command."
        await message.reply(response)
        return

    user_count = users_col.count_documents({})
    response = f"Total users: {user_count}"
    await message.reply(response)
    await log_to_channel(bot, "Bot Owner", user_id, "/stats", response)

# /broadcast command (Owner-only)
@app.on_message(filters.command("broadcast"))
async def broadcast_command(bot: Client, message: Message):
    user_id = message.from_user.id

    if user_id != OWNER_ID:
        response = "You are not authorized to use this command."
        await message.reply(response)
        return

    broadcast_message = ' '.join(message.command[1:])
    if not broadcast_message:
        response = "Please provide a message to broadcast."
        await message.reply(response)
        return

    users = users_col.find({})
    for user in users:
        try:
            await bot.send_message(user["user_id"], broadcast_message)
        except Exception as e:
            print(f"Failed to send broadcast message to user {user['user_id']}: {e}")

    response = "Broadcast message sent to all users."
    await message.reply(response)
    await log_to_channel(bot, "Bot Owner", user_id, "/broadcast", response)

# /bblock command (Owner-only)
@app.on_message(filters.command("bblock"))
async def block_user_command(bot: Client, message: Message):
    user_id = message.from_user.id

    if user_id != OWNER_ID:
        response = "You are not authorized to use this command."
        await message.reply(response)
        return

    target_id = int(message.command[1]) if len(message.command) > 1 else None
    if not target_id:
        response = "Please provide a user ID to block."
        await message.reply(response)
        return

    blocked_users_col.insert_one({"user_id": target_id})
    response = f"User with ID {target_id} has been blocked."
    await message.reply(response)
    await log_to_channel(bot, "Bot Owner", user_id, "/bblock", response)

# /unblock command (Owner-only)
@app.on_message(filters.command("unblock"))
async def unblock_user_command(bot: Client, message: Message):
    user_id = message.from_user.id

    if user_id != OWNER_ID:
        response = "You are not authorized to use this command."
        await message.reply(response)
        return

    target_id = int(message.command[1]) if len(message.command) > 1 else None
    if not target_id:
        response = "Please provide a user ID to unblock."
        await message.reply(response)
        return

    blocked_users_col.delete_one({"user_id": target_id})
    response = f"User with ID {target_id} has been unblocked."
    await message.reply(response)
    await log_to_channel(bot, "Bot Owner", user_id, "/unblock", response)

# /subscription command
@app.on_message(filters.command("subscription"))
async def subscription_command(bot: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name
    user = users_col.find_one({"user_id": user_id})

    if is_user_blocked(user_id):
        response = "You are blocked from using this bot."
        await message.reply(response)
        await log_to_channel(bot, user_name, user_id, "/subscription", response)
        return

    if user:
        subscription_status = "Pro" if is_user_pro(user_id) else "Free"
        credits = user.get("credits", 0)
        response = f"Subscription Status: {subscription_status}\nCredits: {credits}"
    else:
        response = "User not found. Please start the bot with /start command first."
        
    await message.reply(response)
    await log_to_channel(bot, user_name, user_id, "/subscription", response)

@app.on_message(filters.command("addpre"))
async def add_pre_command(bot: Client, message: Message):
    user_id = message.from_user.id

    # Check if the user is the owner
    if user_id != OWNER_ID:
        response = "You are not authorized to use this command."
        await message.reply(response)
        return

    # Check if the command is a reply
    if not message.reply_to_message or not message.reply_to_message.from_user:
        response = "Please reply to the message of the user you want to promote."
        await message.reply(response)
        return

    target_user = message.reply_to_message.from_user
    user_id_to_promote = target_user.id
    user = users_col.find_one({"user_id": user_id_to_promote})

    # Promote the user if found
    if user:
        users_col.update_one(
            {"user_id": user["user_id"]}, 
            {"$set": {"pro": True, "credits": float('Infinity')}}
        )
        response = f"User {target_user.username or target_user.id} has been promoted to Pro status."
        
        # Notify the user about their promotion
        try:
            await bot.send_message(
                user_id_to_promote, 
                "Congratulations! 🎉 You have been promoted to premium Pro status. Enjoy unlimited questions and other benefits!"
            )
        except Exception as e:
            print(f"Failed to notify user {user_id_to_promote} about promotion: {e}")
    else:
        response = f"User {target_user.username or target_user.id} not found."

    await message.reply(response)
    await log_to_channel(bot, "Bot Owner", user_id, "/addpre", response)
import aiohttp  # Ensure you have aiohttp installed
from pyrogram import Client, filters
from pyrogram.types import Message
from krutrim_cloud import KrutrimCloud
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from a .env file

# Initialize the KrutrimCloud client
client = KrutrimCloud()
model_name = "Gemma-2-27B-IT"

@app.on_message(filters.command("query"))
async def query_command(bot: Client, message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name
    user_question = ' '.join(message.command[1:])

    # Check if the user is blocked
    if is_user_blocked(user_id):
        response = "You are blocked from using this bot."
        await message.reply(response)
        await log_to_channel(bot, user_name, user_id, "/query", response)
        return

    # Check if the user provided a question
    if not user_question:
        response = "Please provide a question for the query."
        await message.reply(response)
        return

    # Check user credits
    user = users_col.find_one({"user_id": user_id})
    if user and not is_user_pro(user_id) and user["credits"] <= 0:
        response = "Your credits are exhausted. Contact @AskIQSupport to upgrade to premium."
        await message.reply(response)
        await log_to_channel(bot, user_name, user_id, "/query", response)
        return

    # Notify user that the bot is processing the query
    sent_message = await message.reply("💭 Thinking...")

    # Prepare the messages for the API
    messages = [
        {
            "role": "user",
            "content": user_question,
        },
    ]

    try:
        # Make the API call with max_tokens
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            max_tokens=4096  # Add max_tokens parameter here
        )

        # Access generated output
        query_response = response.choices[0].message.content  # type:ignore

    except Exception as exc:
        query_response = "An error occurred. Contact @AskIQSupport."
        await log_to_channel(bot, user_name, user_id, "/query", f"Error: {str(exc)}")

    # Edit the response with the generated content
    await sent_message.edit_text(query_response)
    await log_to_channel(bot, user_name, user_id, "/query", query_response)

# Start the bot
app.run()

