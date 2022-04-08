# -*- coding: utf-8 -*-
"""
Created on Thu Apr 16 17:10:36 2020

@author: Maria
"""

# This app will have several functions:
    #1 read original database
    #2 create new database
    #3 Tags
    #4 Export stats to an easy to use file for statistical analysis
    #5 Functions to call for data

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!    
#SETTING UP OUR DATABASE
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 
   
import sqlite3
import datetime
import pytz
import os
import re
import json
import click
from flask import current_app, g, Blueprint
from flask.cli import with_appcontext
from flaskr.TimeManager import cur_utc_time, month_sec_range
from bs4 import BeautifulSoup

#Making our Database Manager
    
#setting up new database from old database
def new_setup(old_database):
    
    cur = g.db.cursor()
    #setting up new database
    #creating tables
    cur.execute('''CREATE TABLE entries(
        uid INTEGER PRIMARY KEY,
        title TEXT,
        creation_time REAL,
        modified_time REAL,
        text TEXT NOT NULL,
        start_time TEXT,
        end_time TEXT,
        word_count INTEGER,
        entry_type TEXT,
        notes TEXT) ''')
    
    #TAG CATEGORIES
    cur.execute('''CREATE TABLE tag_categories(
        uid INTEGER PRIMARY KEY,
        tag_category_name TEXT)''')
    
    #cur.execute runs the command that we put in, here we are using it to create tables

    #TAGS
    cur.execute('''CREATE TABLE tags(
        uid INTEGER PRIMARY KEY,
        tag_name TEXT NOT NULL,
        tag_cat INTEGER,
        FOREIGN KEY(tag_cat) REFERENCES tag_categories(uid)
            ON DELETE CASCADE
            ON UPDATE CASCADE)''')
    
    #MATCHING TAGS to the dreams
    cur.execute('''CREATE TABLE tag_matches(
        uid INTEGER PRIMARY KEY,
        entry_id INTEGER,
        tag_id INTEGER,
        FOREIGN KEY(tag_id) REFERENCES tags(uid)
            ON DELETE CASCADE
            ON UPDATE CASCADE,
        FOREIGN KEY(entry_id) REFERENCES entries(uid)
            ON DELETE CASCADE
            ON UPDATE CASCADE)''')   
    
    oldcon = sqlite3.connect(old_database)
    #cursor makes it so we can run code
    oldcur = oldcon.cursor()
    oldcur.execute("SELECT entryCategory, entryContent, entryCreatedDate, entryModifiedDate, entryMoodId FROM tableDiary ORDER BY entryCreatedDate ASC;")
    
    # Setting up our tag dictionaries
    exist_tag_cat = {}
    exist_tag = {}
    
    for row in oldcur:
        #using formatting function to get all metadata
        print(row[2])
        formatted_data = meta_data_formatter(row[1])
        try:
            temp_create_date = float(row[2])/1000
        except ValueError:
            print("There's an error, whoops :'(")
            print("Creation date = ", row[2])
            exit()
        
        #filling in tag_categories
        temp_tag_dict = formatted_data["tags"]
        
        create_dream({"title": formatted_data["title"],
                      "text": formatted_data["dream_text"], 
                      "creation_time":temp_create_date, 
                      "edited_time":row[3]/1000, 
                      "word_count":formatted_data["word_count"],
                      "start_time":formatted_data["sleep_times"][0],
                      "end_time": formatted_data["sleep_times"][1],
                      "entry_type": str([-row[4]]),
                      "notes": formatted_data["notes"]}, temp_tag_dict)
        
    #saving the file
    g.db.commit()
        
  
  
