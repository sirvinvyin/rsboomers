import json
import requests
from bs4 import BeautifulSoup

def refresh_ca_task_data(url):
    response = requests.get(url)
    col = ca_db["tasks"]
    force_list = [448, 445, 443, 434, 437]
    team_boss_list = ['Theatre of Blood', 'Theatre of Blood: Hard Mode']
    group_list = ['duo', 'trio', 'Trio', '4-man', '5-scale', '4-scale', 'group of 8', 'group of 2 or more', 'group of two or more', 'group size of at least 2']
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'lxml')
        tasks = soup.find_all('tr', {'data-ca-task-id': True})
        task_data = []
        for task in tasks:
            task_id = int(task['data-ca-task-id'])
            is_team_task = 0
            boss_name = task.find('a').text.strip()
            task_name = task.find_all('td')[1].text.strip()
            task_description = task.find_all('td')[2].text.strip()
            task_type = task.find_all('td')[3].text.strip()
            if ((boss_name in team_boss_list) or (task_description in group_list) or (task_id in force_list)) and (task_type != 'Kill Count'):
                is_team_task = 1
            entry = {
                'boss_name': boss_name,
                'task_name': task_name,
                'task_type': task_type,
                'task_description': task_description,
                'is_team_task': is_team_task
            }
            col.replace_one({'_id': task_id}, entry, upsert=True)
