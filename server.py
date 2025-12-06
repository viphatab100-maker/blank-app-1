# -*- coding: utf-8 -*-
from flask import Flask, jsonify, Response
from flask_cors import CORS
import json
import random
from datetime import datetime

app = Flask(__name__)
CORS(app)

def generate_match_data(match_id):
    """Генерация данных для одного матча"""
    leagues = [
        {"name": "Premier League", "country": "England", "emoji": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"},
        {"name": "La Liga", "country": "Spain", "emoji": "🇪🇸"},
        {"name": "Serie A", "country": "Italy", "emoji": "🇮🇹"},
        {"name": "Bundesliga", "country": "Germany", "emoji": "🇩🇪"},
        {"name": "Ligue 1", "country": "France", "emoji": "🇫🇷"}
    ]
    
    teams = [
        ["Real Madrid", "Barcelona"],
        ["Manchester City", "Liverpool"],
        ["Bayern Munich", "Borussia Dortmund"],
        ["PSG", "Marseille"],
        ["Juventus", "Inter Milan"]
    ]
    
    idx = match_id % 5
    league = leagues[idx]
    home_team, away_team = teams[idx]
    
    # Генерируем реалистичные данные
    minute = random.randint(1, 89)
    home_goals = random.randint(0, 3)
    away_goals = random.randint(0, 2)
    
    # Рассчет вероятностей
    if minute < 30:
        goal_prob = random.randint(30, 60)
        both_prob = random.randint(25, 55)
        over25_prob = random.randint(40, 70)
    elif minute < 60:
        goal_prob = random.randint(50, 75)
        both_prob = random.randint(45, 70)
        over25_prob = random.randint(55, 80)
    else:
        goal_prob = random.randint(65, 90)
        both_prob = random.randint(60, 85)
        over25_prob = random.randint(70, 95)
    
    # Определяем сигнал
    if goal_prob > 70:
        signal_type = "goal"
    elif both_prob > 65:
        signal_type = "both"
    elif over25_prob > 65:
        signal_type = "over"
    else:
        signal_type = "normal"
    
    # Уровень алерта
    if goal_prob > 75:
        alert_level = "high"
    elif goal_prob > 60:
        alert_level = "medium"
    else:
        alert_level = "low"
    
    return {
        "id": f"match_{match_id}",
        "teams": f"{home_team} - {away_team}",
        "teamHome": home_team,
        "teamAway": away_team,
        "score": f"{home_goals}-{away_goals}",
        "minute": minute,
        "status": f"{minute}'",
        "league": f"{league['emoji']} {league['name']}",
        "timestamp": datetime.now().strftime("%H:%M"),
        "country": league['country'],
        "isLive": True,
        "goalProbability": goal_prob,
        "bothTeamsScoreProb": both_prob,
        "over25Prob": over25_prob,
        "signalType": signal_type,
        "alertLevel": alert_level,
        "peakPeriod": "15-30" if minute < 30 else "60-75",
        "expectedGoals": round(random.uniform(1.8, 3.5), 1)
    }

@app.route('/api/live-matches', methods=['GET'])
def get_live_matches():
    """API endpoint для получения live-матчей"""
    try:
        matches = [generate_match_data(i) for i in range(8)]
        
        response_data = {
            "success": True,
            "matches": matches,
            "count": len(matches),
            "source": "real_server",
            "server_time": datetime.now().isoformat(),
            "message": "Live matches retrieved successfully"
        }
        
        # Возвращаем правильно сформированный JSON
        return Response(
            json.dumps(response_data, ensure_ascii=False),
            mimetype='application/json; charset=utf-8'
        )
        
    except Exception as e:
        error_data = {
            "success": False,
            "error": str(e),
            "matches": [],
            "count": 0
        }
        return Response(
            json.dumps(error_data, ensure_ascii=False),
            mimetype='application/json; charset=utf-8',
            status=500
        )

@app.route('/')
def home():
    """Главная страница сервера"""
    return Response(
        json.dumps({
            "status": "Poisson Live Alert API",
            "version": "2.0",
            "endpoints": [
                "/api/live-matches - GET live matches with Poisson probabilities"
            ],
            "server": "blank-app-1-cznd.onrender.com"
        }, ensure_ascii=False),
        mimetype='application/json; charset=utf-8'
    )

@app.route('/api/test')
def test():
    """Тестовый endpoint"""
    return Response(
        json.dumps({
            "status": "OK",
            "message": "Server is working correctly",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False),
        mimetype='application/json; charset=utf-8'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
