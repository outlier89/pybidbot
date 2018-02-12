import steem
import time
import datetime
import signal
import copy
import requests
from steem import Steem
from datetime import timedelta

nodes = ['https://api.steemit.com',
         'https://rpc.buildteam.io',
         'https://steemd.minnowsupportproject.org',
         'https://steemd.privex.io',
         'https://gtg.steem.house:8090']

acc_name = 'therising'                                #Replace therising with your steem account name.
s = Steem(nodes, keys=['Your_Private_Posting_Key', 'Your_Private_Active_Key'])

ac=steem.account.Account(acc_name,s)
trxlist=['302e45385c83d720850e7c6590a3383b12cb93c7']  #Put the trxid of the upvote or transfer after which you want to start the bot.
votelist=[]
total=0  

curr_round=[]
last_round=[]
%store curr_round
%store last_round

def convt(amt,curr):
    r1 = requests.get('https://api.coinmarketcap.com/v1/ticker/steem-dollars/')
    r2 = requests.get('https://api.coinmarketcap.com/v1/ticker/steem/')
    tkr1=r1.json()[0]['price_usd']
    tkr2=r2.json()[0]['price_usd']
    conv=float(tkr2)/float(tkr1)
    
    print ("Converting", amt, curr)
    famt = amt*conv
    fcurr = 'SBD'
    print ("Converted to",famt,fcurr)
    
    return (famt,fcurr)

def refund (bidder,amt,curr,msg):
    if (0.01<amt<1.0):
        memo = 'Refund for invalid bid: ' + msg
        s.commit.transfer(bidder,amt,curr,memo,acc_name)
        print (memo)
    return

def upvote (votelist,total):
    global last_round
    last_round=copy.deepcopy(curr_round)
    ind=0
    for j in votelist:
        wgt=round(j[0]*100/total,4)
        link = j[2][j[2].find('@'):]
        s.commit.vote(link,wgt,acc_name)
        last_round[ind]['weight']=int(wgt*100)
        ind+=1        
        time.sleep(4)
        print ("Upvoted, weight:",link,wgt)
        
    for k in votelist:
        wgt=round(k[0]*100/total,4)
        link = k[2][k[2].find('@'):]
        comment = 'You got a ' + str(wgt) + '% ' + 'upvote from @' + acc_name + ' courtesy of @' +  k[3]
        s.commit.post(title='',author=acc_name,body=comment,reply_identifier=link)
        time.sleep(22)
        print ("Upvoted, comment:",comment)        
        
    return
    
def validate (bidder,amt,curr,memo):
    
        ### Validation: Min Bid Amt (0.05 SBD)
    if (amt<0.05):
        refund(bidder,amt,curr,'Min Bid amount is 0.05 SBD')
        return ("Invalid")
                
        ### Validation: Valid URL, Post Age, Voted or Not?
    global votelist
    
    pl = memo[memo.find('@'):]
    perm = pl[pl.find('/')+1:]
    auth = pl[1:pl.find('/')]
    urlapi = memo[memo.find('.com/')+4:]
    memos = [x[2][x[2].find('@'):] for x in votelist]
    
    d = timedelta(days=6)
    
    try:
        post = steem.post.Post(pl,s)
                
        votl = [x['voter'] for x in s.get_active_votes(auth,perm)]
        
        if (post.is_main_post()):
        
            if (post.time_elapsed()<d):
                           
                if (acc_name not in votl):
                    
                    if (pl not in memos):
                        global curr_round
                        curr_round.append({"amount":amt,"currency":curr,"sender":bidder,"author":auth,"permlink":perm,"url":urlapi})
                        %store curr_round
                        return ("Valid")
                    else:
                        return("Invalid")
            
                else:
                    refund (bidder,amt,curr,'Post is already upvoted')
                    return ("Invalid")
            
            else:
                refund (bidder,amt,curr,'Max Post Age exceeded')
                return ("Invalid")
        else:
            refund (bidder,amt,curr,'Invalid URL')
            return ("Invalid")
                    
    except:
        refund (bidder,amt,curr,'Invalid URL')
        return ("Invalid")        


while True:
    
       
    try:
            
        gen1= ac.get_account_history(-1,100,filter_by=['transfer','vote'])
        gen2= ac.get_account_history(-1,100,filter_by=['vote'])
    
        for k in gen2:
            if (k['voter'] == acc_name):
                prev_time = datetime.datetime.strptime(k['timestamp'], "%Y-%m-%dT%H:%M:%S")
                break
        tt = timedelta(seconds=20+(10000-s.get_account(acc_name)['voting_power'])*43.2)
        print ("Previous vote time",prev_time)
        print ("Next vote time", prev_time + tt)
    
        if (datetime.datetime.utcnow() - prev_time>tt):
        #if (s.get_account(acc_name)['voting_power']>=10000):
            print ("Upvoting: votelist,total=",votelist,total)
            upvote(votelist,total)
            curr_round = []
            votelist = []
            total = 0
            trxlist.reverse()
            trxlist = trxlist[0:100]                               
            print ("After upvoting: trxlist=",trxlist)
            %store last_round
            %store curr_round
    
    
    
        for i in gen1:
        
            print (i)
            print ("Votelist: ",votelist)
            print ("TrxList: ",trxlist)
        
            if (i['trx_id'] in trxlist):
                print ("Breaking...")
                break
            
            if (i['type']=='transfer'):
                if (i['to']==acc_name):
                    bidder = i['from']
                    memo = i['memo']
                    amt,curr = i['amount'].split(" ")
                    amt = float (amt)
                    trxlist.append(i['trx_id'])
                    print ("Trxlist after append=",trxlist)
                
                    if (validate(bidder,amt,curr,memo)=="Valid"):
                        print ("Valid")
                        
                        if (curr == 'STEEM'):
                            amt,curr = convt(amt,curr)
                        
                        votelist.append([round(amt,3),curr,memo,bidder])
                        total = total + amt
                        print ("Votelist , total after append",votelist,total)
                
        print ("Sleeping...")
        time.sleep(10)
    
    except KeyboardInterrupt:
        print ("Interrupted")
        break
