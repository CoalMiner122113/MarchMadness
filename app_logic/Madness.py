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

from app_logic.objDef import team
from app_logic.TournamentLayout import tourney
from scraping.kpScraper import cycleThroughYears
#from sqlHandler import downloadFromSQL
from sql.sqlHandler import uploadToSQL, downloadFromSQL
import numpy as np


##Code to upload data to SQL, only need to run once
##Setting up the array of years, which will hold the kenpom data for each year for each team
# arrayOfYears = np.zeros((21,350), dtype=object)
# cycleThroughYears(arrayOfYears,2002,2023)
# for i in range(0,22):    
#     uploadToSQL(arrayOfYears[i],i+2002)

# arrayOfYears = []
# cycleThroughYears(arrayOfYears,2024,2024)
# uploadToSQL(arrayOfYears[0],2024)

# Global array to store teams
arr = []

def getTeam(name1):
    #find team based on name
    retTeam = team("Error",0,0,0)
    for teams in arr:
        if (teams.name == name1):
            retTeam = teams
    if(retTeam.name == "Error"):
        print("Error: Team not found " + name1)
    return retTeam      
    #Make aliases dict for the team
    #UConn = Connecticut
    #

# Download data from sql when module is imported
downloadFromSQL(arr, 2024)

if __name__ == "__main__":
    #Have to Hard Code the seeding, can't fix unless I pull seed names from another website and do an array search by name
    east = [ getTeam("Connecticut"),getTeam("Stetson"),getTeam("Florida Atlantic"),getTeam("Northwestern"),getTeam("San Diego St."),getTeam("UAB"),getTeam("Auburn"),getTeam("Yale"),getTeam("BYU"),getTeam("Duquesne"),getTeam("Illinois"),getTeam("Morehead St."),getTeam("Washington St."),getTeam("Drake"),getTeam("Iowa St."),getTeam("South Dakota St.")]
    west = [ getTeam("North Carolina"),getTeam("Wagner"),getTeam("Mississippi St."),getTeam("Michigan St."),getTeam("Saint Mary's"),getTeam("Grand Canyon"),getTeam("Alabama"),getTeam("Charleston"),getTeam("Clemson"),getTeam("New Mexico"),getTeam("Baylor"),getTeam("Colgate"),getTeam("Dayton"),getTeam("Nevada"),getTeam("Arizona"),getTeam("Long Beach St.")]
    south = [ getTeam("Houston"),getTeam("Longwood"),getTeam("Nebraska"),getTeam("Texas A&M"),getTeam("Wisconsin"),getTeam("James Madison"),getTeam("Duke"),getTeam("Vermont"),getTeam("Texas Tech"),getTeam("N.C. State"),getTeam("Kentucky"),getTeam("Oakland"),getTeam("Florida"),getTeam("Colorado"),getTeam("Marquette"),getTeam("Western Kentucky")]
    midwest = [ getTeam("Purdue"),getTeam("Grambling St."),getTeam("Utah St."),getTeam("TCU"),getTeam("Gonzaga"),getTeam("McNeese St."),getTeam("Kansas"),getTeam("Samford"),getTeam("South Carolina"),getTeam("Oregon"),getTeam("Creighton"),getTeam("Akron"),getTeam("Texas"),getTeam("Colorado St."),getTeam("Tennessee"),getTeam("Saint Peter's")]
    #Howard / Wagner
    #Boise St. / Colorado
    #Montana St. / Grambling
    #Virginia / Colorado St.

    tourney(east,west,south,midwest)

# keepRun = 'true'
# while(keepRun != 'stop'):
#     tourney()
#     keepRun = input("\n\n\n\n\nEnter 'stop' to exit : ")
