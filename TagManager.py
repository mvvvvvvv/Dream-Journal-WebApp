# Import libraries
import sqlite3, json

# Importing Blueprint
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)


# importing from our file
from flaskr.DatabaseManager import open_database

bp = Blueprint('TagManager', __name__, url_prefix='/tag_editor')

## TAG EDITOR CODE
@bp.route('',methods=("GET", "POST",))
def tag_editor():
    if request.method == "POST":
        data = json.loads(request.values["data"])
        # All the different possible types of requests.
        if(data["type"] == "tag_cat_merge"):
            tag_cat_merge(data)
        elif(data["type"] == "tag_merge"):
            tag_merge(data)
        elif(data["type"] == "new_tag"):
            new_tag(data)
        elif(data["type"] == "new_cat"):
            new_tag_cat(data)
        elif(data["type"] == "delete_tag"):
            delete_tag(data)
        elif(data["type"] == "delete_cat"):
            delete_cat(data)
        elif(data["type"] == "tag_rename"):
            rename_tag(data)
        elif(data["type"] == "cat_rename"):
            rename_cat(data)
    return render_template('dream/TagManager.html', tag_categories = [dict(e) for e in list_tag_cats()], tags=list_tags())

def tag_cat_merge(data):
    # There are a few things we need to do to successfully merge tag categories
    # 1) Record all the tags inside of these tag categories, and their associated matches
    # 2) Delete original tag categories, and make a new one with the new name (because of on-delete cascade this will destroy all of the tags and tag matches)
    # 3) Make copies of old tags attached to new tag category
    # 4) Make copies of old tag_matches attached to new tags
    
    #1) & 2)
    # Recording the tags
    db = open_database()
    db.execute("PRAGMA foreign_keys = 1")
    cur = db.cursor()
    tags = []
    for key in data["data"]:
        if(data["data"][key]):
            tags += tags_with_category(key)
            cur.execute("DELETE FROM tag_categories WHERE uid = ?", (key,))
    
    # Recording the tag matches
    tag_matches = {}
    for tag in tags:
        tag_matches[tag["uid"]] = tag_id_matches(tag["uid"])
    
    # 2) again, making the new tag category
    cur.execute('''INSERT INTO tag_categories (tag_category_name)
                             VALUES(?)''', (data["name"],))
    temp = cur.execute("SELECT last_insert_rowid()")
    for row in cur:
        new_tag_cat_id = row[0]
    #print("New tag cat id: ", new_tag_cat_id)
    
    # 3)
    # Setting up a list of the new tags
    new_tags = []
    for tag in tags:
        cur.execute("""INSERT INTO tags (tag_name, tag_cat)
                            VALUES(?, ?)""", (tag["tag_name"], new_tag_cat_id,))
        cur.execute("SELECT last_insert_rowid()")
        for row in cur:
            new_tags.append(row[0])
    
    #print(new_tags)
    # 4)
    for i in range(0, len(tags)):
        for tag_match in tag_matches[tags[i]["uid"]]:
            cur.execute("""INSERT INTO tag_matches (entry_id, tag_id)
                                    VALUES(?, ?)""", (tag_match["entry_id"], new_tags[i],))
                                    
    db.commit()
    return
    
def tag_merge(data):
    # There are a few things we need to do to successfully merge tags
    # 1) Record and de-duplicate all the tag matches inside the tags + new name
    # 2) Delete original tags, and make a new one with the new name(because of on-delete cascade this will destroy all of the tag matches)
    # 3) Make copies of old tag_matches attached to new tag
    
    # Opening the database and enabling cascading
    db = open_database()
    db.execute("PRAGMA foreign_keys = 1")
    cur = db.cursor()
    
    # 1) + 2)
    tag_matches = set()
    for tag in data["data"]:
        if data["data"][tag]:
            # The tag has been selected, let's add its matches to the set
            for tag_match in tag_id_matches(tag):
                tag_matches.add(tag_match["entry_id"])
            cur.execute("""DELETE FROM tags WHERE uid = ?""", (tag,))
    
    # 2) part 2, making a new tag
    cur.execute("""INSERT INTO tags (tag_name, tag_cat)
                                    VALUES(?,?)""", (data["name"], data["tag_cat"],))
    temp = cur.execute("SELECT last_insert_rowid()")
    for row in cur:
        tag_uid = row[0]
    
    # And reattaching the tag_matches
    for dream_id in tag_matches:
        cur.execute("""INSERT into tag_matches (entry_id, tag_id)
                                            VALUES(?, ?)""", (dream_id,tag_uid,))
    
    db.commit();
    return

def new_tag(data):
    #make new tag inside an existing tag category
    #1 check what category
    #2 check what name
    #3 add new SQL row in tags with the tag cat attached
    db = open_database()
    cur = db.cursor()
    
    cur.execute("""INSERT into tags (tag_name, tag_cat)
                                    VALUES(?, ?)""", (data["name"], data["tag_cat"],))
                                    
    db.commit();
  
    return

def new_tag_cat(data):
    #adding new tag category - only need name
    db = open_database()
    cur = db.cursor()
    
    #print(data)
    
    cur.execute("""INSERT into tag_categories (tag_category_name)
                                               VALUES(?)""", (data["name"],))
                                               
    db.commit();
    
    return
    