def create_dream(dream_info, tag_metadata):
    ### Listing the pieces of dream_info we need, and making sure they're populated
    possible_dream_info = ["title", "text", "creation_time", "edited_time", "word_count", "start_time", "end_time", "entry_type", "notes"]
    for info in possible_dream_info:
        if info not in dream_info:
            dream_info[info] = ""
    
    
    ### Adding this dream into the database:
    db = open_database()
    cur = db.cursor()
    cur.execute('''INSERT INTO entries (title, text, creation_time, modified_time, word_count, start_time, end_time, entry_type, notes)
                         VALUES(?,?,?,?,?,?,?,?,?)''', (dream_info["title"], dream_info["text"], dream_info["creation_time"], dream_info["edited_time"], dream_info["word_count"], dream_info["start_time"], dream_info["end_time"], dream_info["entry_type"], dream_info["notes"]))
    
    # And gettings its new id
    cur.execute("SELECT last_insert_rowid()")
    for row in cur:
        entry_id = row[0]
            
    
    ### Dealing with the tags
    # Getting a list of all existing categories and tag, tag_cat pairs
    exist_tag_cat = {}
    cur.execute('''SELECT * FROM tag_categories''')
    for row in cur:
        exist_tag_cat[row["tag_category_name"]] = row["uid"]
        
    exist_tag = {}
    cur.execute('''SELECT * FROM tags''')
    for row in cur:
        exist_tag[(row['tag_name'],row['tag_cat'],)] = row['uid']
    
    #checking if category exists, if not, adding it
    for tag_cat in tag_metadata:
        tag_cat_orig = tag_cat
        tag_cat = tag_cat.lower().strip()
        # Checking if tag_category is already in our database
        if tag_cat not in exist_tag_cat:
            # If it's not then add it first
            cur.execute('''INSERT INTO tag_categories (tag_category_name)
                             VALUES(?)''', (tag_cat,))
            cur.execute("SELECT last_insert_rowid()")
            for row in cur:
                exist_tag_cat[tag_cat] = row[0]
                
        tag_cat_id = exist_tag_cat[tag_cat]
    
        # Looping over all of the tags we have for this dream in this category  
        for tag_name in tag_metadata[tag_cat_orig]:
            tag_name = tag_name.lower().strip()
            # Checking if tag, tag_category pair is already in database
            if (tag_name, tag_cat_id,) not in exist_tag:
                # If not, let's add it
                cur.execute('''INSERT INTO tags (tag_name, tag_cat)
                                 VALUES(?,?)''', (tag_name, tag_cat_id))
                cur.execute("SELECT last_insert_rowid()")
                for row in cur:
                    exist_tag[(tag_name,tag_cat_id,)] = row[0]
            
            tag_id = exist_tag[(tag_name,tag_cat_id,)]
            
            # Now let's add our (entry, tag) pair to the database
            cur.execute("""INSERT INTO tag_matches(entry_id, tag_id)
                             VALUES(?,?)""", (entry_id, tag_id,))
    
    # Commiting our results
    db.commit()
    
    
# Dream row object dictionarifier
def dream_row_formatter(dream):
    # Turning this into a dictionary
    dream = dict(dream)
    
    # Converting the entry list string into a real list
    #print("THIS IS THE ENTRY TYPE:",dream["entry_type"])
    if dream["entry_type"] == '':
        dream["entry_type"] = [0]
    else:
        dream["entry_type"] = list(map(int, dream["entry_type"].strip('][').split(',')))
    
    return dream
    
        
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!    
#METADATA FINDER
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 
     

           
def meta_data_finder(entry_text):
    vivid_exist = re.search("-Vividness:", entry_text)
    
    if vivid_exist is not None:
        #Getting the title
        if entry_text[0] == "-":
            title = ""
            title_splitter = [0, entry_text]
        else:
            title_splitter = entry_text.split(sep="\n", maxsplit = 1)
            title = title_splitter[0]
            
        #seperating dream text
        
        
        not_title = title_splitter[1]
        dream_reg = re.search("-Dream Details:", not_title)
        vivid_reg = re.search("-Vividness:", not_title)
        top_split = not_title[0:dream_reg.start(0)]
        dream = not_title[dream_reg.end(0):vivid_reg.start(0)]
        bottom_split = not_title[vivid_reg.start(0):len(not_title)]
        
        metadata_dict = {}
        
        for string in [top_split, bottom_split]:
            regex_results = re.finditer("-([a-zA-Z ]*):", string)
            
            metadata_title = []
            match_start = []
            match_end = []
            
            #finding the metadata template labels
            for match in regex_results:
                metadata_title.append(match.group(1))
                match_start.append(match.start(0))
                match_end.append(match.end(0))
            
            #finding the metadata content
            for i in range(0, len(match_start)-1):
                metadata_dict[metadata_title[i]] =  string[match_end[i]:match_start[i+1]].strip()
                
            #finding last metadata title+content
            metadata_dict[metadata_title[-1]] = string[match_end[-1]:len(string)].strip()
            
        return {"title":title.strip(), "dream_text": dream.strip(), "metadata":metadata_dict}
    
    else:
        metadata_dict = {}
        dream = entry_text.strip()
        return {"title":"", "dream_text": dream, "metadata":metadata_dict}
    
    
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!    
#FORMATTING METADATA
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 
  
