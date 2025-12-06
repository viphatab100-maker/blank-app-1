# server.py - Код для бесплатного сервера
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import time

app = Flask(__name__)
CORS(app)  # Разрешаем запросы от вашего смартфона

# Ключи для разных страниц soccerstats
PAGES = {
    'live': 'https://www.soccerstats.com/live.asp',
    'matches': 'https://www.soccerstats.com/matches.asp',
    'latest': 'https://www.soccerstats.com/latest.asp',
    'results': 'https://www.soccerstats.com/results.asp'
}

def parse_soccerstats_live():
    """Парсинг live-матчей с soccerstats.com"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Получаем HTML страницы
        response = requests.get(PAGES['live'], headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            return {"error": f"Ошибка {response.status_code}", "matches": []}
        
        # Парсинг HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        matches = []
        
        # Ищем все таблицы с матчами
        tables = soup.find_all('table', {'width': '100%'})
        
        for table in tables:
            # Проверяем, что это таблица с матчем (имеет определенную структуру)
            rows = table.find_all('tr')
            if len(rows) < 3:
                continue
                
            try:
                # Извлекаем данные матча
                cells = rows[0].find_all('td')
                if len(cells) >= 4:
                    # Названия команд
                    team_cells = rows[0].find_all('td', {'class': 'odd'})
                    if len(team_cells) >= 2:
                        team_home = team_cells[0].get_text(strip=True)
                        team_away = team_cells[1].get_text(strip=True)
                    else:
                        continue
                    
                    # Счет и минута
                    score_cell = rows[1].find('td')
                    minute_cell = rows[1].find_all('td')[1] if len(rows[1].find_all('td')) > 1 else None
                    
                    if not score_cell or not minute_cell:
                        continue
                    
                    score = score_cell.get_text(strip=True)
                    minute_text = minute_cell.get_text(strip=True)
                    
                    # Извлекаем минуту
                    minute_match = re.search(r'(\d+)\'', minute_text)
                    minute = int(minute_match.group(1)) if minute_match else 0
                    
                    # Определяем лигу
                    league_row = table.find_previous('tr', {'class': 'trow2'})
                    league = league_row.get_text(strip=True) if league_row else "Live Match"
                    
                    # Создаем объект матча
                    match = {
                        'id': f"{team_home}_{team_away}_{datetime.now().timestamp()}",
                        'teams': f"{team_home} - {team_away}",
                        'teamHome': team_home,
                        'teamAway': team_away,
                        'score': score,
                        'minute': minute,
                        'status': minute_text,
                        'league': league[:50],  # Ограничиваем длину
                        'timestamp': datetime.now().strftime('%H:%M'),
                        'country': 'International',
                        'isLive': True
                    }
                    
                    matches.append(match)
                    
            except Exception as e:
                print(f"Ошибка парсинга строки: {e}")
                continue
        
        # Если матчей не найдено, используем альтернативный метод парсинга
        if not matches:
            matches = parse_alternative_method(soup)
        
        return {"success": True, "matches": matches, "count": len(matches)}
        
    except Exception as e:
        print(f"Ошибка парсинга: {str(e)}")
        return {"error": str(e), "matches": []}

def parse_alternative_method(soup):
    """Альтернативный метод парсинга"""
    matches = []
    
    # Ищем таблицы с классом t3
    tables = soup.find_all('table', class_='t3')
    
    for table in tables:
        try:
            # Ищем строки с матчами
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 5:
                    team_home = cells[0].get_text(strip=True)
                    team_away = cells[1].get_text(strip=True)
                    score = cells[2].get_text(strip=True)
                    minute_text = cells[3].get_text(strip=True)
                    
                    if team_home and team_away and minute_text and "'" in minute_text:
                        minute_match = re.search(r'(\d+)\'', minute_text)
                        minute = int(minute_match.group(1)) if minute_match else 0
                        
                        # Определяем лигу
                        prev_elem = table.find_previous('h2')
                        league = prev_elem.get_text(strip=True) if prev_elem else "Live Match"
                        
                        matches.append({
                            'id': f"{team_home}_{team_away}_{datetime.now().timestamp()}",
                            'teams': f"{team_home} - {team_away}",
                            'teamHome': team_home,
                            'teamAway': team_away,
                            'score': score,
                            'minute': minute,
                            'status': minute_text,
                            'league': league[:50],
                            'timestamp': datetime.now().strftime('%H:%M'),
                            'country': 'International',
                            'isLive': True
                        })
                        
        except Exception as e:
            continue
    
    return matches

def calculate_poisson_probability(match):
    """Расчет вероятности по модели Пуассона"""
    minute = match['minute']
    score = match['score']
    
    # Парсим счет
    try:
        home_goals, away_goals = map(int, score.split('-'))
        total_goals = home_goals + away_goals
    except:
        home_goals = away_goals = total_goals = 0
    
    # Базовые параметры
    remaining_time = 90 - minute
    time_factor = remaining_time / 90
    
    # Пиковые периоды
    peak_factor = 1.0
    if (15 <= minute <= 30) or (60 <= minute <= 75):
        peak_factor = 1.4
    
    # Учитываем текущий счет
    score_factor = 1.0
    if total_goals == 0:
        score_factor = 1.3  # Ожидание первого гола
    elif total_goals < 3:
        score_factor = 1.2  # Матч еще не решился
    else:
        score_factor = 0.8  # Уже много голов
    
    # Базовая лямбда для топ-лиг
    if any(league in match['league'] for league in ['Premier', 'La Liga', 'Bundesliga', 'Serie A']):
        base_lambda = 2.8
    else:
        base_lambda = 2.2
    
    # Рассчитываем лямбду для следующих 10 минут
    lambda_value = (base_lambda / 9) * peak_factor * score_factor * time_factor
    lambda_value = min(lambda_value, 2.0)
    
    # Вероятность хотя бы одного гола
    goal_probability = (1 - 2.71828 ** (-lambda_value)) * 100
    
    # Вероятность "Обе забьют"
    if home_goals > 0 and away_goals > 0:
        both_score_prob = 85
    else:
        both_score_prob = min(goal_probability * 0.9, 80)
    
    # Вероятность тотала больше 2.5
    if total_goals >= 3:
        over25_prob = 95
    elif total_goals == 2:
        over25_prob = 70 + (minute / 90 * 20)
    else:
        over25_prob = 40 + (minute / 90 * 30)
    
    # Определяем тип сигнала
    if goal_probability >= 70:
        signal_type = 'goal'
    elif both_score_prob >= 65:
        signal_type = 'bt'
    elif over25_prob >= 65:
        signal_type = 'over'
    else:
        signal_type = 'normal'
    
    # Уровень сигнала
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
        'expectedGoals': round((base_lambda * time_factor * 1.2), 1),
        'poissonFormula': f"λ={round(lambda_value, 2)}"
    }

@app.route('/')
def home():
    return jsonify({"status": "Poisson Live Alert Server", "version": "1.0"})

@app.route('/api/live-matches')
def get_live_matches():
    """API для получения live-матчей"""
    result = parse_soccerstats_live()
    
    # Добавляем расчет Пуассона
    for match in result.get('matches', []):
        poisson_data = calculate_poisson_probability(match)
        match.update(poisson_data)
    
    return jsonify(result)

@app.route('/api/test')
def test():
    """Тестовый endpoint"""
    return jsonify({
        "status": "OK",
        "server_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "endpoints": ["/api/live-matches", "/api/test"]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
