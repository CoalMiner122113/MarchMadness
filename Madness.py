## March Madness Picka #4
## Process:
## Collect all Team Data thru KenPom Web Crawl
## Individually Simulate Each Game
## Use Default Odds, But...
## Each Game Prompts User Entry For "Variability"
## Variability Favors Underdog
## E.G. 5% Variabililty Adds 2.5% Odds To Underdog, Takes 2.5% From Favorite

##Step 1: Create Team Data Repository
##Iterate Over KenPom Table, First Row is Data Key

##Instantiate Match-Up Data Format
##Arrays of Tuples, Each Tuple is a Matchup, and decides the Values of the Next Round of Arrays
##Each Matchup has two keys, one for each team

##Simulate MatchUps
##Determine probability of outcome, prompt user to enter their variability
##Store Winners in next round bracket
## Repeat for each division, then each round

from asyncio.windows_events import NULL
from msilib.schema import Class
import math
import random
from os import stat
from pydoc import classname
from random import random
import numpy
import selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webbrowser import Chrome
import sys

#Class for team objs
class team:

    def __init__(self, name, adjEM, luck, sos ):
        self.name = name
        self.adjEM = adjEM
        self.luck = luck
        self.sos = sos
        self.probability = 0
    
    def versus(self, team2):
        print(self.name,"plays", team2.name)
        numSelf = (self.adjEM + self.sos)
        if(numSelf<1):
            numSelf = 1
        numOther = (team2.adjEM + team2.sos)
        if(numOther<1):
            numOther = 1
        totLuck = 0
        if(numSelf > numOther):
            chance = numOther/numSelf
            team2.probability = 1/(1+1/chance)
            self.probability = 1 - team2.probability
        
        elif(numSelf <= numOther):
            chance = numSelf/numOther
            self.probability = 1/(1+1/chance)
            team2.probability = 1 - self.probability

        if(self.luck > team2.luck):
            totLuck = self.luck - team2.luck
            self.probability += (totLuck/2)
            team2.probability -= (totLuck/2)
        elif(self.luck < team2.luck):
            totLuck = team2.luck - self.luck
            team2.probability += (totLuck/2)
            self.probability -= (totLuck/2)

        #print(self.name+" stats are "+ "AdjEm "+ str(self.adjEM)+" sos "+str(self.sos)+" luck "+str(self.luck))
        #print(team2.name+" stats are "+ "AdjEm "+ str(team2.adjEM)+" sos "+str(team2.sos)+" luck "+str(team2.luck) + "\nChance "+str(chance))

def statStrToFloat(statLine):

    if(statLine[0]=='-'):
        statLine = float(statLine.strip("-"))
        return -statLine
    elif(statLine[0]=='+'):
        return float(statLine.strip("+"))
    else:
        return float(statLine)

def getTableData(bodyNum, rowNum):
    tdXpath = '//*[@id="ratings-table"]/tbody['+str(bodyNum) + ']'+'/tr[' + str(rowNum) + ']'
    tdNum = 2
    tdXpath += '/td[' +str(tdNum) + ']'
    name = driver.find_element(By.XPATH, tdXpath).text.strip(" 01234567890 ")
    tdXpath = '//*[@id="ratings-table"]/tbody['+str(bodyNum) + ']'+'/tr[' + str(rowNum) + ']'
    tdNum = 5
    tdXpath += '/td[' +str(tdNum) + ']'
    adjEM = statStrToFloat(driver.find_element(By.XPATH, tdXpath).text)
    tdXpath = '//*[@id="ratings-table"]/tbody['+str(bodyNum) + ']'+'/tr[' + str(rowNum) + ']'
    tdNum = 12
    tdXpath += '/td[' +str(tdNum) + ']'
    luck = statStrToFloat(driver.find_element(By.XPATH, tdXpath).text)
    tdXpath = '//*[@id="ratings-table"]/tbody['+str(bodyNum) + ']'+'/tr[' + str(rowNum) + ']'
    tdNum = 14
    tdXpath += '/td[' +str(tdNum) + ']'
    sos = statStrToFloat(driver.find_element(By.XPATH, tdXpath).text)
    arr[((bodyNum-1)*40)+rowNum-1] = team(name, (adjEM), (luck), (sos))
    print("array " + str((bodyNum-1)*40+rowNum-1) + " is " + str(arr[((bodyNum-1)*40)+rowNum-1]) )


#Oddly crucial option instantiation (also in driver declaration)
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
#Browser and website instantiation
driverService = Service('./chromedriver')
driver = webdriver.Chrome(options=options, service=driverService)
driver.get("https://kenpom.com/")
#driver.maximize_window()

bodyNum = 1
rowNum = 1
tdNum = 1

