import requests
import json
import os
import time
from threading import Thread
from bfxhfindicators import EMA

import schedule
import time

import telebot

bot = telebot.TeleBot("xxxxxxx:xxxxxxxxx")

def job():
    print("I'm working...")
    get_current_pairs()
    run_extract_candles()
    get_all_diferences_pairs()


schedule.every().day.at("23:00").do(job)
schedule.every().day.at("19:00").do(job)
schedule.every().day.at("07:00").do(job)
schedule.every().day.at("11:00").do(job)
schedule.every().day.at("15:00").do(job)

old_coins = []
new_coins = []

BASE_URL = 'https://api.binance.com'

TIMEFRAME = '4h'
EMA_PERIODS = [55, 200]

symbols = []
candles = {}
prices = {}
ema_values = {}

def load_candles(sym):
    global candles, prices, BASE_URL
    payload = {
            'symbol': sym,
            'interval': TIMEFRAME,
            'limit': 250
    }
    resp = requests.get(BASE_URL + '/api/v1/klines', params=payload)
    klines = json.loads(resp.content)
    # parse klines and store open, high, low, close and vol only
    parsed_klines = []
    for k in klines:
        k_candle = {
            'open': float(k[1]),
            'high': float(k[2]),
            'low': float(k[3]),
            'close': float(k[4]),
            'vol': float(k[5])
        }
        parsed_klines.append(k_candle)
        #print(k)
    candles[sym] = parsed_klines
    index = len(parsed_klines) - 1 # get index of latest candle
    prices[sym] = parsed_klines[index]['close'] # save current price

def run_extract_candles():
    # create results folder if it doesn't exist
    if not os.path.exists('results/'):
        os.makedirs('results/')
    # start with blank files
    open('results/below_55.txt', 'w').close()
    open('results/above_55_below_200.txt', 'w').close()
    open('results/above_200.txt', 'w').close()
    
    # load symbols information
    print('Getting list of BTC trade pairs...')
    resp = requests.get(BASE_URL + '/api/v1/ticker/allBookTickers')
    #print(resp.content)
    tickers_list = json.loads(resp.content)
    for ticker in tickers_list:
        if str(ticker['symbol'])[-3:] == 'BTC':
            symbols.append(ticker['symbol'])
    
    # get 4h candles for symbols
    print('Loading candle data for symbols...')
    for sym in symbols:
        #print('BINANCE:' + sym)
        Thread(target=load_candles, args=(sym,)).start()
    while len(candles) < len(symbols):
        print('%s/%s loaded' %(len(candles), len(symbols)), end='\r', flush=True)
        time.sleep(0.1)
    
    # calculate EMAs for each symbol
    print('Calculating EMAs...')
    for sym in candles:
        for period in EMA_PERIODS:
            iEMA = EMA(period)
            lst_candles = candles[sym][:]
            for c in lst_candles:
                iEMA.add(c['close'])
            if sym not in ema_values:
                ema_values[sym] = {}
            ema_values[sym][period] = iEMA.v()
    
    # save filtered EMA results in txt files
    print('Saving filtered EMA results to txt files...')
    for sym in ema_values:
        ema_55 = ema_values[sym][55]
        ema_200 = ema_values[sym][200]
        price = prices[sym]
        entry = ''
        if price < ema_200:
        # save symbols trading below EMA (50)
            f = open('results/below_55.txt', 'a')
            entry = '%s: $%s\n' %(sym, round(price,3))
            f.write(entry)
        elif price > ema_55 and price < ema_200:
        # save symbols trading above EMA(200)
            f = open('results/above_55_below_200.txt', 'a')
            entry = '%s: $%s\n' %(sym, round(price,3))
            f.write(entry)
        elif price > ema_200:
        # save symbols trading above EMA(50) but below EMA(200)
            f = open('results/above_200.txt', 'a')
            entry = '%s: $%s\n' %(sym, round(price,3))
            f.write(entry)
        f.close()
        del f # cleanup
    
    print('All done! Results saved in results folder.')

def get_current_pairs():

    A = []
    B = []
    lines = open('results/above_200.txt', 'r').read().splitlines()
    for line in lines:
        formated = line.split(":")
        old_coins.append(formated[0])

    print(old_coins)


def get_all_diferences_pairs():
    lines = open('results/above_200.txt', 'r').read().splitlines()
    for line in lines:
        formated = line.split(":")
        new_coins.append(formated[0])

    print(new_coins)

    print("Missing values in first list:", (set(old_coins).difference(new_coins)))
    print("Additional values in first list:", (set(new_coins).difference(old_coins)))
    bot.send_message(367830779, 'Above 200 EMA H4:' + str((set(new_coins).difference(old_coins))))
    bot.send_message(367830779, 'Below 200 EMA H4:' + str((set(old_coins).difference(new_coins))))


def main():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__=="__main__":
    main()


