import tweepy
import json
import sys
import getopt
from langdetect import detect
import pymongo
import mysql.connector

#login
def login():
    fileKeys = open('credentialsTwitter.json').read()
    keys = json.loads(fileKeys)
    auth = tweepy.OAuthHandler(keys['consumer_key'], keys['consumer_secret'])
    auth.set_access_token(keys['access_token'], keys['access_token_secret'])
    twitter = tweepy.API(auth, wait_on_rate_limit=True)
    return twitter


def loginMySql():
    fileKeys = open('adressMySQL.json').read()
    keys = json.loads(fileKeys)
    try:
        client = mysql.connector.connect(user=keys["user"], password=keys["password"], host=keys["host"], database = keys["database"])
        cursor = client.cursor()
    except mysql.connector.errors.ProgrammingError:
        print("crea il db")
    return client, cursor

def loginMongo():
    fileKeys = open('adressMongo.json').read()
    keys = json.loads(fileKeys)
    client = pymongo.MongoClient(keys['adress_local'],int(keys['port_local']))
    return client[keys['name_db']]
#prendere tweet accounts

def getTweets(twitter, account, N, start_date, end_date, id_experiment):
    max_number = 3200
    max_per_request = 200
    languages = ("de", "en", "es", "fr", "it", "pt")
    user_tweets = []
    if (N>max_number):
        N = max_number
        iteration = 16
        last = 0
    else:
        iteration, last = divmod(N, max_per_request)
    user_timeline = twitter.user_timeline(screen_name =account, count=1)
    if (user_timeline):
        for i in range(iteration+1):
            lastTweetId = int(user_timeline[0].id_str)
            user_timeline = twitter.user_timeline(screen_name = account, max_id = lastTweetId, count = max_per_request)
            for tweets in user_timeline:
                if (tweets.lang == None):
                    tweets.lang = detect(tweets.text.replace("\n", " "))
                if (tweets.lang in languages):
                    d = {'id_user': tweets.user.id_str, 'text': tweets.text, 'lang':tweets.lang, 'favourite_count': tweets.favorite_count, 'retweet_count': tweets.retweet_count, 'create_at': tweets.created_at, 'mentions': tweets.entities['user_mentions'], '_id':tweets.id_str, 'id_experiment': [id_experiment], 'coordinates':tweets.coordinates}
                    user_tweets.append(d)
            if i != iteration:
                user_tweets = user_tweets[:len(user_tweets)-1]
            if len(user_timeline)<max_per_request:
                break
    else:
        print('no tweets')
    return user_tweets[:N]


#salvarli nel db
def storeTweets(tweets, db):
    collection = 'tweets'
    experiment = tweets['id_experiment'][0]
    t = db[collection].find_one({'_id':tweets['_id']})
    if t == None:
        db[collection].insert(tweets)
    else:
        if str(experiment) not in t['id_experiment']:
#            print(experiment, t['id_experiment'])
            t['id_experiment']+= experiment
        db[collection].update_one({'_id':t['_id']}, {"$set": t}, upsert= False)
#        print('tweet already exists')
#log

def storeUser(account, user_id, id_experiment, db,name_table):
    collection = 'users'
    db[collection].insert({'id_user':user_id, 'screen_name':account, 'id_experiment':id_experiment, 'type':name_table})

def storeEmergents(emergent, id_experiment, cursor):
    command = ("INSERT INTO emergents (screen_name, id_experiment) VALUES ('"+emergent+"', '"+id_experiment+"')")
    cursor.execute(command)

def getAccounts(cursor, id_experiment, name_table):
    command = ("SELECT screen_name FROM "+name_table+" WHERE id_experiment = "+id_experiment)
    cursor.execute(command)
    accounts = []
    for name in cursor:
        accounts.append(name[0])
    return accounts

def getDescription(twitter, account, N, start_date, end_date, id_experiment, count):
    isEmergent = False
    description = twitter.get_user(account).description.lower()
    if 'writ' in description:
        isEmergent = True
#        print(account, description)
        count+=1
    return count, isEmergent

def main():
#    do the login
    try:
        twitter = login()
    except:
        print('error login Twitter')
#    do the mongo login
    try:
        db = loginMongo()
    except:
        print('error login Mongo')
#        scrivi errore nel log
    try:
        dbSQL, cursor = loginMySql()
    except:
        print('error login MySQL')
#    open accounts file
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'n:s:e:x:')
    except getopt.GetoptError as err:
    # print help information and exit:
        print('err')  # will print something like "option -a not recognized"
#        usage()
        sys.exit(2)
    N = None
    start_date = None
    end_date = None
    id_experiment = None
    name_table = args[0]
    
    for o, a in opts:
        if o == "-n":
            N = a
        elif o == "-s":
            start_date = a
        elif o == "-e":
            end_date = a
        elif o == "-x":
            id_experiment = a
    accounts = getAccounts(cursor, id_experiment, name_table)
    count = 0
    for i in range(len(accounts)):
#        get the tweets for seed i
        try:
            account = accounts[i]
#            print('crawling account '+ account)
            count, isEmergent = getDescription(twitter, account, int(N), start_date, end_date, id_experiment, count)
            if isEmergent:
                print(account)
            if not isEmergent or True:
                tweets = getTweets(twitter, account, int(N), start_date, end_date, id_experiment)
                user_id = tweets[0]['id_user']
                storeUser(account, user_id, id_experiment, db, name_table)
#            else:
#                storeEmergents(account, id_experiment)

        except:
            print(account+' error')
#        scrivi errore nel log
#       store tweets in db for seed i
        try:
            if not isEmergent or True:
                for tweet in tweets:
                    storeTweets(tweet, db)
        except:
            print('errorSalva')
#        scrivi errore nel log

    print(count)

if __name__ == "__main__":
    main()