def meta_data_formatter(entry_text):
    sep_text_data = meta_data_finder(entry_text)
    
    
    #word count
    word_count = 1
    

    word_count_reg = re.finditer("\s[a-zA-Z ]", sep_text_data["dream_text"])
    
    for match in word_count_reg:
        word_count = word_count + 1
        
    formatted_dict = {}
    formatted_dict["word_count"] = word_count
    
    #time to number format
    # dictionary to look at: sep_text_data = {"title":"", "dream_text": dream, "metadata":metadata_dict}

    only_metadata = sep_text_data["metadata"]
    
    # running regex's if we can
    if "Went to bed" in only_metadata:
        regex_sleep = re.search("(\d+:*\d+)", only_metadata["Went to bed"])
    else:
        regex_sleep = None
    if "Woke up" in only_metadata:
        regex_wake = re.search("(\d+:*\d+)", only_metadata["Woke up"])
    else:
        regex_wake = None
        
    
    if regex_sleep and regex_wake is not None:
        sleep_times = [regex_sleep.group(0), regex_wake.group(0)]
    elif regex_sleep is not None:
        sleep_times = [regex_sleep.group(0), ""]
    elif regex_wake is not None:
        sleep_times = ["", regex_wake.group(0)]
    else:
        sleep_times = ["",""]
    
    #put title, text and sleep times into a new dictionary
    formatted_dict["title"] = sep_text_data["title"]
    formatted_dict["dream_text"] = sep_text_data["dream_text"]
    formatted_dict["sleep_times"] = sleep_times
    
    #seperate notes from metadata
    if "NOTES" in only_metadata:
        formatted_dict["notes"] = only_metadata["NOTES"]
    else:
        formatted_dict["notes"] = ""
    
    #remove time, title, notes and text from old dictionary, deleting useless metadata
    # Also deleting things we've built a new place for
    
    for key in ["Went to bed", "Woke up", "NOTES", "Dream number", "Awareness"]:
        if key in only_metadata:
            del only_metadata[key]
    
    
    #add cleaned up metadata to formatted_dict
    formatted_dict["metadata"] = only_metadata
    
    #separating tags
    split_tags = tag_separator(formatted_dict)
    
    #deleting metadata from dictionary + adding new metadata
    del formatted_dict["metadata"]
    formatted_dict["tags"] = split_tags
    
    
        
    return formatted_dict
    

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!    
#SEPERATING TAGS
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 

def tag_separator(tag_metadata_input):
    tag_metadata = tag_metadata_input["metadata"]
    
    split_tags = {}
    
    for key, string in tag_metadata.items():
        split_tags[key] = re.split(",", string)
        
    return split_tags
    
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!    
#SPECIAL FUNCTIONS FOR MAKING A BLANK DREAM/EDITING A DREAM IN SPECIFIC WAYS
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 

def new_blank_dream():
    # Creates a new empty dream and returns its uid
    db = open_database()

    # Creating my new dream
    db.execute("""INSERT INTO entries (creation_time, modified_time, text) VALUES(?,?,?)""",
               (cur_utc_time(), cur_utc_time(), "",))
    
    db.commit()
    
    # Getting that dreams id
    dream_id = db.execute("SELECT last_insert_rowid()")
    for row in dream_id:
        i = row[0]
        
    return (i)
    
def edit_in_editor(dream_id, request):
    # Fetching dream info from request
    text = request.form["text"]
    title = request.form["title"]
    notes = request.form["notes"]
    lucid_level = request.form["lucid_level"]
    sleep_time = request.form["sleep_time"]
    wake_time = request.form["wake_time"]
    modified_time = cur_utc_time()
    #word count
    word_count = dream_word_count(text)
    
    
    
    # Rewriting the dream
    db = open_database()
    db.execute("""UPDATE entries
                SET text = ?,
                    notes = ?,
                    modified_time = ?,
                    title = ?,
                    word_count = ?,
                    entry_type = ?,
                    start_time = ?,
                    end_time = ?
                   WHERE uid = ?""", (text, notes, modified_time, title, word_count, lucid_level, sleep_time, wake_time, dream_id,))
    db.commit()
    
    # Editing tags
    tags_selected = json.loads(request.form["tags_selected"])
    tags_changed = json.loads(request.form["tags_changed"])

    for tag_cat in tags_changed:
        for tag in tags_changed[tag_cat]:
            if(tags_changed[tag_cat][tag]):
                if(tags_selected[tag_cat][tag]):
                    db.execute("""INSERT INTO tag_matches(entry_id, tag_id) VALUES(?,?)""", (dream_id, int(tag),))
                else:
                    db.execute("""DELETE FROM tag_matches WHERE entry_id = ? AND tag_id = ?""", (dream_id, int(tag),))
    db.commit()
    return

    
