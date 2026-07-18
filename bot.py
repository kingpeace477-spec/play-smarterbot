import os
import logging
import random
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Configuration ---
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN environment variable is not set!")
    print("Please set BOT_TOKEN in Railway Variables")
    exit(1)

print(f"✅ Bot token found: {BOT_TOKEN[:10]}... (length: {len(BOT_TOKEN)})")

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- Brain Training Data ---

# Memory Questions - User must recall information
MEMORY_QUESTIONS = [
    {
        "category": "Memory",
        "question": "What color was the sky in the previous message?",
        "options": ["Blue", "Green", "Red", "Yellow"],
        "answer": 0
    },
    {
        "category": "Memory",
        "question": "Which number was NOT shown in the sequence: 7, 14, 21, 28?",
        "options": ["7", "14", "21", "35"],
        "answer": 3
    }
]

# Logic Puzzles
LOGIC_QUESTIONS = [
    {
        "category": "Logic",
        "question": "If all Zips are Zaps, and all Zaps are Zops, are all Zips Zops?",
        "options": ["Yes", "No", "Maybe", "Cannot determine"],
        "answer": 0
    },
    {
        "category": "Logic",
        "question": "What comes next in the sequence: 2, 6, 12, 20, 30, ?",
        "options": ["40", "42", "44", "46"],
        "answer": 1
    }
]

# Quick Math Challenges
MATH_QUESTIONS = [
    {
        "category": "Speed",
        "question": "What is 7 × 8 + 6?",
        "options": ["56", "62", "66", "58"],
        "answer": 1
    },
    {
        "category": "Speed",
        "question": "What is 144 ÷ 12?",
        "options": ["10", "11", "12", "13"],
        "answer": 2
    }
]

# Pattern Recognition
PATTERN_QUESTIONS = [
    {
        "category": "Pattern",
        "question": "Which shape comes next? Triangle, Square, Pentagon, ?",
        "options": ["Hexagon", "Circle", "Octagon", "Star"],
        "answer": 0
    }
]

# Combine all questions
ALL_QUESTIONS = MEMORY_QUESTIONS + LOGIC_QUESTIONS + MATH_QUESTIONS + PATTERN_QUESTIONS

# --- User Data Structure ---
# In production, you'd use a database. This uses in-memory storage.
user_scores = {}
user_streaks = {}
user_last_active = {}

