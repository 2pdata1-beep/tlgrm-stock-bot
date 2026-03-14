from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yfinance as yf

import os
TOKEN = os.getenv("6561701841:AAGxOFKrQ_ULb0i73D3ZVfo9uF-CBrd3mv8")  # replace with your BotFather token

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! Send /price SYMBOL to get the stock price.\nExample: /price AAPL"
    )

# /price command
async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a stock symbol, e.g., /price AAPL")
        return
    symbol = context.args[0].upper()
    try:
        data = yf.Ticker(symbol)
        price_value = data.history(period="1d")["Close"].iloc[-1]
        await update.message.reply_text(f"{symbol} price: ${price_value:.2f}")
    except Exception as e:
        await update.message.reply_text(f"Error fetching data for {symbol}: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.run_polling()