arr = [team(0,0,0,0)]*450

while(bodyNum<10):
    rowNum = 1

    if(bodyNum != 9):

        while(rowNum < 41):
            
            getTableData(bodyNum,rowNum)
            rowNum+=1

    else:

        while(rowNum < 4):
            
            getTableData(bodyNum,rowNum)
            rowNum+=1
    
    bodyNum+=1

def getTeam(name1):
    retTeam = team ("Error",0,0,0)
    for teams in arr:
        if (teams.name == name1):
            retTeam = teams
    return retTeam      
        
    

#Have to Hard Code the seeding, can't fix unless I pull seed names from another website and do an array search by name

def tourney():
    roundA = [ getTeam("Gonzaga"),getTeam("Gonzaga"),getTeam("Memphis"),getTeam("Memphis"),getTeam("New Mexico St."),getTeam("New Mexico St."),getTeam("Arkansas"),getTeam("Arkansas"),getTeam("Alabama"),getTeam("Notre Dame"),getTeam("Texas Tech"),getTeam("Montana St."),getTeam("Michigan St."),getTeam("Davidson"),getTeam("Duke"),getTeam("Cal St. Fullerton")]
    roundB = [ getTeam("Baylor"),getTeam("Baylor"),getTeam("North Carolina"),getTeam("North Carolina"),getTeam("Saint Mary's"),getTeam("Saint Mary's"),getTeam("UCLA"),getTeam("Akron"),getTeam("Texas"),getTeam("Virginia Tech"),getTeam("Purdue"),getTeam("Yale"),getTeam("Murray St."),getTeam("San Francisco"),getTeam("Saint Peter's"),getTeam("Saint Peter's")]
    roundC = [ getTeam("Arizona"),getTeam("Wright St."),getTeam("Seton Hall"),getTeam("TCU"),getTeam("Houston"),getTeam("UAB"),getTeam("Illinois"),getTeam("Chattanooga"),getTeam("Michigan"),getTeam("Michigan"),getTeam("Tennessee"),getTeam("Tennessee"),getTeam("Ohio St. "),getTeam("Loyola Chicago"),getTeam("Villanova"),getTeam("Delaware")]
    roundD = [ getTeam("Kansas"),getTeam("Texas Southern"),getTeam("Creighton"),getTeam("Creighton"),getTeam("Richmond"),getTeam("Richmond"),getTeam("Providence"),getTeam("Providence"),getTeam("LSU"),getTeam("Iowa St."),getTeam("Wisconsin"),getTeam("Colgate"),getTeam("USC"),getTeam("Miami Fl"),getTeam("Auburn"),getTeam("Jacksonville St.")]
    brackets = [roundA, roundB, roundD, roundC]
    bracketNum = 0
    while(bracketNum < 4):
        currBracket = brackets[bracketNum]
        gameNum = 0
        while(gameNum < 8):

            currBracket[gameNum*2].versus(currBracket[gameNum*2+1])
            fact = random()
            if(currBracket[gameNum*2].probability > currBracket[gameNum*2+1].probability):
                if(fact < currBracket[gameNum*2].probability):
                    winner = currBracket[gameNum*2]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact))
                elif(fact >= currBracket[gameNum*2].probability):
                    winner = currBracket[gameNum*2+1]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )
            elif(currBracket[gameNum*2+1].probability >= currBracket[gameNum*2].probability):
                if(fact < currBracket[gameNum*2+1].probability):
                    winner = currBracket[gameNum*2+1]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )
                elif(fact >= currBracket[gameNum*2+1].probability):
                    winner = currBracket[gameNum*2]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )

            currBracket[gameNum] = winner
            gameNum+=1
        gameNum = 0
        while(gameNum < 4):

            currBracket[gameNum*2].versus(currBracket[gameNum*2+1])
            fact = random()
            if(currBracket[gameNum*2].probability > currBracket[gameNum*2+1].probability):
                if(fact < currBracket[gameNum*2].probability):
                    winner = currBracket[gameNum*2]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact))
                elif(fact >= currBracket[gameNum*2].probability):
                    winner = currBracket[gameNum*2+1]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )
            elif(currBracket[gameNum*2+1].probability >= currBracket[gameNum*2].probability):
                if(fact < currBracket[gameNum*2+1].probability):
                    winner = currBracket[gameNum*2+1]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )
                elif(fact >= currBracket[gameNum*2+1].probability):
                    winner = currBracket[gameNum*2]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )

            currBracket[gameNum] = winner
            gameNum+=1
        gameNum = 0
        while(gameNum < 2):

            currBracket[gameNum*2].versus(currBracket[gameNum*2+1])
            fact = random()
            if(currBracket[gameNum*2].probability > currBracket[gameNum*2+1].probability):
                if(fact < currBracket[gameNum*2].probability):
                    winner = currBracket[gameNum*2]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact))
                elif(fact >= currBracket[gameNum*2].probability):
                    winner = currBracket[gameNum*2+1]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )
            elif(currBracket[gameNum*2+1].probability >= currBracket[gameNum*2].probability):
                if(fact < currBracket[gameNum*2+1].probability):
                    winner = currBracket[gameNum*2+1]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )
                elif(fact >= currBracket[gameNum*2+1].probability):
                    winner = currBracket[gameNum*2]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )

            currBracket[gameNum] = winner
            gameNum+=1
        gameNum = 0
        while(gameNum < 1):

            currBracket[gameNum*2].versus(currBracket[gameNum*2+1])
            fact = random()
            if(currBracket[gameNum*2].probability > currBracket[gameNum*2+1].probability):
                if(fact < currBracket[gameNum*2].probability):
                    winner = currBracket[gameNum*2]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact))
                elif(fact >= currBracket[gameNum*2].probability):
                    winner = currBracket[gameNum*2+1]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )
            elif(currBracket[gameNum*2+1].probability >= currBracket[gameNum*2].probability):
                if(fact < currBracket[gameNum*2+1].probability):
                    winner = currBracket[gameNum*2+1]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )
                elif(fact >= currBracket[gameNum*2+1].probability):
                    winner = currBracket[gameNum*2]
                    print("The winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )

            currBracket[gameNum] = winner
            gameNum+=1
        bracketNum+=1

    roundA[0].versus(roundB[0])
    fact = random()
    if(roundA[0].probability > roundB[0].probability):
        if(fact < roundA[0].probability):
            winner = roundA[0]
            print("The AB winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact))
        elif(fact >= roundA[0].probability):
            winner = roundB[0]
            print("The AB winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )
    elif(roundB[0].probability >= roundA[0].probability):
        if(fact < roundB[0].probability):
            winner = roundB[0]
            print("The AB winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )
        elif(fact >= roundB[0].probability):
            winner = currBracket[0]
            print("The AB winner is "+ winner.name + " at probability"+ str(winner.probability)+" with ran = "+str(fact) )

    roundC[0].versus(roundD[0])
    fact = random()
    if(roundC[0].probability > roundD[0].probability):
        if(fact < roundC[0].probability):
            winner2 = roundC[0]
            print("The BC winner2 is "+ winner2.name + " at probability"+ str(winner2.probability)+" with ran = "+str(fact))
        elif(fact >= roundC[0].probability):
            winner2 = roundD[0]
            print("The BC winner2 is "+ winner2.name + " at probability"+ str(winner2.probability)+" with ran = "+str(fact) )
    elif(roundD[0].probability >= roundC[0].probability):
        if(fact < roundD[0].probability):
            winner2 = roundD[0]
            print("The BC winner2 is "+ winner2.name + " at probability"+ str(winner2.probability)+" with ran = "+str(fact) )
        elif(fact >= roundD[0].probability):
            winner2 = currBracket[0]
            print("The BC winner2 is "+ winner2.name + " at probability"+ str(winner2.probability)+" with ran = "+str(fact) )


    winner.versus(winner2)
    fact = random()
    if(winner.probability > winner2.probability):
        if(fact < winner.probability):
            winnerOVA = winner
            print("The BC winner2 is "+ winnerOVA.name + "at probability"+ str(winnerOVA.probability)+" with ran = "+str(fact))
        elif(fact >= winner.probability):
            winnerOVA = winner2
            print("The BC winner2 is "+ winnerOVA.name + "at probability"+ str(winnerOVA.probability)+" with ran = "+str(fact) )
    elif(winner2.probability >= winner.probability):
        if(fact < winner2.probability):
            winnerOVA = winner2
            print("The BC winner2 is "+ winnerOVA.name + "at probability"+ str(winnerOVA.probability)+" with ran = "+str(fact) )
        elif(fact >= winner2.probability):
            winnerOVA = winner2
            print("The BC winner2 is "+ winnerOVA.name + "at probability"+ str(winnerOVA.probability)+" with ran = "+str(fact) )

print(getTeam("Gonzaga").name)

keepRun = 'true'
while(keepRun != 'stop'):
    tourney()
    keepRun = input("\n\n\n\n\nEnter 'stop' to exit : ")

#for team in currBracket:
#    print(team.name)

    

#TTU = team("Texas Tech University", 24.64, -.025, 10.21)
#OU = team("Oklahoma University", 15.96, -.044, 11.92)

#TTU.versus(OU)
#print("\nTTU %:", TTU.probability*100)
#print("\nOU %:", OU.probability*100)
