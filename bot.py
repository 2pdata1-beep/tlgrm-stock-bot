import os
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN=os.getenv("BOT_TOKEN")
if not TOKEN:
    print("BOT_TOKEN not set!")
    exit(1)

async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! 👋\n\n"
        "Example:\n/price AAPL\n/spx_gamma"
    )

async def price(update:Update, context:ContextTypes.DEFAULT_TYPE):
    import yfinance as yf
    if not context.args:
        await update.message.reply_text("Usage: /price SYMBOL")
        return
    symbol=context.args[0].upper()
    try:
        stock=yf.Ticker(symbol)
        price=stock.history(period="1d")['Close'].iloc[-1]
        await update.message.reply_text(f"📈 {symbol}: ${price:.2f}")
    except:
        await update.message.reply_text(f"Error fetching {symbol}")

# Safe SPX Gamma command
async def spx_gamma(update:Update, context:ContextTypes.DEFAULT_TYPE):
    filename="spx_gamma.png"
    if os.path.exists(filename):
        await update.message.reply_photo(photo=InputFile(filename))
    else:
        await update.message.reply_text("Chart not ready yet. Please wait a moment.")

def main():
    app=ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("spx_gamma", spx_gamma))
    print("Bot running...")
    app.run_polling()

if __name__=="__main__":
    main()
