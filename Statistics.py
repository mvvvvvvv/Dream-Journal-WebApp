from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)

bp = Blueprint('Statistics', __name__, url_prefix='/stats')

from flaskr.DatabaseManager import open_database
import json

#Function that makes our python into a page on the app :)
@bp.route('',methods=("GET",))
def stats_viewer():
    cur_stats = stats()
    return render_template('dream/Statistics.html', stats=cur_stats)
    
#function to make the stats dictionary (info for the page)
def stats():
    stat_dict = {"total_dreams":total_dreams(),"total_lucids":total_lucids(),"bar_chart":bar_chart(),"word_count":word_count_max(),}
    return stat_dict

#counts the total dreams in the app
def total_dreams():
    db = open_database()
    total_entries = db.execute("select count(*) from entries").fetchone()[0]
        
    print(total_entries)
    
    return total_entries
    
#counts the total lucids (not including semi lucids)
def total_lucids():
    db = open_database()
    entry_types = db.execute("select entry_type from entries").fetchall()
    
    total_l = 0
    total_one = 0
    total_two = 0
    total_three = 0
    total_four = 0
    total_five = 0
    night_max = 0
    lucid_nights = 0
    
    #looping through all the elements in the entry_type list (since there can be multiple lucids in one night)
    for e in entry_types:
        for n in e:
            n = n.replace("[","")
            n = n.replace("]","")
            li = list(n.split(","))
            
            error = False
            night = 0
            for x in li:
                try:
                    x = int(x)
                except:
                    error = True

                if x is not None and error is not True and x >= 1:
                    total_l = total_l+1
                    night = night+1
                    
                    if x == 1:
                        total_one = total_one+1
                    elif x == 2:
                        total_two = total_two+1
                    elif x == 3:
                        total_three = total_three+1                
                    elif x == 4:
                        total_four = total_four+1      
                    elif x == 5:
                        total_five = total_five+1
                    else:
                        print("STRANGE NUMBER!:", x)
                        
            if night_max < night:
                night_max = night
            if night > 0:
                lucid_nights = lucid_nights+1
                        
        total_l_dict = {"total_l":total_l, "total_one":total_one,"total_two":total_two,"total_three":total_three,"total_four":total_four,"total_five":total_five,"night_max":night_max, "lucid_nights":lucid_nights}            
    return total_l_dict

#making the bar chart :)
def bar_chart():

    t_l = ""
    t1 = ""
    t2 = ""
    t3 = ""
    t4 = ""
    t5 = ""
    ln = ""
    
    tnl = ""
    
    symbol = "\u2610"
    lucid_data = total_lucids()
    t_l = round(lucid_data["total_l"]/10) * symbol
    t1 = round(lucid_data["total_one"]/10) * symbol
    t2 = round(lucid_data["total_two"]/10) * symbol
    t3 = round(lucid_data["total_three"]/10) * symbol    
    t4 = round(lucid_data["total_four"]/10) * symbol
    t5 = round(lucid_data["total_five"]/10) * symbol   
    ln = round(lucid_data["lucid_nights"]/10) * symbol 
    
    tnl = round(int(total_dreams())/10) * symbol
    
    bar_chart_dict = {"t_l":t_l, "t1":t1, "t2":t2, "t3":t3,"t4":t4,"t5":t5,"tnl":tnl, "ln":ln}
    
    return(bar_chart_dict)
    
#making the actual bars for the bar chart :)
def bar_chart_maker(dictionary, count_list):
    #the symbol 
    symbol = "\u2610"

    new_dict = {}
    for i in count_list:
        new_dict[i] = round(dictionary[i]/10)*symbol
    return new_dict
    
#finding the entry with the longest word count
def word_count_max():
    db = open_database()
    word_counts = db.execute("select word_count, uid from entries").fetchall()

    wc_max = 0
    total_wc = 0
    wc_bar_dict = {}
    
    word_count_limits = [100*i for i in range(1,25)]
    #filling in dictionary
    for i in word_count_limits:
        wc_bar_dict[i] = 0
        
    
    for row in word_counts:
        entry = int(row["word_count"])
        if wc_max < entry:
            wc_max = entry
            uid = int(row["uid"])
            wc_return = {"wc":entry, "uid":uid}
            #print(entry)
            #print("MAX = ", wc_max)
        if entry > 0:
            total_wc = total_wc + entry
            #print("TOTAL = ", total_wc)
            
        already_in_dict = False
        for i in word_count_limits:
            if entry < i and already_in_dict == False:
                wc_bar_dict[i] = wc_bar_dict[i] + 1
                already_in_dict = True        
    
    symbol_bar_dict = bar_chart_maker(wc_bar_dict, word_count_limits)
    return_dict = {"wc_return":wc_return,"symbol_bar_dict":symbol_bar_dict,"wc_bar_dict":wc_bar_dict, "total_wc":total_wc, "word_count_limits":word_count_limits,}

    return(return_dict)
    
######################################
#    More Stats Page (Graphs!!!)     #
######################################

@bp.route('/more',methods=("GET",))
def more_stats_viewer():
    cur_stats = more_stats_getter()
    return render_template('dream/more_stats.html', stats=cur_stats)
    
    
# Getting the data needed for the more stats page
def more_stats_getter():
    db = open_database()
    data = db.execute('''SELECT creation_time, uid, entry_type, word_count FROM entries''').fetchall()
    data_dict = [dict(row) for row in data]
    return json.dumps(data_dict)