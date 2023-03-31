#Class for team objs
class team:

    def __init__(self, name, adjEM, luck, sos):
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