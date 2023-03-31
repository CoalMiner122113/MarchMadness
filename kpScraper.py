from objDef import team
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webbrowser import Chrome

#driver.get("https://kenpom.com/index.php?y=2023")
#https://kenpom.com/index.php?y=
#driver.maximize_window()

def startDriver(year):
    #Oddly crucial option instantiation (also in driver declaration)
    driver = webdriver.Chrome(ChromeDriverManager().install())
    #Browser and website instantiation
    driver.get("https://kenpom.com/index.php?y="+str(year))
    driver.minimize_window()
    return(driver)

def statStrToFloat(statLine):

    if(statLine[0]=='-'):
        statLine = float(statLine.strip("-"))
        return -statLine
    elif(statLine[0]=='+'):
        return float(statLine.strip("+"))
    else:
        return float(statLine)

def getTableData(bodyNum, rowNum, driver):
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
    return(team(name, (adjEM), (luck), (sos)))
    #arr[((bodyNum-1)*40)+rowNum-1] = team(name, (adjEM), (luck), (sos))
    
   

##The data goes back to 2002, so we need to loop through the years (21 in 2023)
def cycleThroughYears(arrayOfYears, start, end):
    
    for i in range(start,end+1):
        driver = startDriver(i)
        #Set the body variables
        bodyNum = 1
        rowNum = 1
        
        while(bodyNum<10):
            rowNum = 1

            if(bodyNum != 9):

                while(rowNum < 41):
                    arrayOfYears[i-start][((bodyNum-1)*40)+rowNum-1] = getTableData(bodyNum,rowNum,driver)
                    rowNum+=1
            else:

                while(rowNum < 4):
                    arrayOfYears[i-start][((bodyNum-1)*40)+rowNum-1] = getTableData(bodyNum,rowNum,driver)
                    rowNum+=1
            
            bodyNum+=1 
        driver.close()
    
