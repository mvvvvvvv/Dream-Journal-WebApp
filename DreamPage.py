# -*- coding: utf-8 -*-
"""
Created on Mon Apr 27 20:07:18 2020

@author: Maria
"""

# importing libraries
import functools
import pytz
import datetime
import re
import json

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)

# importing from our file
from flaskr.DatabaseManager import open_database, edit_in_editor, new_blank_dream, dream_row_formatter, month_dream_returner
from flaskr.TagManager import return_binned_tags, list_tag_cats, list_tags, return_id_binned_tags
from flaskr.TimeManager import formatted_date, cur_utc_time, month_day_getter

bp = Blueprint('dream', __name__, url_prefix='/dream')

#Make dream page
@bp.route('/<int:dream_id>',methods=('GET',))
def dream_read(dream_id):
    
    # Initial variable setup
    db = open_database()
    
    # Grab the dream with supplies uid
    dream = db.execute("SELECT * FROM entries WHERE uid = ?", (dream_id,)).fetchone()
    dream = dream_row_formatter(dream)
    
    
    # Local time formatting
    date = formatted_date(dream)
    
    # Tag grabber
    binned_tags = return_binned_tags(dream_id)
    
    if dream == None:
        pass
    else:
        return render_template('dream/dream.html',dream = dream, date=date, dream_id = dream_id, binned_tags = binned_tags)

# New dream creator
@bp.route("/new", methods=("GET","POST",))
def new_dream_page():
    if request.method == "GET":
        return render_template("dream/dreamEditor.html", has_dream=False, tag_categories=[dict(e) for e in list_tag_cats()], tags=list_tags(), binned_tags={})
    elif request.method == "POST":
        # Make and go to new dream
        dream_id = new_blank_dream()
        return dream_edit_request_handler(dream_id, request)
        
        

# Dream editing page
@bp.route("/<int:dream_id>/edit", methods=("GET", "POST",))
def dream_editor_page(dream_id):
    if request.method == "GET":
        db = open_database()
        dream = db.execute("SELECT * FROM entries WHERE uid = ?", (dream_id,)).fetchone()
        
        # Tag category iterator
        tag_cats = [dict(e) for e in list_tag_cats()]
        #print(tag_cats)
        
        # Tag list
        tags = list_tags()
        #print(tags)
        
        # Tags in dream
        binned_tags = return_id_binned_tags(dream_id)
        
        
        return render_template("dream/dreamEditor.html",has_dream=True,dream=dream, tag_categories=tag_cats, tags=tags, binned_tags=binned_tags)
    elif request.method == "POST":
        # Edit and return dream page
        return dream_edit_request_handler(dream_id, request)
        
        

def dream_edit_request_handler(dream_id, request):
    # Sending data to database
    edit_in_editor(dream_id, request)
     
    # Return dream page
    return redirect("/dream/{}".format(dream_id))

# Makes page for the calendar to get info from - not really for human, it looks ugly lol
@bp.route('/calendar_info_page/<int:year>/<int:month>',methods=('GET',))
def calendar_info_page(year,month):
    dream_info = month_dream_returner(month,year)
    dream_dict = [dict(row) for row in dream_info]
    for row in dream_dict:
        day = int(month_day_getter(row["creation_time"]))
        row["day"] = day
    
    dream_info_str = json.dumps(dream_dict)
    return dream_info_str