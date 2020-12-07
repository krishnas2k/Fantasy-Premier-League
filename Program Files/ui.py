#Import req modules
import json
import csv
from ast import literal_eval as make_tuple
import datetime 
import os
#Return id given the player name
def getId(name):
    for name1 in player_name_rev:
        if name1 in name:
            return player_name_rev[name1]
    return None

#Return age of player as of date1
def getAge(id,date1):
    bd = player_bd[id]
    date1 = list(map(int,date1.split('-')))
    bd = list(map(int,bd.split('-')))
    age = (datetime.date(int(date1[0]),int(date1[1]),int(date1[2])) - datetime.date(int(bd[0]),int(bd[1]),int(bd[2]))).days//365
    return age

#Return predicted rating given age of player
def regression(age):
    try:
        # return None
        return age_to_rating[age]
    except:
        return 0.5

#Add goal goalList with player name,team name and no. of goals a details
def addGoal(goalList,p_name,t_name,num):
    for player_dict in goalList:
        if p_name in player_dict:
            player_dict[number_of_goals] += num
            return
    new_dict = {}
    new_dict['name'] = p_name
    new_dict['team_name'] = t_name
    new_dict['number_of_goals'] = num

    goalList.append(new_dict)
    return

#Return match details dictionary given label and date of match
def get_match_details(label,date):
    c_match = None
    res = {}
    team_name = {}
    team1,team2 = label.split(',')[0].split('-')[0],label.split(',')[0].split('-')[1]
    found = 0
    i = 0
    label = label.replace("Bournmouth","Bournemouth")
    for match in matches:
        i += 1
        if match=='':
            continue
        dict = make_tuple(match)[1][0]
        if label in dict["label"] and date in dict["dateutc"]:
            found = 1
            c_match = dict
            break
    if not found:
        return None
    # print(c_match)
    team_name[list(c_match['teamsData'].keys())[0]] = team1
    team_name[list(c_match['teamsData'].keys())[1]] = team2
    # print(team_name)
    res['date'] = date
    res['duration'] = c_match['duration']
    res['winner'] = team_name[str(c_match['winner'])]
    res['gameweek'] = c_match['gameweek']
    res['venue'] = c_match['venue']
    res['red_cards'] = []
    res['yellow_cards'] = []
    res['goals'] = []
    res['own_goals'] = []

    for team in c_match['teamsData']:
        bench = c_match['teamsData'][team]['formation']['bench']
        lineup = c_match['teamsData'][team]['formation']['lineup']
        for entry in bench:
            try:
                if int(entry['goals'])>0:
                    addGoal(res['goals'],player_name[entry['playerId']],team_name[team],entry['goals'])
            except:
                pass
            try:
                if int(entry['ownGoals'])>0:
                    addGoal(res['own_goals'],player_name[entry['playerId']],team_name[team],entry['ownGoals'])
            except:
                pass
            try:
                if int(entry['redCards'])>0:
                    res['red_cards'].append(player_name[entry['playerId']])
            except:
                pass
            try:
                if int(entry['yellowCards'])>0:
                    res['yellow_cards'].append(player_name[entry['playerId']])
            except:
                pass
        for entry in lineup:
            try:
                if int(entry['goals'])>0:
                    addGoal(res['goals'],player_name[entry['playerId']],team_name[team],entry['goals'])
            except:
                pass
            try:
                if int(entry['ownGoals'])>0:
                    addGoal(res['own_goals'],player_name[entry['playerId']],team_name[team],entry['ownGoals'])
            except:
                pass
            try:
                if int(entry['redCards'])>0:
                    res['red_cards'].append(player_name[entry['playerId']])
            except:
                pass
            try:
                if int(entry['yellowCards'])>0:
                    res['yellow_cards'].append(player_name[entry['playerId']])
            except:
                pass
        
    return res

#Return key given value of player_name dict
def GetKey(val):
   for key, value in player_name.items():
      if val == value:
         return key

