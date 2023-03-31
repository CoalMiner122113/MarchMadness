import mysql.connector as sql
from mysql.connector import Error
from objDef import team

##Set up connection to MySQL server and marchMadness database
def setup():
    try:
        connection = sql.connect(host = 'localhost',
                                user = 'root',
                                password = '$quareUpCowboy')
        if connection.is_connected():
            print("Server:", connection.get_server_info())
            cursor = connection.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS marchMadness;")
            cursor.execute("USE marchMadness;")
            cursor.execute("SELECT database();")
            record = cursor.fetchone()
            print("You're connected to DB : ", record)
    except Error as e :
        print("Error : ", e)

    #Setting up a table for each year of data in kenpom database (the +1 is to include 2023)
    for year in range(2002, 2023+1):
        table = "year" + str(year)
        query = "CREATE TABLE IF NOT EXISTS " + table + " (name VARCHAR(35), adjem FLOAT, luck FLOAT, sos FLOAT);"
        cursor.execute(query)

    cursor.close()
    return(connection)


def getConnection():
    try:
        connection = sql.connect(host = 'localhost',
                                user = 'root',
                                password = '$quareUpCowboy')
        if connection.is_connected():
            print("Server:", connection.get_server_info())
            cursor = connection.cursor()
            cursor.execute("USE marchMadness;")
            cursor.execute("SELECT database();")
            record = cursor.fetchone()
            print("You're connected to DB : ", record)
    except Error as e :
        print("Error : ", e)
    
    cursor.close()
    return(connection)


def downloadFromSQL(arr, year):
    ##create connection and cursor from setup
    connection = getConnection()
    cursor = connection.cursor()
    ##Parse through the db and download the data into the array
    size = len(arr)
    for i in range(0, size):
        i+1
    ##Close the connection and cursor
    cursor.close()
    connection.close()

def uploadToSQL(arr, year):
    ##create connection and cursor from setup
    connection = getConnection()
    cursor = connection.cursor()
    size = len(arr)
    table = "year" + str(year)
    ##Parse through the array and upload the data into the db
    for i in range(0, size):
        ##if the end of the list is reached, break out of the loop
        if(arr[i] == 0):
            break
        name = (str)(arr[i].name)
        ##Replace apostrophes with double apostrophes to avoid SQL syntax errors
        name = name.replace("'", "''")
        adjEM = arr[i].adjEM
        luck = arr[i].luck
        sos = arr[i].sos
        query = "INSERT INTO " + table + " (name, adjem, luck, sos) VALUES ('%s', %f, %f, %f);" %(name, adjEM, luck, sos)
        cursor.execute(query)
        connection.commit()
    ##Close the connection and cursor
    cursor.close()
    connection.close()
    
def resetDB():
    ##create connection and cursor from setup
    connection = getConnection()
    cursor = connection.cursor()
    ##Parse through the db and delete all the tables
    for year in range(2002, 2023+1):
        table = "year" + str(year)
        query = "DROP TABLE IF EXISTS " + table + ";"
        cursor.execute(query)
    ##Close the connection and cursor
    query = "DROP TABLE IF EXISTS yearTest;"
    cursor.execute(query)
    connection.commit()
    cursor.close()
    connection.close()
    connection = setup()
    connection.close()

def testSQL():
    ##Setup connection and cursor for test environment
    connection = setup()
    cursor = connection.cursor()
    query = "CREATE TABLE IF NOT EXISTS yearTest (name VARCHAR(30), adjem FLOAT, luck FLOAT, sos FLOAT);"
    cursor.execute(query)
    connection.commit()
    cursor.close()
    connection.close()
    
    ##Test data
    teamTest1 = team("test1", 1.0, 2.1092, 3.129288)
    teamTest2 = team("test2", 4.00001, 5, 6.9029122)
    testArr = [teamTest1, teamTest2]
    uploadToSQL(testArr, "Test")
    # records = cursor.fetchall()
    # print("Total number of rows in year2021 is: ", cursor.rowcount)
    # print("Printing each row's column values i.e.  team record")
    # for row in records:
    #     print("Name = ", row[0])
    #     print("adjEM = ", row[1])
    #     print("luck = ", row[2])
    #     print("sos = ", row[3]

# resetDB()
# testSQL()
setup()