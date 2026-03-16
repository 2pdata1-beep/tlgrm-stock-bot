import os
import yfinance as yf
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio

# ---------- Bot Token ----------
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not found! Add it in Railway Variables.")
    exit(1)

# ---------- /start command ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! 👋\n\n"
        "I can show stock prices.\n\n"
        "Example:\n"
        "/price AAPL\n"
        "/price TSLA\n"
        "/price BTC-USD\n"
        "/spx_gamma (S&P 500 Options)"
    )

# ---------- /price command ----------
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

# ---------- Gamma Exposure Function ----------
def calculate_gex(spot, strike, vol, dte, oi, option_type):
    T = dte / 365
    if T == 0:
        T = 1/365
    d1 = (np.log(spot / strike) + (0.5 * vol**2) * T) / (vol * np.sqrt(T))
    gamma = np.exp(-d1**2 / 2) / (spot * vol * np.sqrt(2 * np.pi * T))
    if option_type == 'call':
        return gamma * oi * 100 * spot**2 * 0.01
    else:
        return -gamma * oi * 100 * spot**2 * 0.01

# ---------- Max Pain Function ----------
def calc_max_pain(calls, puts):
    strikes = sorted(set(calls['strike']).union(puts['strike']))
    pain = []
    for s in strikes:
        call_loss = sum(max(0, s - k) * oi for k, oi in zip(calls['strike'], calls['openInterest']))
        put_loss = sum(max(0, k - s) * oi for k, oi in zip(puts['strike'], puts['openInterest']))
        pain.append({'strike': s, 'total_loss': call_loss + put_loss})
    df_pain = pd.DataFrame(pain)
    max_pain_strike = df_pain.loc[df_pain['total_loss'].idxmin()]['strike']
    return max_pain_strike

# ---------- /spx_gamma command ----------
async def spx_gamma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def fetch_and_plot():
        try:
            ticker = yf.Ticker("^SPX")
            expirations = ticker.options
            if not expirations:
                return None, "No SPX options data available."

            nearest_exp = expirations[0]
            option_chain = ticker.option_chain(nearest_exp)
            calls = option_chain.calls
            puts = option_chain.puts

            # Merge for Put-Call Ratio
            merged = pd.merge(calls[['strike', 'openInterest', 'impliedVolatility']],
                              puts[['strike', 'openInterest', 'impliedVolatility']],
                              on='strike', suffixes=('_call', '_put'))
            merged['put_call_ratio'] = merged['openInterest_put'] / merged['openInterest_call']

            # Max Pain
            max_pain = calc_max_pain(calls, puts)

            # Gamma Exposure using actual IV
            spot_price = ticker.history(period="1d")['Close'].iloc[-1]
            dte = (pd.to_datetime(nearest_exp) - pd.Timestamp.today()).days
            net_gex = []
            for idx, row in merged.iterrows():
                vol_call = row['impliedVolatility_call'] if row['impliedVolatility_call'] > 0 else 0.20
                vol_put = row['impliedVolatility_put'] if row['impliedVolatility_put'] > 0 else 0.20
                call_gex = calculate_gex(spot_price, row['strike'], vol_call, dte, row['openInterest_call'], 'call')
                put_gex = calculate_gex(spot_price, row['strike'], vol_put, dte, row['openInterest_put'], 'put')
                net_gex.append(call_gex + put_gex)
            merged['net_gex'] = net_gex

            # ---------- Plot Charts ----------
            fig, axs = plt.subplots(2, 1, figsize=(12, 10))
            # Put-Call Ratio
            axs[0].plot(merged['strike'], merged['put_call_ratio'], marker='o', label="Put-Call Ratio")
            axs[0].axvline(max_pain, color='r', linestyle='--', label=f"Max Pain: {max_pain}")
            axs[0].set_title("SPX Put-Call Ratio by Strike")
            axs[0].set_xlabel("Strike")
            axs[0].set_ylabel("Put-Call Ratio")
            axs[0].legend()
            axs[0].grid(True)
            # Gamma Exposure
            axs[1].plot(merged['strike'], merged['net_gex'], marker='o', color='orange', label="Net Gamma Exposure")
            axs[1].axvline(max_pain, color='r', linestyle='--', label=f"Max Pain: {max_pain}")
            high_gex_threshold = np.percentile(merged['net_gex'], 95)
            high_gex_strikes = merged['strike'][merged['net_gex'] >= high_gex_threshold]
            for s in high_gex_strikes:
                axs[1].axvline(s, color='purple', linestyle=':', alpha=0.6)
            axs[1].set_title("SPX Gamma Exposure by Strike (High Gamma Walls Highlighted)")
            axs[1].set_xlabel("Strike")
            axs[1].set_ylabel("Net GEX")
            axs[1].legend()
            axs[1].grid(True)
            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            plt.close(fig)
            return buf, None
        except Exception as e:
            return None, str(e)

    loop = asyncio.get_running_loop()
    buf, error = await loop.run_in_executor(None, fetch_and_plot)
    if error:
        await update.message.reply_text(f"⚠️ {error}")
    else:
        await update.message.reply_photo(photo=InputFile(buf, filename="spx_gamma.png"))

# ---------- Main function ----------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Original handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))

    # New SPX Gamma command
    app.add_handler(CommandHandler("spx_gamma", spx_gamma))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
