import os
import json
import pandas as pd
from datetime import datetime, timedelta
import pytz
from binance.client import Client

client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_SECRET_KEY'))

def get_symbol_info_from_cache(symbol):

	# check for symbol cache file existence
	sym_info_fp = os.getenv('BINANCE_SYM_INFO_FILE_PATH')
	if not os.path.exists(sym_info_fp):
		raise Exception("BINANCE_SYM_INFO_FILE_PATH file is not exist!")
	
	# read symbol cache file
	json_d = None  
	with open(sym_info_fp, "r") as f:
		json_d = json.load(f)

	for sym_dict in json_d:
		if sym_dict["symbol"] == symbol:
			return sym_dict

def update_symbol_info():
	syms_info = client.futures_exchange_info()
	with open(os.getenv('BINANCE_SYM_INFO_FILE_PATH'), 'w') as f:
		f.write(json.dumps(syms_info['symbols']))

def get_account_info(asset = 'USDT'):
	bals = client.futures_account_balance(recvWindow = 10000000) # timestamp = int(datetime.utcnow().timestamp() *1000)
	for b in bals:
		if b['asset' ] == asset:
			return b

def get_leverage(symbol):
	poses = client.futures_position_information(recvWindow = 10000000)
	ps = []
	for p in poses:
		if p['symbol'] == symbol:
			return p['leverage']

def get_mark_price(symbol):
	return float(client.futures_mark_price(symbol=symbol)['markPrice'])

def get_positions(symbol):
	poses = client.futures_position_information(recvWindow = 10000000)
	ps = []
	for p in poses:
		if p['symbol'] == symbol and float(p['entryPrice']) > 0:
			ps.append(p)
	return ps

# ez nem kell
def money_qty_to_coin_qty(symbol, usd_to_open):    
	m_price = get_mark_price(symbol)
	c_qty = round(usd_to_open / m_price, 3)
	return c_qty

def get_position_size(symbol, risk_p):

	base_asset = "USDT"
	
	leverage = int(get_leverage(symbol))
	sym_p = float(get_mark_price(symbol))
	bal = float(get_account_info(base_asset)['balance'])

	sym_dict = get_symbol_info_from_cache(symbol)
	
	# read symbol info from cache
	qty_prec = None
	price_prec = None
	min_qty = None  
	min_base_val = None
	
	# get qty precision
	qty_prec = int(sym_dict["quantityPrecision"])
	price_prec = int(sym_dict["pricePrecision"])
	# get min qty
	for fil in sym_dict["filters"]:
		if fil["filterType"] == "LOT_SIZE":
			min_qty = float(fil["minQty"])
		if fil["filterType"] == "MIN_NOTIONAL":
			min_base_val = float(fil["notional"])
		
	if qty_prec is None:
		raise Exception("Error when getting position size, the qty precision cannot be found in symbol info cache file")
	
	if min_qty is None:
		raise Exception("Error when getting position size, the min qty cannot be found in symbol info cache file")
	
	if price_prec is None:
		raise Exception("Error when getting position size, the price_prec cannot be found in symbol info cache file")
	
	if min_base_val is None:
		raise Exception("Error when getting position size, the min_base_val cannot be found in symbol info cache file")
	
	# calculate qty to open
	pos_base_val = bal * (risk_p / 100) * leverage

	# too less base(USDT) ammount
	if pos_base_val < min_base_val:
		raise Exception(f"Error when getting position size, the min_base_val {min_base_val} must be > than the sending ammount {pos_base_val}")

	qty = pos_base_val / sym_p
	qty = round(qty, qty_prec)

	# too small qty
	if min_qty > qty:
		raise Exception(f"Error when getting position size, the min qty {min_qty} > than qty to open {qty} ")

	return {
		'qty_coin': qty,
		'qty_money': pos_base_val,
		'asset': base_asset,
		'leverage': leverage
	}

def send_market_order(symbol, o_side, qty_coin, client_order_id):

	p_side = 'LONG'
	if o_side == 'SELL':
		p_side = 'SHORT'

	return client.futures_create_order(
		symbol=symbol, 
		side=o_side, # client.SIDE_SELL, 'SELL' 
		positionSide= p_side, #  LONG, SHORT
		type=client.FUTURE_ORDER_TYPE_MARKET,
		quantity =  qty_coin, # in coin -> usdt amm / price -> coin amm
		newClientOrderId = client_order_id,
		recvWindow = 10000000)

def close_position(symbol,  p_side):

	o_side = "SELL"
	if p_side == 'SHORT':
		o_side = 'BUY'

	# search for pos 
	pos_qty = None
	ps = get_positions(symbol)
	for p in ps:
		if p['positionSide'] == p_side:
			pos_qty = p['positionAmt']
			break

	# pos not found
	if pos_qty is None:
		raise Exception(f"Error when closing {p_side} positions, no position is found")
	
	if p_side == 'SHORT':
		pos_qty = float(pos_qty)
		pos_qty *= -1

	return client.futures_create_order(
		symbol=symbol, 
		side=o_side,
		positionSide= p_side, #  LONG, SHORT
		type=client.FUTURE_ORDER_TYPE_MARKET,
		quantity = pos_qty,
		recvWindow = 100000000)

def get_orders(symbol, start_time = None, end_time = None, limit = None, order_type = None, order_status = None, o_side = None,  client_order_id = None, order_id = None):

	result = client.futures_get_all_orders(symbol = symbol, startTime = start_time, endTime = end_time, limit = limit, orderId = order_id,  recvWindow = 10000000)
	
	# filter out pos. closing orders
	df_d_in = []
	for r in result:
		if r['reduceOnly'] == False:
			df_d_in.append(r)

	to_ret = {}
	if len(df_d_in) > 0:
		df = pd.DataFrame(df_d_in, dtype = str)
		df = df.sort_values(['updateTime'], ascending = False)
		if client_order_id is not None:
			df = df[df['clientOrderId'] == client_order_id]
		if order_type is not None:
			df = df[df['type'] == order_type]
		if o_side is not None:
			df = df[df['side'] == o_side]  
		if order_status is not None:
			df = df[df['status'] == order_status]
		if limit is not None:
			df = df[0: limit]

		to_ret = df.to_dict(orient="records")

	return to_ret

def get_last_filled_market_order(symbol, o_type, from_date_ts_ms = None, client_order_id = None):  #  o_type = BUY, SELL

	orders_dict = get_orders(symbol, from_date_ts_ms, order_type='MARKET', o_side=o_type, client_order_id = client_order_id)
	if len(orders_dict) > 0:

		last_o = orders_dict[0]

		# elapsed sec-s since last order
		last_o_since_sec = None
		if last_o is not None:
			utc_now_ts = datetime.utcnow().timestamp()
			last_o_utc_ts = datetime.fromtimestamp(int(last_o['updateTime']) / 1000).astimezone(pytz.UTC).replace(tzinfo=None).timestamp()
			last_o_since_sec = int(utc_now_ts - last_o_utc_ts)

		# price diff since last order
		p_diff = abs(get_mark_price(symbol) - float(last_o['avgPrice']))

		return {
			'order': last_o, 
			'info': {'dt_diff_sec': last_o_since_sec, 'p_diff': p_diff}}
	