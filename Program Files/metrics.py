#Import libraries
from numpy import array
from pyspark.mllib.clustering import KMeans, KMeansModel
from pyspark import SparkContext
from pyspark.mllib.regression import LinearRegressionWithSGD
from pyspark.mllib.regression import LabeledPoint

#Return avg of list
def avg(l):
    return sum(l)/len(l)

#Create spark context
sc = SparkContext(appName="KMeans")
#Read player profile file
data = sc.textFile("player_profile.txt")





#Convert each file line into an array of items
parsedData = data.map(lambda line: array([x for x in line.split(',')]))
parameters_kmeans = parsedData.map(lambda x : array([float(x[1]),float(x[2]),float(x[3]),float(x[4]),float(x[5]),str(x[6]),float(x[7]),float(x[8]),float(x[9]),float(x[10]),float(x[11]),float(x[12])]))
pd = parsedData.collect()

#################################################KMeans###############################################################

#Train the model with the profile data
clusters = KMeans.train(parameters_kmeans, 5, maxIterations=10, initializationMode="random")


#Cluster -> List of players grouped in that cluster
player_cluster_ratings = {}
#player id -> predicted cluster number
cluster_predictions = {}

#Convert each np array to list
for i in range(len(pd)):
    pd[i] = list(pd[i])

#Predict cluster for each player and construct cluster_average_ratings
for x in range(len(pd)):
    cluster_no = clusters.predict([float(pd[x][1]),float(pd[x][2]),float(pd[x][3]),float(pd[x][4]),float(pd[x][5]),float(pd[x][6]),float(pd[x][7]),float(pd[x][8]),float(pd[x][9]),float(pd[x][10]),float(pd[x][11]),float(pd[x][12])])
    if cluster_no not in player_cluster_ratings:
        player_cluster_ratings[cluster_no] = []
    player_cluster_ratings[cluster_no].append(float(pd[x][1]))
    cluster_predictions[pd[x][0]] = cluster_no
cluster_average_ratings = {i:avg(player_cluster_ratings[i]) for i in player_cluster_ratings.keys()}

#Update player rating for players that have played <5 matches
for x in range(len(pd)):
    if int(pd[x][3])<5:
        pd[x][1] = cluster_average_ratings[cluster_predictions[pd[x][0]]]


#Save new profiles
f=open('updated_profile.txt','w')
for i in range(len(pd)):
    pd[i] =  '\t'.join(list(map(str,pd[i])))
for ele in pd:
    f.write(ele + '\n')
f.close()
####################################################Regression##################################################################
#Collect params
pd1 = parsedData.collect()

datalist = []

for i in range(len(pd1)):
    age = float(pd1[i][3])
    params = [age,age**2]
    print(params)
    datalist.append(LabeledPoint(float(pd[i][1]),params))

#Train reg model
model = LinearRegressionWithSGD.train(sc.parallelize(datalist), iterations=2000,initialWeights=array([0.001,0.001]),step=0.0000000000000001)

#Save predictions for ages 11 - 60

file = open("rating_predictions",'w')
for i in range(11,61):
    rating = model.predict([i,i**2])
    file.write(str(i) + "," + str(rating) + "\n")

file.close()


sc.stop()