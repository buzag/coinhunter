import json
import pandas as pd
import numpy as np

def create_stoch(dfs):
    dfs['L14'] = dfs['Low'].rolling(window=14).min()
    dfs['H14'] = dfs['High'].rolling(window=14).max()
    dfs['%K'] = 100*((dfs['Close'] - dfs['L14']) / (dfs['H14'] - dfs['L14']) )
    dfs['%D'] = dfs['%K'].rolling(window=3).mean()
    return dfs

def create_bollinger_bands(dfs,window_size=20):
    dfs['30_Day_MA'] = dfs['Close'].rolling(window=window_size).mean()
    dfs['30_Day_STD'] = dfs['Close'].rolling(window=window_size).std() 
    dfs['Upper Band'] = dfs['30_Day_MA'] + (dfs['30_Day_STD'] * 2)
    dfs['Lower Band'] = dfs['30_Day_MA'] - (dfs['30_Day_STD'] * 2)
    return dfs

def create_BB_trigger3(dfs,high,upper,low,lower):
    dfs['bb_sell']=0
    dfs['bb_buy']=0
    dfs.loc[(high > upper),'bb_sell']=1
    dfs.loc[(low < lower),'bb_buy']=1
    return dfs

def create_stoch_trigger(dfs,  high, low, dpc,kpc):
    dfs['stoch_buy'] = 0
    dfs['stoch_sell'] = 0
    dfs.loc[((dpc > high) & (kpc > high)),'stoch_sell']=1
    dfs.loc[((dpc < low) & (kpc < low)),'stoch_buy']=1
    return dfs
                
def generate_triggers(dfs,high,low):
    dfs=create_stoch(dfs)
    dfs=create_bollinger_bands(dfs)
    dfs=create_stoch_trigger(dfs,high,low,dfs['%D'],dfs['%K'])
    dfs=create_BB_trigger3(dfs,dfs['High'],dfs['Upper Band'],dfs['Low'],dfs['Lower Band'])
    return dfs

def intersection_trigger(result_df,inter_df,inter_col,inter_by, result_col_name):
    df_filter=inter_df.loc[inter_df.loc[:, inter_col] == 1, inter_by].values
    
    rowfilter=np.intersect1d(df_filter,result_df[ inter_by ].values)
    result_df[result_col_name]=0
    for i in range(0,rowfilter.shape[0]):
        result_df.loc[ result_df[ inter_by ] == rowfilter[i], result_col_name] = 1
        
    return result_df

#%%

def bb_rs(json1,high=80,low=20):
    df = pd.DataFrame(list(zip(pd.to_datetime(json1['t'], unit='s'), json1['o'],json1['h'],json1['l'],json1['c'])),
              columns =['Time','Open', 'High', 'Low', 'Close'])
    df = generate_triggers(df,high,low)
    df['buy']=0
    df['sell']=0
    df.loc[( df['stoch_buy'] == 1 ) & ( df['bb_buy'] == 1 )  ,'buy' ] = 1
    df.loc[( df['stoch_sell'] == 1 ) & ( df['bb_sell'] == 1 )  ,'sell' ] = 1    
    
    sor=len(df)-1
    
    Dict = {'BUY': {'BUY': df['buy'][sor], 'stoch_value': df['%K'][sor]},
            'SELL': {'SELL2': df['sell'][sor], 'stoch_value': df['%K'][sor]}} 
    
   # print("buy:",df['buy'][sor],"sell: ",df['sell'][sor])
    Dict = {'BB': {'BUY': df['bb_buy'][sor], 'SELL': df['bb_sell'][sor]},
            'STOCH': {'stoch_value': df['%K'][sor]}}
    return Dict


#%%MACD
class Point: 
    def __init__(self, x, y): 
        self.x = x 
        self.y = y 
    
def onSegment(p, q, r): 
    if ( (q.x <= max(p.x, r.x)) and (q.x >= min(p.x, r.x)) and 
           (q.y <= max(p.y, r.y)) and (q.y >= min(p.y, r.y))): 
        return True
    return False
  
