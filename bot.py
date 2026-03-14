import os
import yfinance as yf
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Get token from environment variable (safe for GitHub)
TOKEN = os.getenv("6561701841:AAGxOFKrQ_ULb0i73D3ZVfo9uF-CBrd3mv8")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! 👋\n\nSend:\n/price AAPL\n/price TSLA\n/price BTC-USD"
    )

# Price command
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) == 0:
        await update.message.reply_text("Usage:\n/price AAPL")
        return

    symbol = context.args[0].upper()

    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")

        if data.empty:
            await update.message.reply_text("Symbol not found.")
            return

        price = data["Close"].iloc[-1]

        await update.message.reply_text(
            f"📈 {symbol} price: ${price:.2f}"
        )

    except Exception as e:
        await update.message.reply_text("Error getting price.")

# Main function
def main():

    if TOKEN is None:
        print("ERROR: BOT_TOKEN not found!")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))

    print("Bot is running...")

    app.run_polling()

# Run bot
if __name__ == "__main__":
    main()
