import os
from dotenv import load_dotenv
from flask import Flask

from api.binance_bridge import update_symbol_info

is_debug = True
use_reloader = True

def create_app(): # config_class = Config

    # create flask instance
    app = Flask(__name__)
    #CORS(app)

    # read config
    #app.config.from_object(config_class)

    with app.app_context():
        #bcrypt.init_app(app)

        from api.routes import api
        app.register_blueprint(api)
    
    return app

if __name__ == '__main__':
        
	load_dotenv(f"{os.path.dirname(__file__)}\.env")
        
	update_symbol_info()
    
	app = create_app()
	app.run(os.getenv('FLASK_SERVER'), os.getenv('FLASK_PORT'), debug = is_debug, threaded = True, use_reloader = use_reloader)