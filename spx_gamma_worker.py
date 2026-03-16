import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import time

def calculate_gex(spot, strike, vol, dte, oi, option_type):
    T = dte / 365
    if T == 0: T = 1/365
    d1 = (np.log(spot/strike) + 0.5*vol**2*T) / (vol*np.sqrt(T))
    gamma = np.exp(-d1**2/2)/(spot*vol*np.sqrt(2*np.pi*T))
    return gamma*oi*100*spot**2*0.01 if option_type=='call' else -gamma*oi*spot**2*0.01

def calc_max_pain(calls, puts):
    strikes = sorted(set(calls['strike']).union(puts['strike']))
    pain=[]
    for s in strikes:
        call_loss=sum(max(0,s-k)*oi for k,oi in zip(calls['strike'],calls['openInterest']))
        put_loss=sum(max(0,k-s)*oi for k,oi in zip(puts['strike'],puts['openInterest']))
        pain.append({'strike':s,'total_loss':call_loss+put_loss})
    df=pd.DataFrame(pain)
    return df.loc[df['total_loss'].idxmin()]['strike']

def generate_chart(filename="spx_gamma.png"):
    ticker=yf.Ticker("^SPX")
    expirations=ticker.options
    if not expirations:
        print("No SPX options data available")
        return
    nearest_exp=expirations[0]
    chain=ticker.option_chain(nearest_exp)
    calls, puts = chain.calls, chain.puts
    merged=pd.merge(calls[['strike','openInterest','impliedVolatility']],
                    puts[['strike','openInterest','impliedVolatility']],
                    on='strike', suffixes=('_call','_put'))
    merged['put_call_ratio']=merged['openInterest_put']/merged['openInterest_call']
    max_pain=calc_max_pain(calls, puts)
    spot=ticker.history(period="1d")['Close'].iloc[-1]
    dte=(pd.to_datetime(nearest_exp)-pd.Timestamp.today()).days
    net_gex=[]
    for idx,row in merged.iterrows():
        vol_call=row['impliedVolatility_call'] if row['impliedVolatility_call']>0 else 0.20
        vol_put=row['impliedVolatility_put'] if row['impliedVolatility_put']>0 else 0.20
        net_gex.append(calculate_gex(spot,row['strike'],vol_call,dte,row['openInterest_call'],'call')+
                       calculate_gex(spot,row['strike'],vol_put,dte,row['openInterest_put'],'put'))
    merged['net_gex']=net_gex

    fig, axs=plt.subplots(2,1,figsize=(12,10))
    # Put-Call Ratio
    axs[0].plot(merged['strike'],merged['put_call_ratio'],marker='o',label='Put-Call Ratio')
    axs[0].axvline(max_pain,color='r',linestyle='--',label=f'Max Pain: {max_pain}')
    axs[0].set_title('SPX Put-Call Ratio')
    axs[0].legend()
    axs[0].grid(True)
    # Gamma Exposure
    axs[1].plot(merged['strike'],merged['net_gex'],marker='o',color='orange',label='Net Gamma Exposure')
    axs[1].axvline(max_pain,color='r',linestyle='--',label=f'Max Pain: {max_pain}')
    high_gex=np.percentile(merged['net_gex'],95)
    for s in merged['strike'][merged['net_gex']>=high_gex]:
        axs[1].axvline(s,color='purple',linestyle=':',alpha=0.6)
    axs[1].set_title('SPX Gamma Exposure (High Gamma Walls Highlighted)')
    axs[1].legend()
    axs[1].grid(True)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close(fig)
    print(f"[{datetime.now()}] Chart saved to {filename}")

# Run continuously every 5 minutes
if __name__=="__main__":
    while True:
        try:
            generate_chart()
        except Exception as e:
            print("Error:", e)
        time.sleep(300)  # 5 minutes
