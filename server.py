from flask import Flask, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re

app = Flask(__name__)
CORS(app)

@app.route('/api/live-matches')
def get_live_matches():
    try:
        print("Начинаем парсинг...")
        
        # Вариант 1: Парсим flashscore (более надежно)
        url = "https://www.flashscore.com/football/"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.google.com/'
        }
        
        # Вариант А: Получаем реальные данные
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Статус код: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                matches = parse_flashscore(soup)
                
                if matches:
                    print(f"Найдено матчей: {len(matches)}")
                    return jsonify({
                        "success": True,
                        "matches": matches[:10],  # Ограничиваем 10 матчами
                        "count": len(matches),
                        "source": "flashscore.com"
                    })
        except Exception as e:
            print(f"Ошибка парсинга flashscore: {e}")
        
        # Вариант Б: Если парсинг не удался, используем демо-данные
        matches = generate_realistic_matches()
        print(f"Используем демо-данные: {len(matches)} матчей")
        
        return jsonify({
            "success": True,
            "matches": matches,
            "count": len(matches),
            "source": "demo",
            "note": "Используются демо-данные. Для реальных данных нужно настроить VPN на сервере."
        })
        
    except Exception as e:
        print(f"Общая ошибка: {e}")
        matches = generate_realistic_matches()
        return jsonify({
            "success": True,
            "matches": matches,
            "count": len(matches),
            "source": "demo_error"
        })

def parse_flashscore(soup):
    """Парсинг flashscore.com"""
    matches = []
    
    try:
        # Ищем контейнеры с матчами
        match_elements = soup.find_all('div', class_=re.compile(r'event__match'))
        
        for elem in match_elements[:15]:  # Ограничиваем 15 матчами
            try:
                # Названия команд
                home_team = elem.find('div', class_=re.compile(r'event__participant--home'))
                away_team = elem.find('div', class_=re.compile(r'event__participant--away'))
                
                if not home_team or not away_team:
                    continue
                    
                home = home_team.get_text(strip=True)
                away = away_team.get_text(strip=True)
                
                # Счет
                score_elem = elem.find('div', class_=re.compile(r'event__scores'))
                score = score_elem.get_text(strip=True) if score_elem else "0-0"
                
                # Минута
                minute_elem = elem.find('div', class_=re.compile(r'event__stage'))
                minute_text = minute_elem.get_text(strip=True) if minute_elem else "1'"
                
                # Извлекаем минуту из текста
                minute_match = re.search(r'(\d+)\'', minute_text)
                minute = int(minute_match.group(1)) if minute_match else 1
                
                # Генерируем данные по Пуассону
                poisson_data = calculate_poisson_probability({
                    'minute': minute,
                    'score': score
                })
                
                match_data = {
                    'id': f"{home}_{away}_{int(time.time())}",
                    'teams': f"{home} - {away}",
                    'teamHome': home,
                    'teamAway': away,
                    'score': score,
                    'minute': minute,
                    'status': minute_text,
                    'league': "Live Match",
                    'timestamp': datetime.now().strftime('%H:%M'),
                    'country': 'International',
                    'isLive': True,
                    **poisson_data
                }
                
                matches.append(match_data)
                
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"Ошибка при парсинге flashscore: {e}")
    
    return matches

def generate_realistic_matches():
    """Генерация реалистичных демо-матчей"""
    leagues = [
        ("Premier League", "England"),
        ("La Liga", "Spain"),
        ("Serie A", "Italy"),
        ("Bundesliga", "Germany"),
        ("Ligue 1", "France"),
        ("Champions League", "Europe"),
        ("Europa League", "Europe")
    ]
    
    teams = [
        ("Real Madrid", "Barcelona"),
        ("Manchester City", "Liverpool"),
        ("Bayern Munich", "Borussia Dortmund"),
        ("PSG", "Marseille"),
        ("Juventus", "Inter Milan"),
        ("Chelsea", "Arsenal"),
        ("Atletico Madrid", "Sevilla"),
        ("AC Milan", "Napoli")
    ]
    
    matches = []
    current_time = datetime.now()
    
    for i, ((home, away), (league, country)) in enumerate(zip(teams, leagues)):
        # Случайный счет
        home_goals = i % 3
        away_goals = (i + 1) % 3
        
        # Случайная минута
        minute = 15 + (i * 10)
        if minute > 90:
            minute = 45 + (i * 5) % 45
        
        score = f"{home_goals}-{away_goals}"
        
        # Рассчитываем вероятности
        poisson_data = calculate_poisson_probability({
            'minute': minute,
            'score': score,
            'league': league
        })
        
        matches.append({
            'id': f"demo_{i}_{int(time.time())}",
            'teams': f"{home} - {away}",
            'teamHome': home,
            'teamAway': away,
            'score': score,
            'minute': minute,
            'status': f"{minute}'",
            'league': league,
            'timestamp': current_time.strftime('%H:%M'),
            'country': country,
            'isLive': True,
            **poisson_data
        })
    
    return matches

def calculate_poisson_probability(match):
    """Расчет вероятностей по распределению Пуассона"""
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
    
    # Базовый лямбда в зависимости от лиги
    league = match.get('league', '').lower()
    if any(word in league for word in ['premier', 'champions', 'la liga', 'bundesliga']):
        base_lambda = 2.8
    else:
        base_lambda = 2.2
    
    # Рассчет лямбда
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
        "version": "2.0",
        "endpoints": [
            "/api/live-matches - Live matches with Poisson probabilities",
            "/api/test - Test endpoint"
        ],
        "note": "Если нет реальных матчей, используем реалистичные демо-данные"
    })

@app.route('/api/test')
def test():
    return jsonify({
        "status": "OK",
        "server_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "test_match": {
            "teams": "Test Home - Test Away",
            "score": "1-0",
            "minute": 30,
            "goalProbability": 65
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
