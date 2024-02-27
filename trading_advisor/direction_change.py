import warnings
warnings.filterwarnings('ignore')
from datetime import datetime, timedelta
from time import sleep
import pytz
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from playsound import playsound # needs version 1.2.2, error in 1.3.0
from win10toast import ToastNotifier
from binance_f import RequestClient
from binance_f.model import *
from binance_f.constant.test import *
from binance_f.base.printobject import *

def notify(text, sound_file):
    playsound(sound_file)
    toaster.show_toast(text, text, duration=10, threaded=True)

def check_for_new_hds(df_hds, symbol):

    # first run
    if df_hds is None:
        df_hds = dl_binance_hds(symbol)
        last_hds_date = pd.Timestamp(df_hds['openTime'].values[-1]).to_pydatetime()
        print(f"New {len(df_hds)} hds, last data {last_hds_date.strftime('%Y-%m-%d %H:%M:%S')}")
    else:

        # last dl-ed data
        last_hds_date = pd.Timestamp(df_hds['openTime'].values[-1]).to_pydatetime()
    
        # new data should appear
        secs_elapsed = (datetime.utcnow() - last_hds_date).seconds
        print(f"{secs_elapsed} elapsed since last hds open date")
        last_hds_date = last_hds_date.replace(tzinfo=pytz.utc)
        if secs_elapsed > 120:

            # try to dl new data
            print(f"Trying to dl new data, {secs_elapsed} seconds elapsed")
            df_new_hds = dl_binance_hds(symbol, last_hds_date.astimezone() + timedelta(seconds=1)) # in local tz
            
            # new data found
            if df_new_hds is not None:
                dl_last_hds_date = pd.Timestamp(df_new_hds['openTime'].values[-1]).to_pydatetime()
                print(f"New dl {len(df_new_hds)} hds, last data {dl_last_hds_date.strftime('%Y-%m-%d %H:%M:%S')}")

                # save new data
                df_new_hds = df_new_hds[df_new_hds['openTime'] > df_hds['openTime'].values[-1]]
                if len(df_new_hds) > 0:
                    df_hds = pd.concat([df_hds, df_new_hds]).reset_index(drop=True)
                    last_hds_date = pd.Timestamp(df_hds['openTime'].values[-1]).to_pydatetime()
                    print(f"New saved {len(df_new_hds)} hds, last data {last_hds_date.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    print("no new data saved after filter")
            else:
                print("dl done, no new data found")

    return df_hds

def dl_binance_hds(symbol, start_time = None):
	df = None
	request_client = RequestClient(api_key=g_api_key, secret_key=g_secret_key)

	st = None
	if start_time is not None:
		st = int(datetime.timestamp(start_time) * 1000)

	result = request_client.get_candlestick_data(
			symbol=symbol, 
			interval=CandlestickInterval.MIN1, 
			startTime= st, 
			endTime=None, 
			limit=1000)

	r_arr = []
	for r in result:
		r_arr.append(r.__dict__)

	if len(r_arr) == 0:
		return None

	if df is None:
		df = pd.DataFrame(r_arr)[["openTime", "close", "volume"]]
		df["openTime"] = pd.to_datetime(df["openTime"], unit='ms')
		df["close"] = df["close"].astype(float)
		df["volume"] = df["volume"].astype(float)
		df = df[:-1]
	else:
		df_t = pd.DataFrame(r_arr)[["openTime", "close", "volume"]]
		df_t["openTime"] = pd.to_datetime(df_t["openTime"], unit='ms')
		df_t["close"] = df_t["close"].astype(float)
		df_t["volume"] = df_t["volume"].astype(float)
		df_t = df_t[:-1]

		df = pd.merge(df, df_t, left_index=True, right_index=True) #, on="openTime"

	if len(df) == 0:
		return None

	return df    

def iZLMA(sourceValues, SmoothPer, BarsTaken):

    sum = 0
    sumw = 0
    weight = 0
    
    limit = BarsTaken - 1
    lwma1 = np.zeros(BarsTaken)
    output = np.zeros(BarsTaken)
    
    #last_i = len(sourceValues) - 1
    for i in range(limit, -1, -1):
        sum=0
        sumw=0
        for k in range(SmoothPer):
            weight = SmoothPer - k 
            sumw += weight 
            sum += weight * sourceValues[i + k] 
        
        if sumw != 0:
            lwma1[i] = sum / sumw
        else:
            lwma1[i] = 0
    
    for i in range(limit + 1):
        sum=0
        sumw=0
        for k in range(100000):
            if k < SmoothPer and (i - k) >= 0:
                weight = SmoothPer - k
                sumw += weight
                sum += weight * lwma1[i - k]
            else:
                break

        if sumw != 0:
            output[i] = sum / sumw 
        else:
            output[i] = 0   

    return output

def get_direction_slope(df, dir_col_name, col_vals):

    df[dir_col_name] = -1

    col_vals_1 = f"{col_vals}_1"
    df[col_vals_1] = df[col_vals].shift(1)

    df.loc[df[col_vals] > df[col_vals_1], dir_col_name] = 1

    df.drop([col_vals_1], axis = 1, inplace = True)

    return df

def plot_colored_line(ax, df, col_name, col_color_name, i_start = None, i_end = None):

    x = df.index.values[i_start:i_end]
    y = df[col_name].values[i_start:i_end]
    y_col = df[col_color_name].values[i_start:i_end]    

    for x1, x2, y1,y2, y_col_act in zip(x, x[1:], y, y[1:], y_col):

        if y_col_act == -1:
            ax.plot([x1, x2], [y1, y2], 'r')
        elif y_col_act == 1:
            ax.plot([x1, x2], [y1, y2], 'g')
        else:
            ax.plot([x1, x2], [y1, y2], 'b')

# ---inputs
g_api_key = "your-api-key"
g_secret_key = "your-secret-key"
symbol = "ETHUSDT"
p = 50 # indicator period
plot_c = 200 # data count to plot
keep_gui_sec = 30 # gui responsive for x sec
sound_file = "E:\\Admiral MT5\\Sounds\\bintrader_alert.wav"
    
#------------------------------------

toaster = ToastNotifier()
last_dir = None
last_std_dir = None
df_hds = None
last_hd_date = None
dir_type = [] # 'd','u'
dir_change_idxs = []


if __name__ == '__main__':

    plt.switch_backend('QT5Agg') # pip install PyQt5
    #plt.get_backend()

    plt.ion()

    fig = plt.figure()
    ax1 = fig.add_subplot(231)
    ax2 = fig.add_subplot(232)
    ax3 = fig.add_subplot(233)
    ax4 = fig.add_subplot(234)
    ax5 = fig.add_subplot(235)

    mng = None
    while(True):

        df_hds = check_for_new_hds(df_hds, symbol)
        hd_date = df_hds['openTime'].values[-1]
        if hd_date != last_hd_date:

            print(f"last hds: {hd_date}")

            # calculate vol sum 
            df_hds['close_diff'] = df_hds['close'] - df_hds['close'].shift(1)
            df_hds.loc[(df_hds['close_diff'] < 0) & (df_hds['volume'] > 0), 'volume'] = df_hds['volume'] * -1
            df_hds['vol_sum'] = df_hds['volume'].cumsum()

            # calculate indi and direction color
            ilzma_vals = iZLMA(df_hds['close'].values[::-1], p, len(df_hds) - p) # reverse !
            ilzma_vs_vals = iZLMA(df_hds['vol_sum'].values[::-1], p, len(df_hds) - p)
            df_hds_t = df_hds[p:] # period corr
            df_hds_t['izlma'] = ilzma_vals[::-1]
            df_hds_t['izlma_vs'] = ilzma_vs_vals[::-1]
            get_direction_slope(df_hds_t,"izlma_c", "izlma")

            # calculate std price, indi diff
            df_hds_t['c_izlma_diff'] = df_hds_t['close'] - df_hds_t['izlma']
            df_hds_t['c_izlma_diff_std'] = df_hds_t['c_izlma_diff'] / df_hds_t['c_izlma_diff'].rolling(window=20, min_periods=1).std()        
            df_hds_t['vs_izlma_diff'] = df_hds_t['vol_sum'] - df_hds_t['izlma_vs']
            df_hds_t['vs_izlma_diff_std'] = df_hds_t['vs_izlma_diff'] / df_hds_t['vs_izlma_diff'].rolling(window=20, min_periods=1).std()

            # check for ilzma dir change
            lv = df_hds_t['izlma_c'].values[-1]
            if (last_dir is not None) and (lv != last_dir):

                # sound and toast alert
                #notify("ilzma Trend change", sound_file)

                # save direction
                dir_change_idxs.append(df_hds_t.index[-1])
                if lv == 1:
                    dir_type.append('u')
                else:
                    dir_type.append('d')

            # check for price ilzma diff std -2
            if (df_hds_t['c_izlma_diff_std'].values[-1] < -2.0) and last_std_dir != 1:
                last_std_dir = 1
                notify("price ilzma std -2, long", sound_file)
                if mng is not None: # activate charts
                    mng.window.raise_()

            # check for price ilzma diff std 2
            if (df_hds_t['c_izlma_diff_std'].values[-1] > 2.0) and last_std_dir != -1:
                last_std_dir = -1
                notify("price ilzma std 2, short", sound_file)
                if mng is not None: # activate charts
                    mng.window.raise_() # fig.canvas.manager.window.raise_()

            # calculate direction changes
            if len(dir_type) > 0:
                df_hds_t['dir_change'] = None
                df_hds_t['dir_type'] = None
                df_hds_t.loc[df_hds_t.index.isin(dir_change_idxs), 'dir_change'] = df_hds_t['close']
                df_hds_t.loc[df_hds_t.index.isin(dir_change_idxs), 'dir_type'] = dir_type

            last_dir = lv

            df_to_plot = df_hds_t[plot_c * -1:]

            ax1.clear()
            ax2.clear()
            ax3.clear()
            ax4.clear()
            ax5.clear()

            # plot price, indi
            df_to_plot[['close','izlma']].plot(ax=ax1, title= "Price ilzma")
            plot_colored_line(ax1, df_to_plot, "izlma", "izlma_c")

            df_to_plot[['vol_sum', 'izlma_vs']].plot(ax=ax2, title = "Vs ilzma")

            # plot std price, indi diff
            df_to_plot['c_izlma_diff_std'].plot(ax=ax3, title="Price ilzma diff std")
            ax3.hlines(0, df_to_plot.index[0], df_to_plot.index[-1], linestyles='dashed', colors = 'r')
            ax3.hlines(2, df_to_plot.index[0], df_to_plot.index[-1], linestyles='dashed', colors = 'g')
            ax3.hlines(-2, df_to_plot.index[0], df_to_plot.index[-1], linestyles='dashed', colors = 'g')

            # plot std vs, indi diff
            df_to_plot['vs_izlma_diff_std'].plot(ax=ax4, title= "Vs ilzma diff std")
            ax4.hlines(0, df_to_plot.index[0], df_to_plot.index[-1], linestyles='dashed', colors = 'r')
            ax4.hlines(2, df_to_plot.index[0], df_to_plot.index[-1], linestyles='dashed', colors = 'g')
            ax4.hlines(-2, df_to_plot.index[0], df_to_plot.index[-1], linestyles='dashed', colors = 'g')

            # plot vol sum
            df_to_plot['vol_sum'].plot(ax=ax5, title="vol sum")
            ax5.hlines(0, df_to_plot.index[0], df_to_plot.index[-1], linestyles='dashed', colors = 'r')
            
            # maximize window
            mng = plt.get_current_fig_manager()
            mng.window.showMaximized()

            # update window
            fig.canvas.draw()
            fig.canvas.flush_events()

            # show content
            plt.pause(keep_gui_sec) # sec
            #plt.show()

            # plot direction changes
            if len(dir_type) > 0:
                dir_changes_u = df_hds_t[df_hds_t['dir_type'] == 'u']['dir_change']
                if len(dir_changes_u) > 0:
                    dir_changes_u.plot(color='g', linestyle='None', marker='^')
                dir_changes_d = df_hds_t[df_hds_t['dir_type'] == 'd']['dir_change']
                if len(dir_changes_d) > 0:
                    dir_changes_d.plot(color='r', linestyle='None', marker='^')
                #df_hds_t[~df_hds_t['dir_change'].isnull()]['dir_change'].plot(title = "ilzma dir changes")
                #plt.show()

            last_hd_date = hd_date

        # only one execution(test)
        #break

        sleep(5)