# bot.py
import os
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---------- Bot Token ----------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not found! Add it in your environment variables.")
    exit(1)

# ---------- /start command ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! 👋\n\n"
        "I can show stock prices and SPX Gamma charts.\n\n"
        "Examples:\n"
        "/price AAPL\n"
        "/price TSLA\n"
        "/spx_gamma"
    )

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

# ---------- /spx_gamma command (safe) ----------
async def spx_gamma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filename = "spx_gamma.png"
    if os.path.exists(filename):
        await update.message.reply_photo(photo=InputFile(filename))
    else:
        await update.message.reply_text(
            "SPX Gamma chart not ready yet. Please wait a few minutes for the background worker to generate it."
        )

# ---------- Main function ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("spx_gamma", spx_gamma))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