def dream_word_count(dream):
    word_count = 1
    word_count_reg = re.finditer("\s[a-zA-Z ]", dream)
    for match in word_count_reg:
        word_count = word_count + 1
            
    return(word_count)
    
    
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!    
#OPENING OR CLOSING DATABASE
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 

def open_database():
    if "db" not in g:
        #connecting the database ro the app
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        
    return g.db

def close_database(e=None):
    db = g.pop("db", None)
    
    if db is not None:
        db.close()
        
        
##### Command hack
dbBP = Blueprint('djwifioewafehwabwuigqfuq7aw8g78qukasifgukdsbkjchvbjhawegfyufagwfwyaugq27f3qgyef', __name__)
        
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!    
#INITIALISING DATABASE
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 

def init_database(old_database):
    open_database()
    new_setup(old_database)
    
@dbBP.cli.command("initdb")    
@click.argument("old_database")
@with_appcontext
def init_database_commands(old_database):
    init_database(old_database)
    click.echo("Done!")
    
    
def init_app(app):
    app.teardown_appcontext(close_database)
    app.cli.add_command(init_database_commands)

#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!    
#ONE NOTE DREAM IMPORTER
#!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! 
@dbBP.cli.command("init_one_note")    
@click.argument("mht_file")
@with_appcontext
def import_one_note(mht_file):
    html_doc = open(mht_file,"r").read()
    title_test = open("test.txt","w")
    
    #Looking at the mht file using BeautifulSoup
    soup = BeautifulSoup(html_doc, 'html.parser')
    
    # Loop over the contents, finding what we need
    for element in soup.body:
        if element.name == "div" and element.div != None:
            title = element.div.contents[1].p.contents[0]
            date = element.div.contents[3].p.contents[0]
            time = element.div.contents[3].contents[3].contents[0]
            whole_dream = element.div.contents[5].contents
            
            
            #formatting the title
            split_title = title.split(sep=".", maxsplit = 1)
            formatted_title = split_title[1].replace("\n", " ")
            
            #formatting the date
            split_date = date.split(sep=",", maxsplit = 1)
            formatted_date = split_date[1]
            
            
            
            
            #code_to_type = {"FF99FF": "meta",
            #                "33CCFF": "lucid",
            #                "A5A5A5": "notes",
            #                "#AEABAB": "notes"}
            
            entry_text = ""
            only_metadata = []
            
            formatted_notes = ""
            
            for para in whole_dream:
                para_colour = colour_finder(str(para))
                
                NOTES_exist = re.search("NOTES:", str(para))
                
                span_exist = re.search("<span", str(para))

                
                
                #colours = re.search("colour:#\S*", str(para))
                #print(colours)
                
                try:
                    print(para.contents, str(para))
                    error = False
                    
                except:
                    error = True
                    
                if span_exist is None and error is False:
                    if NOTES_exist is not None:
                        split_notes = para.contents[0].split(sep=":", maxsplit = 1)
                        formatted_notes = split_notes[1]
                        print("NOTES:", formatted_notes)
                        
                    elif para_colour == "pink":
                        only_metadata.append(str(para.contents[0]))
                    
                    elif para_colour == "blue" or "gray" or "indigo":
                        entry_text = entry_text + '<p' + colour_html_assigner(para_colour) +'>' + str(para.contents[0]) + '</p>'
                        
                    else:
                        entry_text = entry_text + '<p>' + str(para.contents[0]) + '</p>'
                elif span_exist is not None and error is False:
                    entry_text = entry_text + span_destroyer("".join(str(i) for i in para.contents))
                else:
                    print("skipped!")
                    
                entry_text = entry_text.replace("\n", " ")
                entry_text = entry_text.replace("&quot;", '"')
                entry_text = entry_text.replace("â€™", "'")
                
                    
            print("DREAM:", entry_text)

            converted_date = one_note_date_converter(formatted_date, time)
            sec_since_epoc = (datetime.datetime.strptime("{0:02d}:{1:02d}:{2:02d}:{3:02d}:{4:04d}:{5}".format(*converted_date), "%M:%H:%d:%m:%Y:%p")-datetime.datetime.utcfromtimestamp(0)).total_seconds()
            print(sec_since_epoc)
            ### Formatting for create_dream
            dream_info = {"title": formatted_title, "text": entry_text, "word_count": dream_word_count(entry_text), "notes": formatted_notes, "creation_time":sec_since_epoc, "edited_time":sec_since_epoc}
            
            # Adding relevant metadata into dream_info
            tags = onenote_metadata([e.replace("\n", " ").strip(" -") for e in only_metadata])
            dream_info_metadata = [("Went to bed","start_time",),  ("Woke up","end_time",)]
            for info in dream_info_metadata:
                if info[0] in tags:
                    dream_info[info[1]] = tags[info[0]][0]
                    tags.pop(info[0])
            
            # Actually create the dream
            create_dream(dream_info, tags)


