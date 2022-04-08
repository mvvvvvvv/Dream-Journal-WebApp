# -*- coding: utf-8 -*-
"""
Created on Sun Apr 26 20:53:22 2020

@author: Maria
"""

import os
import pytz

from flask import Flask


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True, static_folder="static", static_url_path="/static")
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World! peepee poopoo'
    
    from . import DatabaseManager
    DatabaseManager.init_app(app)
    app.register_blueprint(DatabaseManager.dbBP)
    
    from . import DreamPage
    app.register_blueprint(DreamPage.bp)
    
    from . import Home
    app.register_blueprint(Home.bp)
    
    from . import TagManager
    app.register_blueprint(TagManager.bp)
    
    from . import Statistics
    app.register_blueprint(Statistics.bp)
    
    from . import TimeManager
    
    return app