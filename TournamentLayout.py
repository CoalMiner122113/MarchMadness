import math
import random

def tourney(roundA, roundB, roundC, roundD):
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
            winnerOVA = winner
            print("The BC winner2 is "+ winnerOVA.name + "at probability"+ str(winnerOVA.probability)+" with ran = "+str(fact) )
        elif(fact >= winner2.probability):
            winnerOVA = winner2
            print("The BC winner2 is "+ winnerOVA.name + "at probability"+ str(winnerOVA.probability)+" with ran = "+str(fact) )

