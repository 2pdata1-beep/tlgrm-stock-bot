# bot.py
from dotenv import load_dotenv
import os
import asyncio
import yfinance as yf
import pandas as pd
import numpy as np
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- LOAD ENV VARIABLES ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
ALERT_CHAT_ID = os.getenv("ALERT_CHAT_ID")

if not TOKEN:
    print("❌ ERROR: BOT_TOKEN not found in .env")
    exit(1)

# --- CONFIG ---
TICKER = "^GSPC"  # S&P 500 Index
ALERT_INTERVAL = 300  # seconds
ALERT_THRESHOLD = 0.05  # 5% from Max Pain

# --- HELPER FUNCTIONS ---
def fetch_option_chain(ticker=TICKER):
    spx = yf.Ticker(ticker)
    expiration = spx.options[0]
    chain = spx.option_chain(expiration)
    spot = spx.history(period="1d")["Close"].iloc[-1]
    return chain.calls, chain.puts, spot

def compute_max_pain(calls, puts):
    df = pd.merge(
        calls[["strike", "openInterest"]],
        puts[["strike", "openInterest"]],
        on="strike",
        suffixes=("_call", "_put")
    )
    pain = []
    for strike in df["strike"]:
        call_pain = ((df["strike"] - strike).clip(lower=0) * df["openInterest_call"]).sum()
        put_pain = ((strike - df["strike"]).clip(lower=0) * df["openInterest_put"]).sum()
        pain.append(call_pain + put_pain)
    df["pain"] = pain
    df["PCR"] = df["openInterest_put"] / df["openInterest_call"]
    max_pain_strike = df.loc[df["pain"].idxmin(), "strike"]
    return max_pain_strike, df

def calculate_gex(spot, strike, vol, dte, oi, option_type):
    T = dte / 365
    d1 = (np.log(spot / strike) + 0.5 * vol**2 * T) / (vol * np.sqrt(T))
    gamma = np.exp(-d1**2 / 2) / (spot * vol * np.sqrt(2 * np.pi * T))
    return gamma * oi * 100 * spot**2 * 0.01 if option_type == "call" else -gamma * oi * 100 * spot**2 * 0.01

def compute_net_gex(calls, puts, spot):
    strikes = sorted(set(calls["strike"]).union(set(puts["strike"])))
    results = []
    for strike in strikes:
        call_oi = calls[calls["strike"] == strike]["openInterest"].sum()
        put_oi = puts[puts["strike"] == strike]["openInterest"].sum()
        call_gex = calculate_gex(spot, strike, 0.25, 5, call_oi, 'call')
        put_gex = calculate_gex(spot, strike, 0.25, 5, put_oi, 'put')
        results.append({"strike": strike, "Net_GEX": call_gex + put_gex})
    df_gex = pd.DataFrame(results)
    max_gex_strike = df_gex.loc[df_gex["Net_GEX"].idxmax(), "strike"]
    return df_gex, max_gex_strike

# --- LLM SIGNAL FUNCTION ---
def llm_quant_signal(spot, max_pain, max_gex_strike, pcr_sample, news_headlines=None):
    signal = ""
    distance = (spot - max_pain)/max_pain
    if distance > 0.05:
        signal += f"⚠️ SPX above Max Pain ({max_pain:.2f}) → SHORT bias.\n"
    elif distance < -0.05:
        signal += f"⚠️ SPX below Max Pain ({max_pain:.2f}) → LONG bias.\n"
    else:
        signal += "SPX price near Max Pain → neutral.\n"
    signal += f"Gamma Wall (max Net GEX) at {max_gex_strike} may act as magnet.\n"
    avg_pcr = pcr_sample["PCR"].mean()
    signal += f"Put-Call Ratio ({avg_pcr:.2f}) → {'bearish' if avg_pcr>1 else 'bullish'}\n"
    if news_headlines:
        signal += "Recent headlines:\n- " + "\n- ".join(news_headlines[:3])
    return signal

# --- TELEGRAM COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! 👋\nSPX Gamma + Max Pain bot.\n"
        "Use /spx for numeric data, /spx_llm for LLM-style signal.\n"
        "Auto-alerts trigger when SPX nears Max Pain or Gamma Wall."
    )

async def spx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        calls, puts, spot = fetch_option_chain()
        max_pain, df = compute_max_pain(calls, puts)
        df_gex, max_gex_strike = compute_net_gex(calls, puts, spot)
        distance = abs(spot - max_pain)/max_pain
        signal = "⚠️ Price ABOVE Max Pain" if spot > max_pain else "⚠️ Price BELOW Max Pain" if distance>ALERT_THRESHOLD else "Neutral (Price near Max Pain)"
        msg = (
            f"📊 SPX: {spot:.2f}\nMax Pain: {max_pain}\nGamma Wall: {max_gex_strike}\nSignal: {signal}\n"
            f"PCR Sample:\n{df[['strike','PCR']].head().to_string(index=False)}"
        )
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error fetching SPX: {str(e)}")

async def spx_llm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        calls, puts, spot = fetch_option_chain()
        max_pain, df = compute_max_pain(calls, puts)
        df_gex, max_gex_strike = compute_net_gex(calls, puts, spot)
        news_headlines = [
            "Fed announces interest rate update",
            "SPX futures rise amid tech rally",
            "Market watchers eye gamma exposure zones"
        ]
        msg = llm_quant_signal(spot, max_pain, max_gex_strike, df, news_headlines)
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Error fetching SPX LLM: {str(e)}")

# --- AUTO ALERTS ---
async def auto_alerts(app):
    if not ALERT_CHAT_ID:
        print("⚠️ ALERT_CHAT_ID not set. Skipping auto-alerts.")
        return
    bot = app.bot
    while True:
        try:
            calls, puts, spot = fetch_option_chain()
            max_pain, df = compute_max_pain(calls, puts)
            df_gex, max_gex_strike = compute_net_gex(calls, puts, spot)
            distance = abs(spot - max_pain)/max_pain
            send_alert = False
            msg = f"📊 SPX Alert:\nPrice: {spot:.2f}\nMax Pain: {max_pain}\nGamma Wall: {max_gex_strike}\n"
            if distance > ALERT_THRESHOLD:
                send_alert = True
                msg += "⚠️ Price ABOVE Max Pain\n" if spot > max_pain else "⚠️ Price BELOW Max Pain\n"
            if abs(spot - max_gex_strike)/max_gex_strike < 0.005:
                send_alert = True
                msg += "⚠️ Price near Gamma Wall → potential market-maker squeeze\n"
            if send_alert:
                await bot.send_message(chat_id=ALERT_CHAT_ID, text=msg)
        except Exception as e:
            print(f"Auto-alert error: {str(e)}")
        await asyncio.sleep(ALERT_INTERVAL)

# --- MAIN ---
async def main_async():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("spx", spx))
    app.add_handler(CommandHandler("spx_llm", spx_llm))
    print("✅ SPX Gamma + LLM Bot running...")
    asyncio.create_task(auto_alerts(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main_async())
