# importing libraries
import functools
import pytz
import datetime
import sqlite3
import math

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)

# importing from our file
from flaskr.DatabaseManager import open_database, dream_row_formatter
from flaskr.TimeManager import formatted_date

bp = Blueprint('home', __name__, url_prefix='/home')

page_size = 30

@bp.route("/")
def last_list_page():
    # Returning the last page
    return list_entries(get_last_page())

@bp.route('/<int:page_number>')
def list_entries(page_number):
    
    # Grabbing dreams from database
    db = open_database()
    db.row_factory = sqlite3.Row
    min_id = 1 + (page_number-1)*page_size
    max_id = page_number*page_size
    dreams = db.execute("""SELECT * FROM entries WHERE uid BETWEEN ? and ?
                       ORDER BY uid ASC""", (min_id,max_id,)).fetchall()
    dreams = list(map(dream_row_formatter, dreams))
    print([e["entry_type"] for e in dreams])
    
    
    
    # Getting the dates for each dream
    dates = [formatted_date(dream) for dream in dreams]
    
    return render_template("dream/home.html", zipped_dreams=zip(dreams,dates),
                                              page_number=page_number,
                                              last_page_number=get_last_page())
    dream["entry_type"] = map(int, zip_dream[0]["entry_type"].strip('][').split(', '))
    print(dream["entry_type"])
    print(type(dream["entry_type"]))


### AUX functions ###
def get_last_page():
    # First, let's find the id of the last entry
    db = open_database()
    last_entry = db.execute("""SELECT uid from entries ORDER BY uid DESC LIMIT 1""").fetchone()['uid']
    
    # Calculating the dream number
    last_page_number = math.ceil(last_entry/page_size)
    
    return last_page_number