def orientation(p, q, r): 
      
    val = (float(q.y - p.y) * (r.x - q.x)) - (float(q.x - p.x) * (r.y - q.y)) 
    if (val > 0):

        return 1
    elif (val < 0): 
        return 2
    else: 
        return 0

def doIntersect(p1,q1,p2,q2): 

    o1 = orientation(p1, q1, p2) 
    o2 = orientation(p1, q1, q2) 
    o3 = orientation(p2, q2, p1) 
    o4 = orientation(p2, q2, q1) 

    if ((o1 != o2) and (o3 != o4)): 
        return True
    if ((o1 == 0) and onSegment(p1, p2, q1)): 
        return True
    if ((o2 == 0) and onSegment(p1, q2, q1)): 
        return True
    if ((o3 == 0) and onSegment(p2, p1, q2)): 
        return True
    if ((o4 == 0) and onSegment(p2, q1, q2)): 
        return True
    return False

def macd(json1):
    df = pd.DataFrame(list(zip(pd.to_datetime(json1['t'], unit='s'), json1['o'],json1['h'],json1['l'],json1['c'])),
              columns =['Time','Open', 'High', 'Low', 'Close'])
    #create ema macd signal
    df['ema200'] = df['Close'].ewm(span = 200).mean()
    df['ema12'] = df['Close'].ewm(span = 12, adjust = False).mean()
    df['ema26'] = df['Close'].ewm(span = 26, adjust = False).mean()
    df['MACD'] = (df['ema12']-df['ema26'])
    df['signal'] =  df['MACD'].ewm(span = 9, adjust = False).mean()
    
    #create trend
    df['ema200_5'] = df['ema200'] - df['ema200'].shift(5)
    df['ema200_10'] = df['ema200'] - df['ema200'].shift(10)
    df['ema200_25'] = df['ema200'] - df['ema200'].shift(25)
    df['ema200_50'] = df['ema200'] - df['ema200'].shift(50)
    df['ema200_75'] = df['ema200'] - df['ema200'].shift(75)
    df['trend'] = 0
    #df.trend[(df['ema200_10'] > 0) & (df['ema200_25'] > 0) & (df['ema200_50'] > 0) & (df['ema200_75'] > 0) ] = 1
    
    #check if trend is increasing
    trend = (df['ema200_5'] > 0) & (df['ema200_10'] > 0) & (df['ema200_25'] > 0) & (df['ema200_50'] > 0) & (df['ema200_75'] > 0)
    trend =  (df['ema200_25'] > 0) & (df['ema200_50'] > 0) & (df['ema200_75'] > 0)
    df['trend'] = trend
    
  
    df['intersection'] = ''
    for i in range(0,len(df)): 
        try: 
            p1 = Point(i, df.at[i,'MACD']) 
            q1 = Point(i+1, df.at[i+1,'MACD']) 
            p2 = Point(i, df.at[i,'signal']) 
            q2 = Point(i+1, df.at[i+1,'signal']) 
              
            if doIntersect(p1, q1, p2, q2): 
                if df.at[i,'MACD'] < 0 and df.at[i,'signal'] < 0:
                    df.at[i,'intersection'] = 1
                else:
                    df.at[i,'intersection'] = 0
            else: 
                
                df.at[i,'intersection'] = 0
        except: 
            df.at[i+1,'intersection'] = 0
            pass
    
    buy = (df['trend']==1) & (df['intersection']==1)
    df['buy'] = buy
    eredmeny=df['buy'][-1:].values[0]
    return eredmeny


#%%
    
api_key = ['boi4o5nrh5rab1ps2lp0','bos2477rh5rbk6e6osq0']
 
import requests
#import os
#os.chdir("C:/Users/slezakm/Documents/GitHub/TradingBot/Pasztazo/")
import os 

r = requests.get('https://finnhub.io/api/v1/forex/symbol?exchange=forex.com&token='+api_key[0])
json1=json.loads(r.text)
prices_name=[]
prices_symbol=[]
for i in range(0,len(json1)):
    prices_symbol.append(json1[i]['symbol'])
    prices_name.append(json1[i]['displaySymbol'])
    
