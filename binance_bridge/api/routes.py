from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from api.binance_bridge import get_account_info, get_positions, get_mark_price, send_market_order, get_position_size, get_last_filled_market_order, close_position

api = Blueprint('api',__name__)

@api.route('/api/v1/resources/get_account_info', methods=['GET'])
def get_account_info_ep():
    
	asset = request.args.get('asset')
	if asset is None:
		asset = 'USDT'
        
	res = get_account_info(asset)

	return jsonify({'status': 'SUCCEED', 'data': res})

@api.route('/api/v1/resources/get_mark_price', methods=['GET'])
def get_mark_price_ep():
    
	symbol = request.args.get('symbol')
	if symbol is None:
		return jsonify({ 'status': 'ERROR', 'data': 'Error when requesting mark price, no symbol is specified'})
		
	res = get_mark_price(symbol)

	return jsonify({'status': 'SUCCEED', 'data': { 'mark_price': res}})

@api.route('/api/v1/resources/get_positions', methods=['GET'])
def get_positions_ep():
    
	symbol = request.args.get('symbol')
	if symbol is None:
		return jsonify({ 'status': 'ERROR', 'data': 'Error when requesting positions, no symbol is specified'})
		
	res = get_positions(symbol)
	
	return jsonify({'status': 'SUCCEED', 'data': res})

@api.route('/api/v1/resources/get_position_size', methods=['GET'])
def get_position_size_ep():
    
	symbol = request.args.get('symbol')
	if symbol is None:
		return jsonify({ 'status': 'ERROR', 'data': 'Error when requesting position size, no symbol is specified'})
	
	risk_p = request.args.get('risk_p')
	if risk_p is None:
		return jsonify({ 'status': 'ERROR', 'data': 'Error when requesting position size, no risk_p is specified'})
		
	res = get_position_size(symbol, float(risk_p))

	return jsonify({'status': 'SUCCEED', 'data': res})

@api.route('/api/v1/resources/send_market_order', methods=['GET'])
def send_market_order_ep():
    
	symbol = request.args.get('symbol')
	if symbol is None:
		return jsonify({ 'status': 'ERROR', 'data': 'Error when sending market order, no symbol is specified'})
	
	o_side = request.args.get('o_side')
	if o_side is None:
		return jsonify({ 'status': 'ERROR', 'data': 'Error when sending market order, no o_side is specified'})
	
	qty_perc = request.args.get('qty_perc')
	if qty_perc is None:
		return jsonify({ 'status': 'ERROR', 'data': 'Error when sending market order, no qty_perc is specified'})
	qty_perc = float(qty_perc)

	client_order_id = request.args.get('client_order_id')
	if client_order_id is None:
		return jsonify({ 'status': 'ERROR', 'data': 'Error when sending market order, no client_order_id is specified'})
	
	p_sizing = get_position_size(symbol, qty_perc)
	qty_coin = float(p_sizing['qty_coin'])

	res = send_market_order(symbol, o_side, qty_coin, client_order_id)

	return jsonify({'status': 'SUCCEED', 'data': res})

@api.route('/api/v1/resources/close_position', methods=['GET'])
def close_position_ep():
    
	symbol = request.args.get('symbol')
	if symbol is None:
		return jsonify({ 'status': 'ERROR', 'data': 'Error when sending market order, no symbol is specified'})
	
	p_side = request.args.get('p_side')
	if p_side is None:
		return jsonify({ 'status': 'ERROR', 'data': 'Error when sending market order, no p_side is specified'})

	res = close_position(symbol, p_side)

	return jsonify({'status': 'SUCCEED', 'data': res})

@api.route('/api/v1/resources/get_last_filled_market_order', methods=['GET'])
def get_last_filled_market_order_ep():
    
	symbol = request.args.get('symbol')
	if symbol is None:
		return jsonify({'status': 'ERROR', 'data': 'Error when requesting last filled market order, no symbol is specified'})
	
	o_side = request.args.get('o_side')
	if o_side is None:
		return jsonify({'status': 'ERROR', 'data': 'Error when requesting last filled market order, no o_side is specified'})
	
	from_date_ts_ms = request.args.get('from_date_ts_ms')
	if from_date_ts_ms is None:
		from_date_ts_ms = int((datetime.utcnow() - timedelta(days = 1)).timestamp() * 1000)
	else:
		from_date_ts_ms = int(from_date_ts_ms)

	client_o_id = request.args.get('client_o_id')

	res = get_last_filled_market_order(symbol, o_side, from_date_ts_ms, client_o_id)

	return jsonify({'status': 'SUCCEED', 'data': res})