def delete_tag(data):
    #just have to delete the tag and cascade
    db = open_database()
    db.execute("PRAGMA foreign_keys = 1")
    cur = db.cursor()
    
    for tag in data["tags"]:
        if data["tags"][tag] == 1:
            cur.execute("""DELETE FROM tags WHERE uid = ?""",(tag,))
            
    db.commit();
        
    return
    
def delete_cat(data):
    db = open_database()
    db.execute("PRAGMA foreign_keys = 1")
    cur = db.cursor()
    
    cur.execute("""DELETE FROM tag_categories WHERE uid = ?""",(data["cat"]["uid"],))
    
    db.commit();
    
def rename_tag(data):
    db = open_database()
    cur = db.cursor()
    
    cur.execute("""UPDATE tags SET tag_name = ? WHERE uid = ?""", (data["name"], data["uid"]))
    db.commit();
    
    return
    
def rename_cat(data):
    db = open_database()
    cur = db.cursor()
    
    cur.execute("""UPDATE tag_categories SET tag_category_name = ? WHERE uid = ?""", (data["name"], data["uid"]))
    db.commit();
    
    return
        
    
## UTILITY FUNCTIONS
    
def return_binned_tags(dream_uid):
    """Takes in a dream_uid
    Outputs a dictionary: (tag_group_name, tag_group_id) -> list((tag_name, tag_id))
    """
    
    # Initial variable setup.
    db = open_database()
    
    # Grabbing the tags that belong to this dream.
    tag_matches = db.execute("SELECT tag_id FROM tag_matches WHERE entry_id = ?", (dream_uid,)).fetchall()
    print([dict(e) for e in tag_matches]);
    
    # Associating tags with tag_category
    tag_cat_names = {}
    return_dict = {}
    for tag in tag_matches:
        tag_info = db.execute("SELECT tag_cat, tag_name FROM tags WHERE uid = ?", (tag["tag_id"],)).fetchone()
        
        # Do we already know about the associated tag_group?
        ################## FIX THIS STUPID BULLSHIT LATER, NOTE TO SELF, THIS BULLSHIT IS STILL UNFIXED, BUT NOW WE AT LEAST KNOW ITS CONTAINED HERE COMPLETELY
        if tag_info["tag_cat"] not in tag_cat_names:
            tag_cat_info = db.execute("SELECT tag_category_name FROM tag_categories WHERE uid = ?", (tag_info["tag_cat"],)).fetchone()
            tag_cat_names[tag_info["tag_cat"]] = tag_cat_info["tag_category_name"]
            return_dict[(tag_cat_names[tag_info["tag_cat"]], tag_info["tag_cat"])] = list()
            
        # Shoving all this info into our return dictionary
        return_dict[(tag_cat_names[tag_info["tag_cat"]], tag_info["tag_cat"])].append((tag_info["tag_name"], tag["tag_id"]))
    return return_dict
    
# Same as return binned tags but using ids
def return_id_binned_tags(dream_uid):
    # Initial variable setup.
    db = open_database()
    
    # Grabbing the tags that belong to this dream.
    tag_matches = db.execute("SELECT * FROM tag_matches WHERE entry_id = ?", (dream_uid,)).fetchall()
    
    return_dict = {}
    for tag in tag_matches:
        tag_cat_info = db.execute("SELECT tag_cat FROM tags WHERE uid = ?", (tag["tag_id"],)).fetchone()
        if tag_cat_info["tag_cat"] not in return_dict:
            return_dict[tag_cat_info["tag_cat"]] = list()
        return_dict[tag_cat_info["tag_cat"]].append(tag["tag_id"])
    
    return return_dict

def dreams_with_tag(tag_uid):
    """Takes in a tag uid
    Outputs an iterator of dreams with that tag attached, formatted as sqlite row objects
    """
    
    # Initial variable setup
    db = open_database()
    
    # Creating an iterator of uids belonging to dreams with tag
    dream_uids = map(lambda x: x["entry_id"], db.execute("SELECT * FROM tag_matches WHERE tag_id = ?", (tag_uid,)).fetchall())
    
    # Creating dream list
    dream_list = list()
    
    # Populating and returning dream list
    for uid in dream_uids:
        dream_list.append(db.execute("SELECT * FROM entries WHERE uid = ?", (uid,)).fetchone())
    
    return dream_list
    
def tags_with_category(tag_cat_uid):
    """Takes in a tag_cat_uid
    Outputs an iterator of tags in that category, formatted as sqlite row objects
    """
    
    # Initial variable setup
    db = open_database()
    
    # Returning the iterator of tags in supplied category
    return db.execute("SELECT * FROM tags WHERE tag_cat = ?", (tag_cat_uid,)).fetchall()
    
def list_tag_cats():
    """ Returns an interator of all current tag categories"""
    # Opening the databsae
    db = open_database()
    
    # Returning said list
    return db.execute("SELECT * FROM tag_categories ORDER BY uid ASC").fetchall()

def list_tags():
    """ Returns an iterator of all tags """
    # Opening the database
    db = open_database()
    
    # Returing said iterator
    return [dict(e) for e in db.execute("SELECT * FROM tags ORDER BY uid ASC").fetchall()]
    
def tag_id_matches(tag_id):
    # Opening the databse
    db = open_database()
    
    # Returning a list of matches for a given tag
    return [dict(e) for e in db.execute("SELECT * FROM tag_matches WHERE tag_id = ?", (tag_id,)).fetchall()]