#Return player profile details for option opt=0. If opt=0, return only player rating
def profile_details(p_name,csvreaderList,opt=0):
    # “name”: “”,
    # “birthArea”: “”,
    # “birthDate”: “”,
    # “foot”: “”,
    # “role”: “”,
    # “height”: (integer),
    # “passportArea”: “”,
    # “weight”: (integer),
    # “fouls”: (integer),
    # “goals”: (integer),
    # “own_goals”: (integer),
    # “percent_pass_accuracy”: (2-digit integer),
    # “percent_shots_on_target”: (2-digit integer)
    # ['name', 'birthArea', 'birthDate', 'foot', 'role', 'height', 'passportArea', 'weight', 'Id']
    #pid,playerrating(pr, change in pr, no_of_matches), playerprofile(pa, de, se, fl, og, target, fk_eff, g, anp, akp, np, kp)
    d_final = dict()
    d_final["name"] = p_name
    index = names.index(p_name) +1
    d_final["birthArea"] = csvreaderList[index][1]
    d_final["birthDate"] = csvreaderList[index][2]
    d_final["foot"] = csvreaderList[index][3]
    d_final["role"] = csvreaderList[index][4]
    d_final["height"] = csvreaderList[index][5]
    d_final["passportArea"] = csvreaderList[index][6]
    d_final["weight"] = csvreaderList[index][7]
    p_id = GetKey(p_name)
    #print(type(p_id))
    
    csvList = [line.split('\t') for line in open(filename3).read().split('\n') if line!='']
    # print(csvList)
    flag = 0
    for row in csvList[1:]:
        if p_id == int(row[0]):
            if opt==1:
                return float(row[1])

            flag = 1
            d_final["fouls"] = int(row[5])
            d_final["goals"] = int(row[6])
            d_final["ownGoals"] = int(row[7])
            d_final["percent_pass_accuracy"] = int(((int(row[9]) + int(row[10])*2)/(int(row[11]) + int(row[12])*2)) * 100)
            d_final["percent_shots_on_target"] = int(row[8])

            break
    if flag == 0:
        d_final["fouls"] = 0
        d_final["goals"] = 0
        d_final["ownGoals"] = 0
        d_final["percent_pass_accuracy"] = 0
        d_final["percent_shots_on_target"] = 0

    if opt==1:
        return 0.5

    return d_final

#Return winning chance given team details - player list and ratings of the players
def predict_winning_chance(players_1, players_2, rate_1, rate_2):
    
    chem_list = []
    for p1 in players_1:
        for p2 in players_2:
            if (int(p1),int(p2)) in chem_coeff_dict:
                chem_list.append(chem_coeff_dict[(int(p1),int(p2))])
            else:
                chem_list.append(0.5)
    chem = sum(chem_list)/len(chem_list)

    sum_1 = 0
    sum_2 = 0
    for i in rate_1:
        sum_1 += i*chem
    for i in rate_2:
        sum_2 += i*chem
    strA = sum_1/len(rate_1)
    strB = sum_2/len(rate_2)
    wiA = (0.5 + strA + (strA + strB)/2)*100
    wiB = 100 - wiA
    return wiA,wiB


#Read various files
#Player details file
filename1 = "players.csv"
#Match details - From streamed data
filename2 = "matches.txt"
matches = open(filename2).read().split("\n")
#Profile data file - after clustering
filename3 = "updated_profile.txt"
#Eating predictions file
filename4 = "rating_predictions.txt"
#Chemistry coefficients file
filename5 = "chem_coefficients.txt"
#Player names
names = []
#Player ids
pids = []
#List of rows from players.csv
csvreaderList = None
#id -> name
player_name = {}
#name -> id mapping
player_name_rev = {}
#id -> birthdate mapping
player_bd = {}


#Convert files to list of tuples one per line
prediction_list = [line.split(',') for line in open(filename4).read().split('\n')]
coeff_list = [make_tuple(line) for line in open(filename5).read().split('\n') if line.strip()!='']

#Create age to predicted rating mapping
age_to_rating = {}
for entry in prediction_list[:-1]:
    if int(entry[0]) not in age_to_rating:
        age_to_rating[int(entry[0])] = float(entry[1])


#Create player pair to chem coeff mappping
chem_coeff_dict = {}
for entry in coeff_list:
    if entry[0] not in chem_coeff_dict:
        chem_coeff_dict[entry[0]] = float(entry[1])



#Read players.csv and store rows
with open(filename1, 'r') as csvfile:
    csvreader = csv.reader(csvfile)
    csvreaderList = list(csvreader)

#Construct a few dictionaries and lists
for row in csvreaderList[1:]:
    player_name[int(row[-1])] = row[0]
    player_name_rev[row[0]] = row[-1]
    player_bd[row[-1]] = row[2]
    names.append(row[0])
    pids.append(row[8])


