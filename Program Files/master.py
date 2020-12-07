import findspark
findspark.init()
import json
import datetime
from pyspark import SparkConf, SparkContext 
from pyspark.streaming import StreamingContext
from pyspark.sql import SQLContext
from pyspark.mllib.linalg import Vectors
from pyspark.mllib.regression import LabeledPoint
from pyspark.mllib.regression import StreamingLinearRegressionWithSGD



####################################################################################################################
########################################### Spark Initialisation ###################################################
###################################################################################################################

conf = SparkConf()
conf.setAppName("FPL")
sc = SparkContext(conf=conf)
sqlContext = SQLContext(sc)
ssc = StreamingContext(sc, 100)
ssc.checkpoint("checkpoint_FPL")



####################################################################################################################
########################################### Quadratic Regression ###################################################
####################################################################################################################

numFeatures = 2
model = StreamingLinearRegressionWithSGD()
model.setInitialWeights([0.0, 0.0])



####################################################################################################################
###################################### Reading players.csv, teams.csv ##############################################
####################################################################################################################

# Reading players and teams csv files
players = sqlContext.read.load("file:///C:\\Users\\navan\\Desktop\\Source_Code\\players.csv", format="csv", header="true", inferSchema="true")
playerBirthDate = players.select("Id","birthDate").rdd.collectAsMap()
playerBirthDate = sc.broadcast(playerBirthDate)
# teams = sqlContext.read.load("file:///home/navaneeth/Desktop/Project/Source_Code/teams.csv", format="csv", header="true", inferSchema="true")



####################################################################################################################
############################################ Required functions ####################################################
####################################################################################################################

def isMatch(record):
	'''
	checks if its a match record
	'''
	recordJson = json.loads(record)
	try:
		mId = recordJson["wyId"]
		return True
	except:
		return False

def saveMatch(record):
	recordJson = json.loads(record)
	return recordJson["wyId"], recordJson

def addMatch(new, old):
	if old is None:
		return new
	return old

def getPlayerListFromMatch(m):
	m = json.loads(m)
	players_subst_stats = []
	date = m["date"]

	for t in m["teamsData"]:
		team_data = m["teamsData"][t]
		sub_data = m["teamsData"][t]["formation"]["substitutions"]

		inPlayers = [s["playerIn"] for s in sub_data]
		outPlayers = [s["playerOut"] for s in sub_data]
		subTime = [s["minute"] for s in sub_data]

		bench_players = [p["playerId"] for p in team_data["formation"]["bench"]]
		starting_xi = [p["playerId"] for p in team_data["formation"]["lineup"]]
		for pId in starting_xi:
			try:
				idx = outPlayers.index(pId)
				players_subst_stats.append((pId, (pId, date, 0, subTime[idx],t)))
			except ValueError:
				players_subst_stats.append((pId, (pId, date, 0, 90,t)))
		for pId in bench_players:
			try:
				idx = inPlayers.index(pId)
				players_subst_stats.append((pId, (pId, date, subTime[idx], 90, t)))
			except ValueError:
				players_subst_stats.append((pId, (-1, -1, -1, -1, -1)))
	return players_subst_stats

def isEvent(record):
	'''
	checks if its an event record
	'''
	recordJson = json.loads(record)
	try:
		eId = recordJson["eventId"]
		return True
	except:
		return False

def metricsValsCalc(record):
	'''
	metric values
	'''

	recordJson = json.loads(record)

	'''
	TUPLE INFORMATION:
	(acc normal pass) anp,
	(accurate key pass) akp, 
	(normal pass) np, 
	(key pass) kp
	(duel won) dw, 
	(neutral duel) nd,
	(total duel) td,
	shots,
	shots on target and goals,
	shots on target and not goals,
	shots on target,
	fouls,
	own goals,
	free kicks,
	effective free kicks,
	penalties scored,
	goals,
	match_id
	'''

	eventid = recordJson["eventId"]
	matchId = recordJson["matchId"]
	pid = recordJson["playerId"]
	tags = [d["id"] for d in recordJson["tags"]]
	own_goal = 0
	goals = 0

	#Check for goal
	if 101 in tags:
		goals = 1

	#Check for own goal
	if 102 in tags:
		own_goal=1

	# pass event
	if eventid == 8:
		anp = 0; akp = 0; np = 0; kp = 0;

		if 302 in tags:
			kp = 1
		else:
			np = 1
		if 1801 in tags and 302 in tags:
			akp = 1
		elif 1801 in tags:
			anp = 1
		return (pid, (anp, akp, np, kp, 0, 0, 0,0,0,0, 0, 0, own_goal,0, 0, 0, goals, matchId))

	# duel event
	elif eventid == 1:
		dw = 0; nd = 0; td = 1;
		if 703 in tags:
			dw = 1
		if 702 in tags:
			nd = 1
		return (pid, (0, 0, 0, 0, dw, nd, td,0,0,0, 0, 0, own_goal,0, 0, 0, goals, matchId))

	#shot event
	elif eventid==10:
		shots=1;on_target_goal=0;on_target_notgoal=0;on_target=0;
		if 1801 in tags:
			on_target += 1;
		if 1801 in tags and 101 in tags:
			on_target_goal += 1
		if 1801 in tags and 101 not in tags:
			on_target_notgoal += 1
		return (pid, (0, 0, 0, 0, 0, 0, 0, shots, on_target_goal, on_target_notgoal,on_target, 0, own_goal,0, 0, 0, goals, matchId))

	#free kick
	elif eventid==3:
		fk = 1; eff = 0; penal_goals = 0;
		if 1801 in tags:
			eff += 1
		if recordJson["subEventId"]==35 and 101 in tags:
			penal_goals += 1;
		return (pid, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, own_goal,fk,eff,penal_goals, goals, matchId))

	#Foul loss
	elif eventid==2:
		return (pid, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, own_goal,0, 0, 0, goals, matchId))

	return (pid, (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, own_goal,0, 0, 0, goals, matchId))

