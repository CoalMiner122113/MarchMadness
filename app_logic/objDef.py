import math
import random
#Class for team objs
class team:

    def __init__(self, name, adjEM, luck, sos):
        self.name = name
        self.adjEM = adjEM
        self.luck = luck
        self.sos = sos
        self.probability = 0
    
    def normalize_adjEM(self, team2, round_num):
        r_min = -33
        r_max = 33
        t_min = 0
        t_max = 45
        max_diff_percent = [0.91, 0.77, 0.7, 0.63, 0.56, 0.49]  #Maximum % difference in AdjEM for each round

        #array to hold the normalized adjEMs (we dont want to change the original adjEMs)
        normalizedAdjEMs = [self.adjEM, team2.adjEM]
        
        #normalize the adjEMs
        scaling_factor = (t_max - t_min) / (r_max - r_min)
        normalizedAdjEMs[0] = (self.adjEM - r_min) * scaling_factor + t_min
        normalizedAdjEMs[1] = (team2.adjEM - r_min) * scaling_factor + t_min
        
        #determine max % change, the higher the round, the tighter the range
        max_adjEM = max(abs(normalizedAdjEMs[0]), abs(normalizedAdjEMs[0]))
        max_diff = max_adjEM * max_diff_percent[round_num - 1]
        
        #if team1's adjEM is greater than team2's by more than the max change %, we elevate team 2's adjEM
        if normalizedAdjEMs[0] > (normalizedAdjEMs[1] + max_diff):
            normalizedAdjEMs[1] = normalizedAdjEMs[0] - max_diff
        #if team2's adjEM is greater than team1's by more than the max change %, we elevate team 1's adjEM
        elif normalizedAdjEMs[1] > (normalizedAdjEMs[0] + max_diff):
            normalizedAdjEMs[0] = normalizedAdjEMs[1] - max_diff
        
        return normalizedAdjEMs
    
    def versus(self, team2, round_num):
        print("\n")
        print(self.name, "plays", team2.name)

        # Normalize Adjusted Efficiency Margin for the two teams based on round number
        normalized = self.normalize_adjEM(team2, round_num)
        normalizedAdjEM1 = normalized[0]
        normalizedAdjEM2 = normalized[1]

        # Calculate strength for each team
        if(self.sos > 0):
            self_strength = normalizedAdjEM1 + (math.sqrt(self.sos))
        else:
            self_strength = normalizedAdjEM1 + (0 - (math.sqrt(abs(self.sos))))
        if(team2.sos > 0):
            team2_strength = normalizedAdjEM2 + (math.sqrt(team2.sos))
        else:
            team2_strength = normalizedAdjEM2 + (0 - (math.sqrt(abs(team2.sos))))

        # Calculate probability of winning based on relative strengths
        self_probability = self_strength / (self_strength + team2_strength)
        team2_probability = 1 - self_probability

        # Adjust probabilities of underdog based on luck (only if luck is > 0)
        if self_probability >= team2_probability:
            if team2.luck > 0:
                team2_probability = team2_probability + (team2.luck / 7)
                # Ensure probabilities are within [0, 1] range
                self_probability = 1 - team2_probability
        else:
            if(self.luck > 0):
               self.probability = self_probability + (self.luck / 7)
               # Ensure probabilities are within [0, 1] range
               team2_probability = 1 - self_probability
        
        #set calculated probabilities        
        self.probability = self_probability
        team2.probability = team2_probability

    
    def versusOLD(self, team2):
        print(self.name, "plays", team2.name)
        if(team2.adjEM <= 0):
            team2.adjEM = .25
        # Calculate strength for each team
        if(self.sos > 0):
            self_strength = self.adjEM + (math.sqrt(self.sos))
        else:
            self_strength = self.adjEM + (0 - (math.sqrt(abs(self.sos)))) 
        if(team2.sos > 0):
            team2_strength = team2.adjEM + (math.sqrt(team2.sos))
        else:
            team2_strength = team2.adjEM + (0 - (math.sqrt(abs(team2.sos))))

        # Calculate probability of winning based on relative strengths
        self_probability = self_strength / (self_strength + team2_strength)
        team2_probability = 1 - self_probability

        # Adjust probabilities based on luck
        if self_probability > team2_probability:
            if self.luck > 0:
                self_probability -= self.luck
                team2_probability += self.luck
        elif self_probability < team2_probability:
            if self.luck < 0:
                self_probability += abs(self.luck)
                team2_probability -= abs(self.luck)

        print(self.name+" stats are "+ "AdjEm "+ str(self.adjEM)+" sos "+str(self.sos)+" luck "+str(self.luck))
        print(team2.name+" stats are "+ "AdjEm "+ str(team2.adjEM)+" sos "+str(team2.sos)+" luck "+str(team2.luck))
        
        # Print probabilities
        print(self.name, "win probability:", self_probability)
        print(team2.name, "win probability:", team2_probability)