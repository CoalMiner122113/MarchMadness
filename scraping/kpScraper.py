from app_logic.objDef import team
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webbrowser import Chrome
from dotenv import dotenv_values

config = dotenv_values(".env")

#driver.get("https://kenpom.com/index.php?y=2023")
#https://kenpom.com/index.php?y=
#driver.maximize_window()

def startDriver(year):
   #Specifying the params for the chrome driver

    chrome_path = "C:\Program Files\Google\Chrome\Application\chrome.exe"
    chrome_driver_path  = config['CHROMEDRIVER_PATH']
    chrome_options = Options()
    chrome_options.binary_location= chrome_path
    ##Can't be headless, so leaving this out for now...
    #chrome_options.add_argument("--headless")

    service = Service(chrome_driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    #Browser and website instantiation
    driver.get("https://kenpom.com/index.php?y="+str(year))
    #driver.maximize_window()
    
    return driver

def statStrToFloat(statLine):

    if(statLine[0]=='-'):
        statLine = float(statLine.strip("-"))
        return -statLine
    elif(statLine[0]=='+'):
        return float(statLine.strip("+"))
    else:
        return float(statLine)

def getTableData(row_element):
    cells = row_element.find_elements(By.TAG_NAME, "td")
    
    #The name contains the tournament seed, so we need to strip that out
    name = cells[1].text.strip(" 01234567890 ")
    #+/- is a special case, so we need to handle it with a special function statStrToFloat
    adjEM = statStrToFloat(cells[4].text)
    luck = statStrToFloat(cells[11].text)
    sos = statStrToFloat(cells[13].text)
    
    return name, adjEM, luck, sos
    
   

##The data goes back to 2002, so we need to loop through the years (21 in 2023)
def cycleThroughYears(arrayOfYears, start, end):
    #Start with an empty array that will be added to the arrayOfYear
    teams = []
    #Loop through the years, end +1 because range is exclusive
    for i in range(start,end+1):
        driver = startDriver(i)
        scrapeSite(teams, driver)
        driver.close()
        arrayOfYears.append(teams)
        
def scrapeSite(teams, driver):
    
    #The table where the data is contained
    table = driver.find_element(By.ID, 'ratings-table')
    #The table consists of multiple tbody elements, so we need to get all of them
    tbody_elements = table.find_elements(By.TAG_NAME, 'tbody')
    
    for tbody in tbody_elements:
        #Get all rows (aka teams) in the tbody
        rows = tbody.find_elements(By.TAG_NAME, "tr")
    
        for row in rows:
            #Get the data from each row (team)
            name, adjEM, luck, sos = getTableData(row)
            teams.append(team(name, adjEM, luck, sos))