# Seperates out onenote_metadata and puts it in a more paletable form
def onenote_metadata(unformatted_metadata):
    # Output dictionary:
    metadata_dict = {}
    
    # Figuring out which type the unformatted_metadata belongs to:
    for metadata in unformatted_metadata:
        try:
            # Grabbing the metadata type and content
            mtype, mcontent = metadata.split(":", 1)
            mtype = mtype.strip()
            mcontent = mcontent.strip()
            
            
            # Adding it to the metadata dictionary
            metadata_dict[mtype] = mcontent.split(",")
        except ValueError:
            print("METADATA ERROR:", metadata)
    
    return metadata_dict
    
#this was only used to import my dreams for one note
def one_note_date_converter(date, time):
    months_dict = {"January":1, "February":2, "March":3, "April":4, "May":5, "June":6, "July":7, "August":8, "September":9, "October":10, "November":11, "December":12}
    
    split_date = date.split()
    day = int(split_date[0])
    unformatted_month = split_date[1]
    year = int(split_date[2])
    month = months_dict[unformatted_month]
    
    split_AMPM = time.split()
    AMPM = split_AMPM[1]
    split_times = split_AMPM[0]
    
    minutes = int((split_times.split(":"))[1])
    


    hours = int((split_times.split(":"))[0])
    
    print("Day = ",day )
    print("Month = ",month )
    print("Year = ",year )
    print("Hours = ",hours )
    print("Minutes = ",minutes )
    print(AMPM)
    
    return [minutes,hours,day,month,year,AMPM]

#for one note as well - fixes formatting
def span_destroyer(text):
    found_spans = re.findall('<span [a-zA-Z=:\#\'\"0-9-]*>', text)
    span_number = len(found_spans)
    
    i = 0
    
    while i < span_number:
        found_spans = re.finditer('<span [a-zA-Z=:\#\'\"0-9-]*>', text)
        
        print(span_number)
        spans_list = [ass for ass in found_spans]
        
        print(spans_list)
        colour = colour_finder(spans_list[0].group(0))
        print(colour)
        text = text.replace(spans_list[0].group(0), "<span"+colour_html_assigner(colour)+">" ,1)
        i = i+1

    return text
    
#for one note - converts the colours I used into a simple format for my app
def colour_finder(text):
    pink_exist = re.search("#FF99FF", text)
    
    indigo_exist = re.search("#2E75B5", text)
    
    blue_exist = re.search("#33CCFF", text)
    
    gray_exist = re.search("#A5A5A5", text)
    gray_exist2 = re.search("#AEABAB", text)
    gray_exist3 = re.search("#757070", text)
    
    if gray_exist or gray_exist2 or gray_exist3 is not None:
        return"gray"
    elif indigo_exist is not None:
        return"indigo"
    elif pink_exist is not None:
        return "pink"
    elif blue_exist is not None:
        return "blue"
    else:
        return "black"
    
#For one note again - converting the colours I found to the correct format
def colour_html_assigner(colour):
    if colour == "gray":
        return ' class = "notes_style"'
    elif colour == "indigo":
        return ' class = "semi_lucid_style"'
    elif colour == "blue":
        return ' class = "lucid_style"'
    else:
        return ""
        
#for the calendar - finds the range of seconds in a specific month (epoch time)
def month_dream_returner(month,year):
    sec_range = month_sec_range(month, year)
    db = open_database()
    month_dreams = db.execute('''SELECT creation_time, uid, entry_type, word_count FROM entries 
                                 WHERE creation_time <= ? AND creation_time >= ?''',[sec_range[1],sec_range[0]]).fetchall()
    return month_dreams