def metricsCounterCalc(new, old):
	'''
	updates new state of metric counts
	'''
	a, b, c, d, e, f, g,h,i,j,k,l,m,n,o,p,q = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
	m_id = -1
	for metrics in new:
		a += metrics[0]
		b += metrics[1]
		c += metrics[2]
		d += metrics[3]
		e += metrics[4]
		f += metrics[5]
		g += metrics[6]
		h += metrics[7]
		i += metrics[8]
		j += metrics[9]
		k += metrics[10]
		l += metrics[11]
		m += metrics[12]
		n += metrics[13]
		o += metrics[14]
		p += metrics[15]
		q += metrics[16]
		m_id = metrics[17]
	if old is None:
		return (a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, m_id)
	if old[-1] != m_id:
		return (a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, m_id)
	return (a + old[0], b + old[1], c + old[2], d + old[3], e + old[4], f + old[5], g + old[6], h + old[7], i + old[8], j + old[9], k + old[10], l + old[11], m + old[12], n + old[13], o + old[14], p + old[15], q + old[16], old[-1])

def finalMetricsCalc(new, old):
	'''
	calculates final metrics
	'''
	new = new[0]
	try:
		pa = (new[0] + new[1] * 2) / (new[2] + new[3] * 2)
	except:
		pa = 0
	try:
		de = (new[4] + new[5] * 0.5) / (new[6])
	except:
		de = 0
	try:
		se = (new[8] + (new[9]*0.5))/new[7]
	except:
		se = 0

	try:
		target = new[10]
	except:
		target = 0

	try:
		fl,og,g=new[11],new[12],new[16]
	except:
		fl,og,g = 0,0,0

	try:
		fk_eff = (new[14]+new[15])/new[13]
	except:
		fk_eff = 0

	anp = new[0]; akp = new[1]; np = new[2]; kp = new[3];
	return (pa, de, se, fl, og, target, fk_eff, g, anp, akp, np, kp)

def playerRatingUpdate(new, old):
	'''
	updates player rating after every match
	'''
	'''
	(pr, change in pr, no_of_matches)
	'''
	try:
		monthToNumber = {"January":1,"February":2,"March":3,"April":4,"May":5,"June":6,"July":7,"August":8,"September":9,"October":10,"November":11,"December":12}
		new1 = new[0][0]
		time_on_pitch = new[0][1][3] - new[0][1][2]
		pa = new1[0]
		de = new1[1]
		se = new1[2]
		fl = new1[3]
		og = new1[4]
		target = new1[5]
		fk_eff = new1[6]
		no_of_matches = 1
		
		birthDate = (playerBirthDate.value[new[0][1][0]]).split("-")
		birthYear = int(birthDate[0])
		birthMonth = int(birthDate[1])
		birthDay = int(birthDate[2])
		birthTime = datetime.datetime(birthYear, birthMonth, birthDay)
		matchDate = new[0][1][1].split(" ")
		matchYear = int(matchDate[2])
		matchMonth = monthToNumber[matchDate[0]]
		matchDay = int(matchDate[1].strip(','))
		matchTime = datetime.datetime(matchYear, matchMonth, matchDay)
		age = (matchTime - birthTime).days
		age = round(age/365)

		if old is None:
			old = (0.5, 0.0, 1, 0)
		else:
			no_of_matches += old[2]
		playerContrib = (pa + de + fk_eff + target) / 4
		#Penalise
		playerContrib = playerContrib - ((0.005*fl + 0.05*og)*playerContrib)
		finalContrib = (playerContrib + old[0]) / 2
		if time_on_pitch == 90:
			new_rating = 1.05*finalContrib
		else:
			new_rating = (time_on_pitch/90)*finalContrib

		return (new_rating, new_rating-old[0], no_of_matches, age)
	except:
		return old

def trainingDataCalc(x):
	playerRating = x[1][0][0]
	age = x[1][0][3]
	label = playerRating
	vec = Vectors.dense([age, age**2])
	return LabeledPoint(label, vec)

