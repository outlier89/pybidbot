import steem
import time
import datetime
import signal
from steem import Steem
from datetime import timedelta

nodes = ['https://api.steemit.com',
         'https://rpc.buildteam.io',
         'https://steemd.minnowsupportproject.org',
         'https://steemd.privex.io',
         'https://gtg.steem.house:8090']

acc_name = 'whalebuilder'
s = Steem(nodes)

ac=steem.account.Account(acc_name,s)
trxlist=[]
votelist=[]
total=0  

def refund (bidder,amt,curr,msg):
    memo = 'Refund for invalid bid: ' + msg
    #s.commit.transfer(bidder,amt,curr,memo)
    print (memo)
    return

def upvote (votelist,total):
    for j in votelist:
        wgt=round(j[0]*100/total,4)
        link = j[2][j[2].find('@'):]
        comment = 'You got a ' + str(wgt) + '% ' + 'upvote from @' + acc_name + ' courtesy of @' +  j[3]
        #s.commit.vote(link,wgt,acc_name)
        #s.commit.post(title='',author=acc_name,body=comment,reply_identifier=link)
        print ("Upvoted, weight:",link,wgt)
    return
    
def validate (bidder,amt,curr,memo):
    
        # Validation: Min Bid Amt (0.05 SBD)
    if (amt<0.05):
        refund(bidder,amt,curr,'Min Bid amount is 0.05 SBD')
        return ("Invalid")
                
        # Validation: Valid URL, Post Age, Voted or Not?
    pl = memo[memo.find('@'):]
    perm = pl[pl.find('/')+1:]
    auth = pl[1:pl.find('/')]
    d = timedelta(days=6)
    try:
        post = steem.post.Post(pl,s)
                
        votl = [x['voter'] for x in s.get_active_votes(auth,perm)]
                
        if (post.is_main_post()):
        
            if (post.time_elapsed()<d):
                           
                if (acc_name not in votl):
                    return ("Valid")
            
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
    
        prev_vote = next(gen2)
        prev_time = prev_vote['timestamp']
        tt = timedelta(minutes=144)
        print ("Previous vote time",prev_time)
        print ("Next vote time",datetime.datetime.strptime(prev_time, "%Y-%m-%dT%H:%M:%S") + tt)
    
        if (datetime.datetime.utcnow() - datetime.datetime.strptime(prev_time, "%Y-%m-%dT%H:%M:%S")>tt):
            print ("Upvoting: votelist,total=",votelist,total)
            upvote(votelist,total)
            votelist = []
            total = 0
            trxlist.reverse()
            trxlist = trxlist[0:100]                                 #Change trxlist range for high Steem Power
            print ("After upvoting: trxlist=",trxlist)
    
    
    
        for i in gen1:
        
            print (i)
        
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
                        if (curr == 'STEEM'):
                            tkr = s.get_ticker()
                            conv = tkr['latest']
                            print ("Converting", amt, curr)
                            #amt = amt*float(conv)
                            #curr = 'SBD'
                            print ("Converted to",amt,curr)
                            
                        print ("Valid")
                        votelist.append([round(amt,3),curr,memo,bidder])
                        total = total + amt
                        print ("Votelist , total after append",votelist,total)
                
        print ("Sleeping...")
        time.sleep(5)
    
    except KeyboardInterrupt:
        print ("Interrupted")
        break    
