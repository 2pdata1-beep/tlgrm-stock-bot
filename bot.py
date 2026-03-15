import os
import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Read the bot token from Railway environment variable
TOKEN = os.getenv("BOT_TOKEN")

# Stop if token is missing
if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not found! Add it in Railway Variables.")
    exit(1)


# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! 👋\n\n"
        "I can show stock prices.\n\n"
        "Example:\n"
        "/price AAPL\n"
        "/price TSLA\n"
        "/price BTC-USD"
    )


# /price command
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) == 0:
        await update.message.reply_text(
            "Usage:\n/price SYMBOL\nExample: /price AAPL"
        )
        return

    symbol = context.args[0].upper()

    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")

        if data.empty:
            await update.message.reply_text(f"Symbol {symbol} not found.")
            return

        price = data["Close"].iloc[-1]

        await update.message.reply_text(
            f"📈 {symbol} price: ${price:.2f}"
        )

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ Error getting price for {symbol}."
        )


# Main function
def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))

    print("✅ Bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
