# bot.py
import os
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# ---------- Bot Token ----------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not found! Add it in your environment variables.")
    exit(1)

DATA_DIR = "data"  # Folder where background worker saves charts and CSVs

# ---------- /start command ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Gamma Exposure", callback_data="gamma")],
        [InlineKeyboardButton("Charts", callback_data="chart")],
        [InlineKeyboardButton("Max Pain Point", callback_data="maxpain")],
        [InlineKeyboardButton("Daily Volume", callback_data="dailyvolume")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Hello! 👋\n\n"
        "I can show SPX options analysis. Choose an option below or use commands:\n"
        "/spx_gamma\n/chart\n/maxpain\n/daily_volume",
        reply_markup=reply_markup
    )

# ---------- /spx_gamma command ----------
async def spx_gamma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filename = os.path.join(DATA_DIR, "spx_gamma.png")
    if os.path.exists(filename):
        await update.message.reply_photo(photo=InputFile(filename))
    else:
        await update.message.reply_text("Gamma chart not ready yet. Wait for background worker to generate it.")

# ---------- /chart command ----------
async def chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Default: send daily chart
    daily_chart = os.path.join(DATA_DIR, "spx_daily.png")
    weekly_chart = os.path.join(DATA_DIR, "spx_weekly.png")
    msg = "Available charts:\n"
    if os.path.exists(daily_chart):
        msg += "- Daily Expiration Chart: /chart_daily\n"
    if os.path.exists(weekly_chart):
        msg += "- Weekly Expiration Chart: /chart_weekly\n"
    await update.message.reply_text(msg)

async def chart_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filename = os.path.join(DATA_DIR, "spx_daily.png")
    if os.path.exists(filename):
        await update.message.reply_photo(photo=InputFile(filename))
    else:
        await update.message.reply_text("Daily chart not ready yet.")

async def chart_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filename = os.path.join(DATA_DIR, "spx_weekly.png")
    if os.path.exists(filename):
        await update.message.reply_photo(photo=InputFile(filename))
    else:
        await update.message.reply_text("Weekly chart not ready yet.")

# ---------- /maxpain command ----------
async def maxpain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filename = os.path.join(DATA_DIR, "spx_maxpain.png")
    if os.path.exists(filename):
        await update.message.reply_photo(photo=InputFile(filename))
    else:
        await update.message.reply_text("Max Pain chart not ready yet.")

# ---------- /daily_volume command ----------
async def daily_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filename = os.path.join(DATA_DIR, "spx_dailyvolume.png")
    if os.path.exists(filename):
        await update.message.reply_photo(photo=InputFile(filename))
    else:
        await update.message.reply_text("Daily volume chart not ready yet.")

# ---------- Callback query handler (inline buttons) ----------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "gamma":
        await spx_gamma(update, context)
    elif data == "chart":
        await chart(update, context)
    elif data == "maxpain":
        await maxpain(update, context)
    elif data == "dailyvolume":
        await daily_volume(update, context)

# ---------- /price command ----------
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import yfinance as yf
    if not context.args:
        await update.message.reply_text("Usage: /price SYMBOL\nExample: /price AAPL")
        return
    symbol = context.args[0].upper()
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")
        if data.empty:
            await update.message.reply_text(f"Symbol {symbol} not found.")
            return
        price = data["Close"].iloc[-1]
        await update.message.reply_text(f"📈 {symbol} price: ${price:.2f}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error getting price for {symbol}.")

# ---------- Main function ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("spx_gamma", spx_gamma))
    app.add_handler(CommandHandler("chart", chart))
    app.add_handler(CommandHandler("chart_daily", chart_daily))
    app.add_handler(CommandHandler("chart_weekly", chart_weekly))
    app.add_handler(CommandHandler("maxpain", maxpain))
    app.add_handler(CommandHandler("daily_volume", daily_volume))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