def testingDataCalc(x):
	age = x[1][0][3]
	vec = Vectors.dense([age, age**2])
	return (age, vec)

def savePredictedPlayerRating(new, old):
	try:
		return new[0]
	except:
		return old

def filterUnwanted(x):
	return (x[0], (x[1][0][1], x[1][1][1][-1]))

def joiner(rdd_a, rdd_b):
	rdd_c = rdd_a.cartesian(rdd_b)
	return rdd_c

def joiner1(record):
	p1_record = record[0]
	p2_record = record[1]
	key1 = (p1_record[0], p2_record[0])
	key2 = (p2_record[0], p1_record[0])
	value = (p1_record[1], p2_record[1])
	return [(key1, value), (key2, value)]

def chemCoeffUpdate(new,old):
	try:
		new = new[0]
		if old is None:
			old = 0.5
		same_team = new[0][-1]==new[1][-1]
		if(same_team):
			if (new[0][0]>0 and new[1][0]<0) or (new[0][0]<0 and new[1][0]>0):
				delta = (new[0][0] + new[1][0])/2
				if delta<0:
					delta = -delta
				return (old-delta)
			else:
				delta = (new[0][0] + new[1][0])/2
				return (old+delta)
		else:
			if (new[0][0]>0 and new[1][0]<0) or (new[0][0]<0 and new[1][0]>0):
				delta = (new[0][0] + new[1][0])/2
				if delta<0:
					delta = -delta
				return (old+delta)
			else:
				delta = (new[0][0] + new[1][0])/2
				return (old-delta)
	except:
		return old

def playerProfileUpdate(new, old):
	'''
	new[0]: (pa, de, se, fl, og, target, fk_eff, g, anp, akp, np, kp)
	'''
	try:
		if old is None:
			fouls = new[0][3]
			goals = new[0][7]
			own_goals = new[0][4]
			shots_on_target = new[0][5]
			anp = new[0][8]
			akp = new[0][9]
			np = new[0][10]
			kp = new[0][11]
		else:
			fouls = new[0][3] + old[0]
			goals = new[0][7] + old[1]
			own_goals = new[0][4] + old[2]
			shots_on_target = new[0][5] + old[3]
			anp = new[0][8] + old[4]
			akp = new[0][9] + old[5]
			np = new[0][10] + old[6]
			kp = new[0][11] + old[7]
		return (fouls,goals,own_goals,shots_on_target,anp,akp,np,kp)
	except IndexError:
		return old



####################################################################################################################
############################################## Driver Function #####################################################
####################################################################################################################

dataStream = ssc.socketTextStream("localhost", 6100).repartition(10)


### Match information
match = dataStream.filter(isMatch)
match.pprint()

### All matches
matches = match.map(saveMatch).updateStateByKey(addMatch)

# ### Player Substitutions
playerSubs = match.flatMap(getPlayerListFromMatch)
playerSubs.pprint()

# ### Events
events = dataStream.filter(isEvent)
events.pprint()

# ### Metrics
metricsVals = events.map(metricsValsCalc)
metricsVals.pprint()

# ### Metrics Counts
metricsCounter = metricsVals.updateStateByKey(metricsCounterCalc)
metricsCounter.pprint()

# ### Final Metrics
finalMetrics = metricsCounter.updateStateByKey(finalMetricsCalc)
finalMetrics.pprint()

# ### Final Metrics + player time on pitch data
playerData = finalMetrics.join(playerSubs)
playerData.pprint()

# ### Player Rating
playerRating = playerData.updateStateByKey(playerRatingUpdate)
playerRating.pprint()

# ### Current Match Details
currentMatch = playerRating.join(playerData)
currentMatch.pprint()

# ### Training Data
trainingData = currentMatch.map(trainingDataCalc)
trainingData.pprint()
model.trainOn(trainingData)

# ### Testing Data
testingData = currentMatch.map(testingDataCalc)
testingData.pprint()

# ### Predicted Player Rating
predictedPlayerRating = model.predictOnValues(testingData).updateStateByKey(savePredictedPlayerRating)
predictedPlayerRating.pprint(100)

### Change in PR, Team_id
playerRating1 = currentMatch.map(filterUnwanted).repartition(1)
playerRating1.pprint()

### Cartesian Product
joined = playerRating1.transformWith(joiner, playerRating1)
joined = joined.flatMap(joiner1)
joined.pprint()

### Chemistry Coefficients
chemCoeff = joined.updateStateByKey(chemCoeffUpdate)
chemCoeff.pprint(422500)

### Player profile
playerProfile = finalMetrics.updateStateByKey(playerProfileUpdate)
playerProfile.pprint()

### Final Profile
finalProfile = playerRating.join(playerProfile)
finalProfile.pprint(650)

####################################################################################################################
############################################## Begin Streaming #####################################################
####################################################################################################################

ssc.start()
ssc.awaitTermination()
ssc.stop()