# --- Bot Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message explaining the bot's advanced features."""
    user = update.effective_user
    
    # Check if user has played before
    user_id = user.id
    if user_id in user_scores:
        last_active = user_last_active.get(user_id)
        streak = user_streaks.get(user_id, 0)
        
        # Check if streak is maintained (played within 24 hours)
        if last_active and (datetime.now() - last_active) < timedelta(hours=24):
            streak += 1
        else:
            streak = 0
        user_streaks[user_id] = streak
        
        welcome = (
            f"🧠 Welcome back to **Play Smarter**, {user.first_name}!\n\n"
            f"📊 Your stats:\n"
            f"• Total Score: {user_scores.get(user_id, 0)}\n"
            f"• Daily Streak: {streak} days 🔥\n\n"
            "Ready to train your brain? Click below to start!"
        )
    else:
        user_scores[user_id] = 0
        user_streaks[user_id] = 0
        welcome = (
            f"🧠 Welcome to **Play Smarter**, {user.first_name}!\n\n"
            "This bot is designed to train your brain with:\n"
            "• 🧩 Logic puzzles\n"
            "• 📝 Memory challenges\n"
            "• ⚡ Speed math\n"
            "• 🔍 Pattern recognition\n\n"
            "Start your brain training journey now!"
        )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Start Training", callback_data='start_training')],
        [InlineKeyboardButton("📊 My Stats", callback_data='show_stats')]
    ])
    
    await update.message.reply_text(
        welcome,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

async def start_training(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts a new training session with randomized questions."""
    query = update.callback_query
    await query.answer()
    
    # Initialize user session
    user_id = update.effective_user.id
    context.user_data['training_mode'] = True
    context.user_data['current_question'] = 0
    context.user_data['score'] = 0
    context.user_data['questions'] = random.sample(ALL_QUESTIONS, 5)  # 5 random questions
    context.user_data['start_time'] = time.time()
    
    await ask_question(update, context)

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the current question to the user."""
    questions = context.user_data.get('questions', [])
    current = context.user_data.get('current_question', 0)
    
    if current >= len(questions):
        # Training complete - show results
        await show_results(update, context)
        return
    
    q_data = questions[current]
    question_text = (
        f"🧠 **Training Session**\n"
        f"Question {current + 1} of {len(questions)}\n"
        f"Category: {q_data['category']}\n\n"
        f"{q_data['question']}"
    )
    
    # Create keyboard with options
    keyboard = []
    option_labels = ["A", "B", "C", "D"]
    for i, option in enumerate(q_data['options']):
        keyboard.append([
            InlineKeyboardButton(
                f"{option_labels[i]}. {option}",
                callback_data=f'train_answer_{i}'
            )
        ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send or edit message
    if update.callback_query:
        await update.callback_query.edit_message_text(
            question_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            question_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def handle_training_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes the user's answer and provides feedback."""
    query = update.callback_query
    await query.answer()
    
    # Parse answer
    selected_index = int(query.data.split('_')[2])
    current = context.user_data.get('current_question', 0)
    questions = context.user_data.get('questions', [])
    
    if current >= len(questions):
        await query.edit_message_text("Training complete! Use /start to play again.")
        return
    
    q_data = questions[current]
    correct_index = q_data['answer']
    
    # Check answer
    if selected_index == correct_index:
        context.user_data['score'] = context.user_data.get('score', 0) + 10
        feedback = f"✅ Correct! +10 points"
    else:
        feedback = f"❌ Incorrect. The answer was: {q_data['options'][correct_index]}"
    
    # Move to next question
    context.user_data['current_question'] = current + 1
    
    # Show feedback then next question
    await query.edit_message_text(
        f"{feedback}\n\n⏳ Loading next question..."
    )
    
    # Use a different approach to show next question
    # We'll send the next question directly without waiting for callback
    import asyncio
    await asyncio.sleep(1)  # Brief delay for user to read feedback
    
    # Reset callback to continue
    await ask_question(update, context)

async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the final results of the training session."""
    score = context.user_data.get('score', 0)
    total = len(context.user_data.get('questions', []))
    elapsed = time.time() - context.user_data.get('start_time', time.time())
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)
    
    # Calculate performance rating
    max_score = total * 10
    percentage = (score / max_score) * 100
    
    if percentage >= 90:
        rating = "🏆 Genius Level!"
        advice = "You're a brain training master!"
    elif percentage >= 70:
        rating = "🌟 Great Performance!"
        advice = "Keep practicing to reach genius level!"
    elif percentage >= 50:
        rating = "👍 Good Effort!"
        advice = "Focus on your weaker categories."
    else:
        rating = "📚 Keep Training!"
        advice = "Practice makes perfect! Try again."
    
    # Save stats
    user_id = update.effective_user.id
    user_scores[user_id] = user_scores.get(user_id, 0) + score
    user_last_active[user_id] = datetime.now()
    
    # Update streak
    streak = user_streaks.get(user_id, 0)
    if streak > 0:
        user_streaks[user_id] = streak + 1
    else:
        user_streaks[user_id] = 1
    
    results = (
        f"📊 **Training Complete!**\n\n"
        f"Score: {score} points\n"
        f"Time: {minutes}m {seconds}s\n"
        f"Rating: {rating}\n\n"
        f"{advice}\n\n"
        f"🔥 Daily Streak: {user_streaks.get(user_id, 0)} days\n"
        f"🏅 Total Score: {user_scores.get(user_id, 0)}\n\n"
        "🔄 Use /start to train again!"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            results,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(results, parse_mode='Markdown')

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the user's statistics."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    score = user_scores.get(user_id, 0)
    streak = user_streaks.get(user_id, 0)
    last_active = user_last_active.get(user_id)
    
    # Check if streak is still active
    if last_active and (datetime.now() - last_active) > timedelta(hours=24):
        streak = 0
    
    stats = (
        f"📊 **Your Brain Training Stats**\n\n"
        f"🏅 Total Score: {score} points\n"
        f"🔥 Current Streak: {streak} days\n"
        f"📅 Last Active: {last_active.strftime('%Y-%m-%d %H:%M') if last_active else 'Never'}\n\n"
        "💡 Tip: Train daily to maintain your streak!\n"
        "🎯 Use /start to begin a new session."
    )
    
    await query.edit_message_text(
        stats,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows help information."""
    help_text = (
        "🤖 **Play Smarter Bot Help**\n\n"
        "**Commands:**\n"
        "/start - Start the bot and see your stats\n"
        "/help - Show this help message\n"
        "/train - Start a training session\n"
        "/stats - View your statistics\n\n"
        "**Features:**\n"
        "🧠 Brain Training Exercises\n"
        "📊 Track your progress\n"
        "🔥 Daily Streaks\n"
        "🏆 Score System\n\n"
        "Train your brain every day to get smarter!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def train_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direct command to start training."""
    context.user_data['training_mode'] = True
    context.user_data['current_question'] = 0
    context.user_data['score'] = 0
    context.user_data['questions'] = random.sample(ALL_QUESTIONS, 5)
    context.user_data['start_time'] = time.time()
    await ask_question(update, context)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Direct command to show stats."""
    user_id = update.effective_user.id
    score = user_scores.get(user_id, 0)
    streak = user_streaks.get(user_id, 0)
    last_active = user_last_active.get(user_id)
    
    if last_active and (datetime.now() - last_active) > timedelta(hours=24):
        streak = 0
    
    stats = (
        f"📊 **Your Stats**\n\n"
        f"🏅 Total Score: {score}\n"
        f"🔥 Streak: {streak} days\n"
        f"📅 Last Active: {last_active.strftime('%Y-%m-%d %H:%M') if last_active else 'Never'}\n"
    )
    await update.message.reply_text(stats, parse_mode='Markdown')

# --- Main Application ---

def main():
    """Starts the bot."""
    print("🚀 Starting Play Smarter Bot...")
    print(f"🔑 Using token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("train", train_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(start_training, pattern='start_training'))
    application.add_handler(CallbackQueryHandler(show_stats, pattern='show_stats'))
    application.add_handler(CallbackQueryHandler(handle_training_answer, pattern='train_answer_'))
    
    print("✅ Bot is ready and listening for messages!")
    application.run_polling()

if __name__ == '__main__':
    main()