#Start taking inputs
while(True):

    os.system('cls')
    print("\t\t\t\tFantasy Premier League\t\t\t\t")
    path = input("Enter the path to the input JSON file: ")
    f = open(path)
    data = json.load(f)

    #Find req_type
    try:
        req_type = data["req_type"]
    except:
        req_type = 3

    flag = 0
    while flag == 0:
        if(req_type == 1):
            #Handle winning chance request
            date = data["date"]
            team1 = data["team1"]
            team2 = data["team2"]
            #print(type(team1),type(team2))
            team1_fields = []
            team2_fields = []
            for i in team1:
                team1_fields.append(team1[i])
            for i in team2:
                team2_fields.append(team2[i])

            #Check role requirement
            gk = 0  # 1
            df = 0  # >3
            md = 0  # >2
            fw = 0  # >1


            # Schema : ['name', 'birthArea', 'birthDate', 'foot', 'role', 'height', 'passportArea', 'weight', 'Id']
            for i in range(1, len(team1_fields)):
                pl_name = team1_fields[i]
                if pl_name in names:
                    for row in csvreaderList:
                        if pl_name == row[0]:
                            role = row[4]
                            break

                    #print(pl_name,row)
                    if role == "GK":
                        gk += 1
                    elif role == "DF":
                        df += 1
                    elif role == "MD":
                        md += 1
                    elif role == "FW":
                        fw += 1

            #Prompt user if team invalid
            if not (gk==1 and fw>=1 and md>=2 and df>=2):
                print("Team 1 invalid. Please try again \n")
                break

            else:
                #Similarly for team 2
                gk = 0  # 1
                df = 0  # >3
                md = 0  # >2
                fw = 0  # >1
                # ['name', 'birthArea', 'birthDate', 'foot', 'role', 'height', 'passportArea', 'weight', 'Id']
                for i in range(1, len(team2_fields)):
                    pl_name = team2_fields[i]
                    for row in csvreaderList:
                        if pl_name == row[0]:
                            role = row[4]
                            break    
                    #print(pl_name,row)
                    if role == "GK":
                        gk += 1
                    elif role == "DF":
                        df += 1
                    elif role == "MD":
                        md += 1
                    elif role == "FW":
                        fw += 1
                #print(gk,df,md,fw)
                if not (gk==1 and fw>=1 and md>=2 and df>=2):
                    print("Team 2 invalid. Please try again \n")
                    break
                else:
                    #Check if player rating is too low <0.2 => retired
                    retired_1 = []
                    rate_1 = []
                    players_1 = []
                    for i in range(1, len(team1_fields)):
                        pl_name = team1_fields[i]
                        pl_id = getId(pl_name)
                        players_1.append(pl_id)
                        age = getAge(pl_id,date)
                        rating = profile_details(pl_name,csvreaderList,opt=1)
                        if rating is None:
                            rating = regression(age)
                        rate_1.append(rating)
                        if rating < 0.0:
                            retired_1.append(pl_name)
                    retired_2 = []
                    rate_2 = []
                    players_2 = []


                    for i in range(1, len(team2_fields)):
                        pl_name = team2_fields[i]
                        pl_id = getId(pl_name)
                        players_2.append(pl_id)
                        age = getAge(pl_id,date)
                        rating = profile_details(pl_name,csvreaderList,opt=1)
                        if rating is None:
                            rating = regression(age)
                        rate_2.append(rating)
                        if rating < 0.0:
                            retired_2.append(pl_name)

                    if len(retired_1) is not 0:
                        print("The following players from team1 are retired\n")
                        for i in retired_1:
                            print(i)
                    if len(retired_2) is not 0:
                        print("The following players from team2 are retired\n")
                        for i in retired_2:
                            print(i)
                    if len(retired_1) is not 0 or len(retired_2) is not 0:
                        print("Teams have retired players. Please try again \n")
                        break
                    else:
                        flag = 1
                        wi_A, wi_B = predict_winning_chance(players_1, players_2, rate_1, rate_2)
                            
                        d_A = {}
                        d_A["name"] = team1["name"]
                        d_A["winning chance"] = wi_A
                        d_B = {}
                        d_B["name"] = team2["name"]
                        d_B["winning chance"] = wi_B
                        d_final = {}
                        d_final["team1"] = d_A;
                        d_final["team2"] = d_B;
                        with open("output.json", "w") as output: 
                            json.dump(d_final, output)
                            print("Output written to output.json successfully")

        #Handle player profile request
        elif req_type == 2:
            if data["name"] not in names:
                print("The player is not registered\n")
                break
            else:
                flag = 1
                # profile function returns the profile with the required attributes in the form of dictionary
                d_final = profile_details(data["name"],csvreaderList)
                with open("output.json", "w") as output: 
                    #print(d_final)
                    json.dump(d_final, output)
                    print("Output written to output.json successfully")
                
        else:
            #Handle match details request
            flag = 1
            date = data["date"]             
            label = data["label"]

            # get_match_details returns the match details as a dictionary
            d_final = get_match_details(label,date)
            if d_final is None:
                print('Sorry, match could not be found')
            else:
                with open("output.json", "w") as output: 
                    #print(d_final)
                    json.dump(d_final, output)
                    print("Match found.Output written to output.json successfully")

    ex = int(input('Enter 1 to continue, any other key to exit:'))
    if ex==1:
        continue
    else:
        break




 

