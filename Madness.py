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

from objDef import team
from TournamentLayout import tourney
from kpScraper import cycleThroughYears
#from sqlHandler import downloadFromSQL
from sqlHandler import uploadToSQL
import numpy as np


##Code to upload data to SQL, only need to run once
##Setting up the array of years, which will hold the kenpom data for each year for each team
# arrayOfYears = np.zeros((21,350), dtype=object)
# cycleThroughYears(arrayOfYears,2002,2023)
# for i in range(0,22):    
#     uploadToSQL(arrayOfYears[i],i+2002)

arrayOfYears = np.zeros((21,350), dtype=object)
cycleThroughYears(arrayOfYears,2023,2023)
uploadToSQL(arrayOfYears[0],2023)


def getTeam(name1):
    #download data from sql
    arr = arr
    retTeam = team ("Error",0,0,0)
    for teams in arr:
        if (teams.name == name1):
            retTeam = teams
    return retTeam      




#Have to Hard Code the seeding, can't fix unless I pull seed names from another website and do an array search by name
# roundA = [ getTeam("Alabama"),getTeam("Texas A&M Corpus Christi"),getTeam("Maryland"),getTeam("West Virginia"),getTeam("San Diego St."),getTeam("Charleston"),getTeam("Virginia"),getTeam("Furman"),getTeam("Creighton"),getTeam("N.C. State"),getTeam("Baylor"),getTeam("UC Santa Barbara"),getTeam("Missouri"),getTeam("Utah State"),getTeam("Arizona"),getTeam("Princeton")]
# roundB = [ getTeam("Purdue"),getTeam("Farleigh Dickinson"),getTeam("Memphis"),getTeam("FAU"),getTeam("Duke"),getTeam("Oral Roberts"),getTeam("Tennessee"),getTeam("Louisianna"),getTeam("Kentucky"),getTeam("Providence"),getTeam("Kansas St."),getTeam("Montana St."),getTeam("Michigan St."),getTeam("USC"),getTeam("Marquette"),getTeam("Vermont")]
# roundC = [ getTeam("Houston"),getTeam("North Kentucky"),getTeam("Iowa"),getTeam("Auburn"),getTeam("Miami"),getTeam("Drake"),getTeam("Indiana"),getTeam("Kansas St."),getTeam("Iowa St."),getTeam("Pittsburgh"),getTeam("Xavier"),getTeam("Kennesaw St."),getTeam("Texas A&M"),getTeam("Penn St."),getTeam("Texas"),getTeam("Colgate")]
# roundD = [ getTeam("Kansas"),getTeam("Howard"),getTeam("Arkansas"),getTeam("Illinois"),getTeam("St. Mary's"),getTeam("VCU"),getTeam("UConn"),getTeam("Iona"),getTeam("TCU"),getTeam("Arizona St."),getTeam("Gonzaga"),getTeam("Grand Canyon"),getTeam("Northwestern"),getTeam("Boise St."),getTeam("UCLA"),getTeam("UNC Asheville")]


# keepRun = 'true'
# while(keepRun != 'stop'):
#     tourney()
#     keepRun = input("\n\n\n\n\nEnter 'stop' to exit : ")
