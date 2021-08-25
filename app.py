from flask import Flask, request
import sys, json, subprocess, functools, operator, time, asyncio, os, sqlite3
from pprint import pprint
from datetime import datetime, timezone
from string import Template

from debugger import initialize_flask_server_debugger_if_needed
initialize_flask_server_debugger_if_needed()

sys.path.insert(1, '/app/ddd')

from ddd.data import Data
from ddd.phab import Conduit
from ddd.data import PropertyMatcher
# from ddd.boardmetrics import ObjectMetrics

def fetchProjectName(cursor):
    return dict(cursor.execute('select * from columns').fetchone())['project_name']

def fetchColumns(cursor):
    rows = cursor.execute('select * from columns').fetchall()
    return dict((row['column_phid'], row['column_name']) for row in rows)

def fetchTaskTimeInColumns(cursor, taskID):
    rows = cursor.execute('select * from task_metrics where task = ? and metric like "PHID-PCOL-%" order by ts', [taskID]).fetchall()
    def durationOrDurationSinceNow(row):
        return row['duration'] if row['next_metric'] else int(time.time() - row['ts']) # / (60 * 60 * 24)
    return dict((row['metric'], durationOrDurationSinceNow(row)) for row in rows)

def fetchTaskCompletionTime(cursor, taskID):
    return dict(cursor.execute('select sum(duration) as duration from task_metrics where task = ?', [taskID]).fetchone())['duration']

# def fetchAllTaskIDs(cursor):
#     rows = cursor.execute('select distinct task from task_metrics order by CAST(task AS int)').fetchall()
#     return list(map(lambda row: row['task'], rows))

app = Flask(__name__)

# http://127.0.0.1:5000/?taskID=275701
phab = Conduit(phab_url = os.getenv('CONDUIT_URL'), token = os.getenv('CONDUIT_TOKEN'))

def stringFromFile(fileName):
    with open(fileName, 'r') as f:
        return f.read()
    return None

def getGraphingTemplateHTML(fileName, addGraphsJS):
    return Template(stringFromFile(fileName)).substitute(
        ADD_GRAPHS_JS = addGraphsJS
    )

def htmlToShowGraphsForProjects(jsToAddGraphsForProjects):
    return getGraphingTemplateHTML('template-bargraph.html', jsToAddGraphsForProjects)

async def start():
    connection = sqlite3.connect('metrics.db')
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor() 
    
    taskID = request.args.get('taskID')
    taskTimeInColumns = fetchTaskTimeInColumns(cursor, taskID)
    columns = fetchColumns(cursor)
    projectName = fetchProjectName(cursor)
    taskCompletionTime = fetchTaskCompletionTime(cursor, taskID)
    # allTaskIDs = fetchAllTaskIDs(cursor)

    cursor.close()
    connection.close()

    timesInColumsGraphJS = ''
    if len(taskTimeInColumns) > 0:
        timesInColumsGraphJS = f'''
            addGraph(
                {json.dumps([columns[columnID] for columnID in columns.keys()])},
                {json.dumps([round(taskTimeInColumns[columnID] / (60 * 60 * 24), 1) if columnID in taskTimeInColumns else 0 for columnID in columns.keys()])},
                {[]},
                '<b>Task Time in Columns</b><br>T{taskID} on <i>{projectName}</i>',
                'Column',
                'Days in column',
                metric => `${{metric}} days`
            )
        '''
    return htmlToShowGraphsForProjects(timesInColumsGraphJS)

@app.route('/')
async def main():
    return await start()
