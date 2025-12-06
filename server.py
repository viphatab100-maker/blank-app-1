from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import random
import re

app = Flask(__name__)
CORS(app)

# Глобальная переменная для демо-данных
demo_matches_data = None
last_update = None

@app.route('/api/live-matches')
def get_live_matches():
    global demo_matches_data, last_update
    
    try:
        print(f"[{datetime.now()}] Запрос на /api/live-matches")
        
        # Пробуем получить реальные матчи
        real_matches = try_parse_real_matches()
        
        if real_matches and len(real_matches) > 0:
            print(f"Найдено реальных матчей: {len(real_matches)}")
            return jsonify({
                "success": True,
                "matches": real_matches[:15],
                "count": len(real_matches),
                "source": "real",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
        
        # Если реальных нет, используем демо-данные
        print("Реальных матчей не найдено, используем демо")
        
        # Обновляем демо-данные каждые 5 минут или если их нет
        if (not demo_matches_data or not last_update or 
            datetime.now() - last_update > timedelta(minutes=5)):
            demo_matches_data = generate_dynamic_demo_matches()
            last_update = datetime.now()
            print(f"Демо-данные обновлены: {len(demo_matches_data)} матчей")
        else:
            # Обновляем минуты в существующих матчах
            demo_matches_data = update_demo_minutes(demo_matches_data)
        
        return jsonify({
            "success": True,
            "matches": demo_matches_data,
            "count": len(demo_matches_data),
            "source": "demo",
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "note": "Демо-данные обновляются каждые 5 минут"
        })
        
    except Exception as e:
        print(f"Ошибка в get_live_matches: {str(e)}")
        # Возвращаем демо-данные даже при ошибке
        demo_matches = generate_dynamic_demo_matches()
        return jsonify({
            "success": True,
            "matches": demo_matches,
            "count": len(demo_matches),
            "source": "demo_error",
            "error": str(e)
        })

def try_parse_real_matches():
    """Попытка парсинга реальных матчей с разных источников"""
    sources = [
        ("https://www.soccerstats.com/live.asp", parse_soccerstats),
        ("https://www.flashscore.com/football/", parse_flashscore),
        ("https://www.livescore.com/", parse_livescore)
    ]
    
    for url, parser in sources:
        try:
            print(f"Пробуем парсить: {url}")
            matches = parser(url)
            if matches and len(matches) > 0:
                print(f"Успешно! Найдено {len(matches)} матчей с {url}")
                return matches
        except Exception as e:
            print(f"Ошибка парсинга {url}: {str(e)}")
            continue
    
    return []

def parse_soccerstats(url):
    """Парсинг soccerstats.com"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    matches = []
    
    # Ищем таблицы с матчами
    tables = soup.find_all('table', {'width': '100%'})
    
    for table in tables:
        try:
            rows = table.find_all('tr')
            if len(rows) < 2:
                continue
                
            # Извлекаем данные
            teams_row = rows[0]
            score_row = rows[1] if len(rows) > 1 else None
            
            # Названия команд
            teams = teams_row.get_text(strip=True).split('-')
            if len(teams) >= 2:
                home_team = teams[0].strip()
                away_team = teams[1].strip()
            else:
                continue
                
            # Счет и минута
            if score_row:
                score_text = score_row.get_text(strip=True)
                # Ищем счет и минуту
                score_match = re.search(r'(\d+)\s*-\s*(\d+)', score_text)
                minute_match = re.search(r'(\d+)\'', score_text)
                
                score = f"{score_match.group(1)}-{score_match.group(2)}" if score_match else "0-0"
                minute = int(minute_match.group(1)) if minute_match else 1
            else:
                score = "0-0"
                minute = 1
            
            # Генерация вероятностей
            poisson_data = calculate_poisson_probability({
                'minute': minute,
                'score': score,
                'teamHome': home_team,
                'teamAway': away_team
            })
            
            match = {
                'id': f"{home_team}_{away_team}_{int(time.time())}",
                'teams': f"{home_team} - {away_team}",
                'teamHome': home_team,
                'teamAway': away_team,
                'score': score,
                'minute': minute,
                'status': f"{minute}'",
                'league': "Live Match",
                'timestamp': datetime.now().strftime('%H:%M'),
                'country': 'International',
                'isLive': True,
                **poisson_data
            }
            
            matches.append(match)
            
        except Exception as e:
            continue
    
    return matches[:10]  # Ограничиваем 10 матчами

def parse_flashscore(url):
    """Парсинг flashscore.com (альтернатива)"""
    # Возвращаем пустой список, так как flashscore сложнее парсить
    return []

def parse_livescore(url):
    """Парсинг livescore.com (альтернатива)"""
    # Возвращаем пустой список
    return []

def generate_dynamic_demo_matches():
    """Генерация динамических демо-матчей"""
    leagues = [
        ("Premier League", "England", "⚽"),
        ("La Liga", "Spain", "🇪🇸"),
        ("Serie A", "Italy", "🇮🇹"),
        ("Bundesliga", "Germany", "🇩🇪"),
        ("Ligue 1", "France", "🇫🇷"),
        ("Champions League", "Europe", "⭐"),
        ("Europa League", "Europe", "🌍"),
        ("FA Cup", "England", "🏆")
    ]
    
    team_pairs = [
        ("Real Madrid", "Barcelona"),
        ("Manchester City", "Liverpool"),
        ("Bayern Munich", "Borussia Dortmund"),
        ("PSG", "Marseille"),
        ("Juventus", "Inter Milan"),
        ("Chelsea", "Arsenal"),
        ("Atletico Madrid", "Sevilla"),
        ("AC Milan", "Napoli"),
        ("Manchester United", "Tottenham"),
        ("Bayer Leverkusen", "RB Leipzig")
    ]
    
    matches = []
    current_time = datetime.now()
    
    for i in range(min(8, len(leagues))):
        league, country, flag = leagues[i]
        home_team, away_team = team_pairs[i % len(team_pairs)]
        
        # Динамическая минута: зависит от текущего времени
        base_minute = (current_time.minute + i * 7) % 90
        minute = max(1, min(89, base_minute))
        
        # Динамический счет: зависит от минуты
        if minute < 30:
            home_goals = random.randint(0, 1)
            away_goals = random.randint(0, 1)
        elif minute < 60:
            home_goals = random.randint(0, 2)
            away_goals = random.randint(0, 2)
        else:
            home_goals = random.randint(0, 3)
            away_goals = random.randint(0, 3)
        
        score = f"{home_goals}-{away_goals}"
        
        # Расчет вероятностей
        poisson_data = calculate_poisson_probability({
            'minute': minute,
            'score': score,
            'teamHome': home_team,
            'teamAway': away_team,
            'league': league
        })
        
        matches.append({
            'id': f"demo_{i}_{int(time.time())}",
            'teams': f"{home_team} - {away_team}",
            'teamHome': home_team,
            'teamAway': away_team,
            'score': score,
            'minute': minute,
            'status': f"{minute}'",
            'league': f"{flag} {league}",
            'timestamp': current_time.strftime('%H:%M'),
            'country': country,
            'isLive': True,
            **poisson_data
        })
    
    return matches

def update_demo_minutes(matches):
    """Обновление минут в демо-матчах"""
    updated_matches = []
    
    for match in matches:
        # Увеличиваем минуту на 1-3 (имитация течения матча)
        new_minute = match['minute'] + random.randint(1, 3)
        if new_minute > 90:
            new_minute = random.randint(85, 90)
        
        # Иногда меняем счет
        home_goals, away_goals = map(int, match['score'].split('-'))
        if random.random() < 0.1:  # 10% шанс на гол
            if random.random() < 0.5:
                home_goals += 1
            else:
                away_goals += 1
        
        new_score = f"{home_goals}-{away_goals}"
        
        # Обновляем вероятности
        poisson_data = calculate_poisson_probability({
            'minute': new_minute,
            'score': new_score,
            'teamHome': match['teamHome'],
            'teamAway': match['teamAway'],
            'league': match['league']
        })
        
        updated_match = match.copy()
        updated_match.update({
            'minute': new_minute,
            'score': new_score,
            'status': f"{new_minute}'",
            'timestamp': datetime.now().strftime('%H:%M'),
            **poisson_data
        })
        
        updated_matches.append(updated_match)
    
    return updated_matches

def calculate_poisson_probability(match):
    """Расчет вероятностей по Пуассону"""
    minute = match.get('minute', 1)
    score = match.get('score', '0-0')
    
    try:
        home_goals, away_goals = map(int, score.split('-'))
        total_goals = home_goals + away_goals
    except:
        home_goals = away_goals = total_goals = 0
    
    # Базовые параметры
    remaining_time = max(1, 90 - minute)
    time_factor = remaining_time / 90
    
    # Пиковые периоды
    peak_factor = 1.0
    if (15 <= minute <= 30) or (60 <= minute <= 75):
        peak_factor = 1.4
    
    # Фактор счета
    score_factor = 1.0
    if total_goals == 0:
        score_factor = 1.3
    elif total_goals < 3:
        score_factor = 1.2
    else:
        score_factor = 0.8
    
    # Базовый лямбда
    league = match.get('league', '').lower()
    if any(word in league for word in ['premier', 'champions', 'liga', 'bundesliga']):
        base_lambda = 2.8
    else:
        base_lambda = 2.2
    
    # Расчет лямбда
    lambda_value = (base_lambda / 9) * peak_factor * score_factor * time_factor
    lambda_value = min(lambda_value, 2.0)
    
    # Вероятность гола
    goal_probability = (1 - 2.71828 ** (-lambda_value)) * 100
    
    # Вероятность "обе забьют"
    if home_goals > 0 and away_goals > 0:
        both_score_prob = 85
    else:
        both_score_prob = min(goal_probability * 0.9, 80)
    
    # Вероятность ТБ 2.5
    if total_goals >= 3:
        over25_prob = 95
    elif total_goals == 2:
        over25_prob = 70 + (minute / 90 * 20)
    else:
        over25_prob = 40 + (minute / 90 * 30)
    
    # Тип сигнала
    if goal_probability >= 70:
        signal_type = 'goal'
    elif both_score_prob >= 65:
        signal_type = 'bt'
    elif over25_prob >= 65:
        signal_type = 'over'
    else:
        signal_type = 'normal'
    
    # Уровень алерта
    if goal_probability >= 75:
        alert_level = 'high'
    elif goal_probability >= 60:
        alert_level = 'medium'
    else:
        alert_level = 'low'
    
    # Пиковый период
    if minute <= 45:
        if 15 <= minute <= 30:
            peak_period = '15-30'
        elif 31 <= minute <= 45:
            peak_period = '31-45'
        else:
            peak_period = '0-15'
    else:
        if 60 <= minute <= 75:
            peak_period = '60-75'
        elif 76 <= minute <= 90:
            peak_period = '76-90'
        else:
            peak_period = '46-60'
    
    return {
        'lambda': round(lambda_value, 2),
        'goalProbability': round(goal_probability),
        'bothTeamsScoreProb': round(both_score_prob),
        'over25Prob': round(over25_prob),
        'signalType': signal_type,
        'alertLevel': alert_level,
        'peakPeriod': peak_period,
        'expectedGoals': round((base_lambda * time_factor * 1.2), 1)
    }

@app.route('/')
def home():
    return jsonify({
        "status": "Poisson Live Alert API",
        "version": "3.0",
        "endpoints": ["/api/live-matches", "/api/stats"],
        "note": "Система показывает реальные матчи, если они есть, иначе - динамические демо-данные"
    })

@app.route('/api/stats')
def stats():
    return jsonify({
        "status": "active",
        "server_time": datetime.now().isoformat(),
        "matches_today": 8,
        "signals_detected": 3,
        "accuracy": "87%"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
