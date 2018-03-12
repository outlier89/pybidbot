import steem
import time
import datetime
import math
import signal
import copy
import requests
import sys
import traceback
from steem import Steem
from datetime import timedelta

nodes = ['https://api.steemit.com',
         'https://rpc.buildteam.io',
         'https://steemd.minnowsupportproject.org',
         'https://steemd.privex.io',
         'https://gtg.steem.house:8090']

acc_name = 'therising'                                #Replace therising with your steem account name.
s = Steem(nodes, keys=['Your_Private_Posting_Key', 'Your_Private_Active_Key'])

firstrun= True
rndlimit= False                                        #Set to True if you want to enable round fill limit
trxlist=[]
votelist=[]
total=0
errcnt=0

curr_round=[]
last_round=[]
#%store curr_round                          # Uncomment all %store statements if you want to enable api
#%store last_round


def node_failover():
    global nodes,s
    nodes = nodes[1:] + nodes[:1]
    print ("Switching to the next node: ",nodes)
    s = Steem(nodes)
    return
    

def get_vote_value(account_name):
    total_vests=float(s.get_account(account_name)['vesting_shares'].split(" ")[0]) + float(s.get_account(account_name)['received_vesting_shares'].split(" ")[0])
    vests_steem= total_vests*(10**6)*0.02*float(s.get_reward_fund('post')['reward_balance'].split(" ")[0])/float(s.get_reward_fund('post')['recent_claims'])
    vests_sbd = vests_steem*float(s.get_current_median_history_price()['base'].split(" ")[0])/float(s.get_current_median_history_price()['quote'].split(" ")[0])
    vote_value = (vests_sbd/(2*float(requests.get('https://api.coinmarketcap.com/v1/ticker/steem-dollars/').json()[0]['price_usd'])))+(vests_sbd/2)
    vote_value = round(vote_value,2)
    return (vote_value)


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
    global firstrun,errcnt
    if ((0.01<amt<100.0) and (not firstrun)):
        memo = 'Refund for invalid bid: ' + msg
        for i in range(16):
            try:
                s.commit.transfer(bidder,amt,curr,memo,acc_name)
                break
            except:
                print ("Refund error: ", sys.exc_info()[0])
                print (traceback.format_exc())
                errcnt+=1
                if (errcnt>=5):
                    node_failover()
                    errcnt=0
                time.sleep(3)
        print (memo)
    elif (firstrun):
        print ("No refund: First Run")
    else:
        print ("No refund: Amt not eligible")
    return

def upvote (votelist,total):
    global last_round,curr_round,errcnt

    last_round=copy.deepcopy(curr_round)
    curr_round = []
    
    ind=0
    errcnt=0
    for j in votelist:
        wgt=round(j[0]*100/(total),2)
        link = j[2][j[2].find('@'):]
        while True:
            try:
                s.commit.vote(link,wgt,acc_name)
                break
            except:
                print ("Voting error: ", sys.exc_info()[0])
                print (traceback.format_exc())
                errcnt+=1
                if (errcnt>=5):
                    node_failover()
                    errcnt=0
                time.sleep(4)
            
        last_round[ind]['weight']=int(wgt*100)
        ind+=1        
        time.sleep(5)
        print ("Upvoted, weight:",link,wgt)
    
   # %store last_round
   # %store curr_round
                                             #Comment
    for k in votelist:
        wgt=round(k[0]*100/(total),2)
        link = k[2][k[2].find('@'):]
        comment = 'You just rose by ' + str(wgt) + '% upvote from @' + acc_name + ' courtesy of @' +  k[3]     
        while True:
            try:
                s.commit.post(title='',author=acc_name,body=comment,reply_identifier=link)
                break
            except:
                print ("Commenting error: ", sys.exc_info()[0])
                print (traceback.format_exc())
                errcnt+=1
                if (errcnt>=5):
                    node_failover()
                    errcnt=0
                time.sleep(3)
        time.sleep(22)
        print ("Upvoted & commented:",link)        
        
    return
    
