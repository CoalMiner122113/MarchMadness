import math
import random

def simulate_game(team1, team2, roundNum):
    team1.versus(team2, roundNum)
    fact = random.random()
    if(team1.probability > team2.probability):
        if(fact < team1.probability):
            winner = team1
            loser = team2
        else:
            winner = team2
            loser = team1
    else:
        if(fact < team2.probability):
            winner = team2
            loser = team1
        else:
            winner = team1
            loser = team2
    return [winner, loser, fact]

def round64(east, west, south, midwest):
    results = {
        'east': [],
        'west': [],
        'south': [],
        'midwest': []
    }
    winners = {
        'east': [],
        'west': [],
        'south': [],
        'midwest': []
    }
    
    brackets = [east, west, south, midwest]
    division_names = ['east', 'west', 'south', 'midwest']
    
    for div_idx, bracket in enumerate(brackets):
        div_name = division_names[div_idx]
        for i in range(8):
            team1 = bracket[i*2]
            team2 = bracket[i*2+1]
            game_result = simulate_game(team1, team2, 1)
            results[div_name].append(game_result)
            winners[div_name].append(game_result[0])
    
    return results, [winners['east'], winners['west'], winners['south'], winners['midwest']]

def round32(east, west, south, midwest):
    results = {
        'east': [],
        'west': [],
        'south': [],
        'midwest': []
    }
    winners = {
        'east': [],
        'west': [],
        'south': [],
        'midwest': []
    }
    
    brackets = [east, west, south, midwest]
    division_names = ['east', 'west', 'south', 'midwest']
    
    for div_idx, bracket in enumerate(brackets):
        div_name = division_names[div_idx]
        for i in range(4):
            team1 = bracket[i*2]
            team2 = bracket[i*2+1]
            game_result = simulate_game(team1, team2, 2)
            results[div_name].append(game_result)
            winners[div_name].append(game_result[0])
    
    return results, [winners['east'], winners['west'], winners['south'], winners['midwest']]

def sweet16(east, west, south, midwest):
    results = {
        'east': [],
        'west': [],
        'south': [],
        'midwest': []
    }
    winners = {
        'east': [],
        'west': [],
        'south': [],
        'midwest': []
    }
    
    brackets = [east, west, south, midwest]
    division_names = ['east', 'west', 'south', 'midwest']
    
    for div_idx, bracket in enumerate(brackets):
        div_name = division_names[div_idx]
        for i in range(2):
            team1 = bracket[i*2]
            team2 = bracket[i*2+1]
            game_result = simulate_game(team1, team2, 3)
            results[div_name].append(game_result)
            winners[div_name].append(game_result[0])
    
    return results, [winners['east'], winners['west'], winners['south'], winners['midwest']]

def elite8(east, west, south, midwest):
    results = {
        'east': [],
        'west': [],
        'south': [],
        'midwest': []
    }
    winners = {
        'east': [],
        'west': [],
        'south': [],
        'midwest': []
    }
    
    brackets = [east, west, south, midwest]
    division_names = ['east', 'west', 'south', 'midwest']
    
    for div_idx, bracket in enumerate(brackets):
        div_name = division_names[div_idx]
        team1 = bracket[0]
        team2 = bracket[1]
        game_result = simulate_game(team1, team2, 4)
        results[div_name].append(game_result)
        winners[div_name].append(game_result[0])
    
    return results, [winners['east'], winners['west'], winners['south'], winners['midwest']]

def final4(east_winner, west_winner, south_winner, midwest_winner):
    results = []
    
    # First semifinal: East vs West
    game1_result = simulate_game(east_winner[0], west_winner[0], 5)
    results.append(game1_result)
    
    # Second semifinal: South vs Midwest
    game2_result = simulate_game(south_winner[0], midwest_winner[0], 5)
    results.append(game2_result)
    
    return results, [[game1_result[0]], [game2_result[0]]]

def championship(semifinal1_winner, semifinal2_winner):
    game_result = simulate_game(semifinal1_winner[0], semifinal2_winner[0], 6)
    return [game_result], [[game_result[0]]]

def tourney(roundA, roundB, roundC, roundD):
    # Round of 64
    r64_results, r64_winners = round64(roundA, roundB, roundC, roundD)
    
    # Round of 32
    r32_results, r32_winners = round32(r64_winners[0], r64_winners[1], r64_winners[2], r64_winners[3])
    
    # Sweet 16
    s16_results, s16_winners = sweet16(r32_winners[0], r32_winners[1], r32_winners[2], r32_winners[3])
    
    # Elite 8
    e8_results, e8_winners = elite8(s16_winners[0], s16_winners[1], s16_winners[2], s16_winners[3])
    
    # Final 4
    f4_results, f4_winners = final4(e8_winners[0], e8_winners[1], e8_winners[2], e8_winners[3])
    
    # Championship
    champ_results, champ_winner = championship(f4_winners[0], f4_winners[1])
    
    return {
        'round64': r64_results,
        'round32': r32_results,
        'sweet16': s16_results,
        'elite8': e8_results,
        'final4': f4_results,
        'championship': champ_results,
        'champion': champ_winner[0][0]
    }