prices_name=prices_name[0:80]
prices_symbol=prices_symbol[0:80]


date_types = [15 ,30, 60, 'D', 'W']

date_names = ['15m','30m','1h','1D','1W']

result=[]

for i in range(0,80):

    try:
        r = requests.get('https://finnhub.io/api/v1/forex/candle?symbol='+prices_symbol[i]+'&resolution='+str(date_types[0])+'&count=300&token='+api_key[0])
        json1=json.loads(r.text)
        r = requests.get('https://finnhub.io/api/v1/forex/candle?symbol='+prices_symbol[i]+'&resolution='+str(date_types[1])+'&count=300&token='+api_key[0])
        json2=json.loads(r.text)
        r = requests.get('https://finnhub.io/api/v1/forex/candle?symbol='+prices_symbol[i]+'&resolution='+str(date_types[2])+'&count=300&token='+api_key[0])
        json3=json.loads(r.text)
        r = requests.get('https://finnhub.io/api/v1/forex/candle?symbol='+prices_symbol[i]+'&resolution='+str(date_types[3])+'&count=300&token='+api_key[0])
        json4=json.loads(r.text)
        r = requests.get('https://finnhub.io/api/v1/forex/candle?symbol='+prices_symbol[i]+'&resolution='+str(date_types[4])+'&count=300&token='+api_key[0])
        json5=json.loads(r.text)
    except:
        r = requests.get('https://finnhub.io/api/v1/forex/candle?symbol='+prices_symbol[i]+'&resolution='+str(date_types[0])+'&count=300&token='+api_key[1])
        json1=json.loads(r.text)
        r = requests.get('https://finnhub.io/api/v1/forex/candle?symbol='+prices_symbol[i]+'&resolution='+str(date_types[1])+'&count=300&token='+api_key[1])
        json2=json.loads(r.text)
        r = requests.get('https://finnhub.io/api/v1/forex/candle?symbol='+prices_symbol[i]+'&resolution='+str(date_types[2])+'&count=300&token='+api_key[1])
        json3=json.loads(r.text)
        r = requests.get('https://finnhub.io/api/v1/forex/candle?symbol='+prices_symbol[i]+'&resolution='+str(date_types[3])+'&count=300&token='+api_key[1])
        json4=json.loads(r.text)
        r = requests.get('https://finnhub.io/api/v1/forex/candle?symbol='+prices_symbol[i]+'&resolution='+str(date_types[4])+'&count=300&token='+api_key[1])
        json5=json.loads(r.text)
        pass
    
    result.append([prices_name[i],
                    bb_rs(json1)['BB']['BUY'],bb_rs(json2)['BB']['BUY'],bb_rs(json3)['BB']['BUY'], bb_rs(json4)['BB']['BUY'],bb_rs(json5)['BB']['BUY'],
                    bb_rs(json1)['BB']['SELL'],bb_rs(json2)['BB']['SELL'],bb_rs(json3)['BB']['SELL'], bb_rs(json4)['BB']['SELL'],bb_rs(json5)['BB']['SELL'],
                    bb_rs(json1)['STOCH']['stoch_value'],bb_rs(json2)['STOCH']['stoch_value'],bb_rs(json3)['STOCH']['stoch_value'],bb_rs(json4)['STOCH']['stoch_value'],bb_rs(json5)['STOCH']['stoch_value'],
                    macd(json1),macd(json2),macd(json3),macd(json4),macd(json5)])
        
#RESULT[VALUTA_NEV, BB_BUY, BB_SELL, RSI, MACD, DATE_TYPE]
cols_help=['BB_BUY','BB_SELL','RSI','MACD']

cols=['price_name']

for j in range(0,len(cols_help)):
    for i in range(0,len(date_names)):
        cols.append(cols_help[j]+'_'+date_names[i])
        
df3 = pd.DataFrame(result, columns=cols)

csv_name='eredmeny.csv'
full_path = os.path.realpath(__file__)

#df3.to_csv(full_path[:-18]+csv_name,index=False)
df3.to_csv('./'+csv_name,index=False)

print(full_path[:-18]+csv_name)
print("kesz")
import time
time.sleep(10)