def validate (bidder,amt,curr,memo):
    
    global votelist,curr_round,total,rndlimit

        ### Validation: Min Bid Amt (1.0 SBD)
    if (amt<1.0):
        refund(bidder,amt,curr,'Min Bid amount is 1 SBD')
        return ("Invalid")
                

        ### Validation: Round Fill Limit
    if (rndlimit):
        try:
            vote_value=get_vote_value(acc_name)
            curr_vote_value=round(0.75*vote_value*1.0,3)
            print ("Vote Value: ",curr_vote_value)
        
            if (curr == 'STEEM'):
                namt,ncurr = convt(amt,curr)
            
                if ((total+namt)>curr_vote_value):
                    refund(bidder,amt,curr,'Our bot guarantees profit or atleast breakeven for our bot-users. Please bid in the next round as current round is already around breakeven.')
                    return ("Invalid")

            
            if ((total+amt)>curr_vote_value):
                print ("Total round amt:")
                refund(bidder,amt,curr,'Our bot guarantees profit or atleast breakeven for our bot-users. Please bid in the next round as current round is already around breakeven.')
                return ("Invalid")
        except:
            print ("Round Limit Error: ",sys.exc_info()[0])
            print (traceback.format_exc())



        ### Validation: Valid URL, Post Age, Voted or Not?
    
    
    pl = memo[memo.find('@'):]
    perm = pl[pl.find('/')+1:]
    auth = pl[1:pl.find('/')]
    urlapi = memo[memo.find('.com/')+4:]
    memos = [x[2][x[2].find('@'):] for x in votelist]
    
    d = timedelta(days=3.5)
    
    try:
        post = steem.post.Post(pl,s)
                
        votl = [x['voter'] for x in s.get_active_votes(auth,perm)]
        
        if (post.is_main_post()):
        
            if (post.time_elapsed()<d):
                           
                if (acc_name not in votl):
                    
                    if (pl not in memos):
                        
                        curr_round.append({"amount":amt,"currency":curr,"sender":bidder,"author":auth,"permlink":perm,"url":urlapi})
                        #%store curr_round
                        return ("Valid")
                    
                    else:
                        curr_round[memos.index(pl)]['amount']+=round(amt,3)
                        #%store curr_round
                        
                        if (curr == 'STEEM'):
                            amt,curr = convt(amt,curr)
                        
                        votelist[memos.index(pl)][0]+=round(amt,3)
                        total+=amt
                        return("Already Present in Votelist")
            
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
        print ("Validation error: ", sys.exc_info()[0])
        print (traceback.format_exc())
        return ("Invalid")        


while True:
    
       
    try:
        
        ac=steem.account.Account(acc_name,s)    
        gen1= ac.get_account_history(-1,500,filter_by=['transfer'])
        gen2= ac.get_account_history(-1,500,filter_by=['vote'])
    
        for k in gen2:
            if (k['voter'] == acc_name):
                prev_time = datetime.datetime.strptime(k['timestamp'], "%Y-%m-%dT%H:%M:%S")
                break
        tt = timedelta(seconds=30+(10000-s.get_account(acc_name)['voting_power'])*43.2)
        print ("Current Time: "+ str(datetime.datetime.utcnow()) +"|Prev vote: " + str(prev_time) + "|Next Vote: " + str(prev_time + tt))
    
    
        for i in gen1:
        
            if (i['trx_id'] in trxlist):
                print ("Breaking at TrxID: ",i['trx_id'])
                break
            
            if (i['to']==acc_name):
                bidder = i['from']
                memo = i['memo']
                amt,curr = i['amount'].split(" ")
                amt = float (amt)
                trxlist.append(i['trx_id'])
                print ("Trxlist after append=",trxlist)
                
                if (validate(bidder,amt,curr,memo)=="Valid"):
                        
                    if (curr == 'STEEM'):
                        amt,curr = convt(amt,curr)
                        
                    votelist.append([round(amt,3),curr,memo,bidder])
                    total = total + amt
                    print ("Votelist , total after append",votelist,total)
                
        #print ("Votelist: ",votelist,total)
        
        if ( (datetime.datetime.utcnow() - prev_time) > tt):           
            
            print ("Upvoting: votelist,total=",votelist,total)
            upvote(votelist,total)
            votelist = []
            total = 0
            trxlist = trxlist[0:5] + trxlist[-5:]

        
        firstrun=False
        time.sleep(10)
    
    except KeyboardInterrupt:
        print ("Interrupted")
        break
        
    except:
        print ("Unexpected error: ", sys.exc_info()[0])
        print (traceback.format_exc())
        errcnt+=1
        if (errcnt>=5):
            node_failover()
            errcnt=0
        time.sleep(10)
