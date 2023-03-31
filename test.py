## This file is designed to test the Selenium functionality
import numpy
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webbrowser import Chrome

#Oddly crucial option instantiation (also in driver declaration)
driver = webdriver.Chrome(ChromeDriverManager().install())
#Browser and website instantiation
driver.get("https://kenpom.com/")
#driver.maximize_window()
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
    print("array " + str((bodyNum-1)*40+rowNum-1) + " is " + str(arr[((bodyNum-1)*40)+rowNum-1].name) )



bodyNum = 1
rowNum = 1
tdNum = 1

arr = [team(0,0,0,0)]*350

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