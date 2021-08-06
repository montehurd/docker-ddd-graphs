from flask import Flask, request
import sys, json, subprocess, functools, operator, time, asyncio, os
from pprint import pprint
from datetime import datetime, timezone
from string import Template

from debugger import initialize_flask_server_debugger_if_needed
initialize_flask_server_debugger_if_needed()


sys.path.insert(1, '/app/ddd')

from ddd.data import Data
from ddd.phab import Conduit

from ddd.boardmetrics import ObjectMetrics
from ddd.data import PropertyMatcher


app = Flask(__name__)


# http://localhost:8381/?projectNames=iOS-app-Bugs
# phab = Conduit(phab_url = 'https://phabricator.wikimedia.org/api/', token = '')

# http://localhost:8381/?projectNames=Test-Project
# http://localhost:8381/?projectPHIDs=PHID-PROJ-egwedyhdplvmss4qfzv4,PHID-PROJ-htdrulsasg7rxvnfvp5g
# phab = Conduit(phab_url = 'http://docker-phabricator_phabricator_1:80/api/', token = 'api-pkzahk74gg7tpnltwmhhok5xwt4i')
phab = Conduit(phab_url = os.getenv('CONDUIT_URL'), token = os.getenv('CONDUIT_TOKEN'))

def localTimezoneDateStringFromTimeStamp(ts):
    local_now = datetime.now().astimezone()
    local_tz = local_now.tzinfo
    return datetime.fromtimestamp(ts, tz=local_tz).strftime('%x, %r')

def getProjectForProjectTitle(title):
    projectMatches = phab.request('project.search', {
        'constraints': {
            'name' : title
        }
    })
    if len(projectMatches.data) < 1:
        print(f'No projects found with title "{title}"')
        return None
    return projectMatches.data[0]

def getProjectsForProjectPHIDs(phids):
    projectMatches = phab.request('project.search', {
        'constraints': {
            'phids': phids
        }
    })
    if len(projectMatches.data) < 1:
        print(f'No projects found with phids "{phids}"')
        return None
    return projectMatches.data

nonOpenTicketStatuses = [
    'closed',
    'resolved',
    'stalled',
    'declined',
    'invalid'
]

def fetchTransactionsForTaskPHID(taskPHID):
    print(f'\tfetching ticket transactions for {taskPHID}')
    transactions = phab.request('transaction.search', {
        'objectIdentifier': taskPHID
    })
    transactions.fetch_all()
    print("============================")
    print(list(transactions.data))
    print("============================")
    return list(transactions.data)

def fetchTicketsWithProject(projectPHID):
    print(f'\nfetching project tickets')
    tickets = phab.request('maniphest.search', {
        'constraints': {
            'projects': [projectPHID]
        }
    })
    tickets.fetch_all()
    return list(tickets.data)

def isTransactionOfType(transaction, typeName):
    return transaction['type'] == typeName

def transactionHasOperations(transaction):
    return 'operations' in transaction['fields']

def dictionaryKeyValueIntersection(dict1, dict2):
    return {key: dict1[key] for key in dict1 if key in dict2 and dict2[key] == dict1[key]}

def isDictionaryInDictionary(dict1, dict2):
    return dictionaryKeyValueIntersection(dict1, dict2) == dict1

def transactionHasOperationWithKeysAndValues(transaction, keysAndValues):
    if not transactionHasOperations(transaction):
        return False
    operationWithKeysAndValues = next((operation for operation in transaction['fields']['operations'] if isDictionaryInDictionary(keysAndValues, operation)), None)
    return operationWithKeysAndValues != None

def isTicketProjectTransaction(transaction, projectPHID):
    return isTransactionOfType(transaction, 'projects') and (
            transactionHasOperationWithKeysAndValues(transaction, {
                'operation': 'add',
                'phid': projectPHID
            })
            or
            transactionHasOperationWithKeysAndValues(transaction, {
                'operation': 'remove',
                'phid': projectPHID
            })
        )

def isTicketCloseStatusTransaction(transaction):
    return isTransactionOfType(transaction, 'status') and next((True for status in nonOpenTicketStatuses if 'fields' in transaction and isDictionaryInDictionary({'new': status}, transaction['fields'])), False)

def fetchAddedOrRemovedTransactions(taskPHID, projectPHID):
    transactions = fetchTransactionsForTaskPHID(taskPHID)
    return list(filter(lambda transaction:
        isTicketCloseStatusTransaction(transaction)
        or
        isTicketProjectTransaction(transaction, projectPHID)
    , transactions))

def ticketFirstTimeAddedToProject(transactions, projectPHID):
    return next((transaction['dateModified'] for transaction in reversed(transactions) if transaction['type'] == 'projects' and transactionHasOperationWithKeysAndValues(transaction, {'operation': 'add', 'phid': projectPHID})), None)

def ticketLastTimeRemovedFromProject(transactions, projectPHID):
    return next((transaction['dateModified'] for transaction in transactions if transaction['type'] == 'projects' and transactionHasOperationWithKeysAndValues(transaction, {'operation': 'remove', 'phid': projectPHID})), None)

def ticketLastTimeStatusClosed(transactions):
    return next((transaction['dateModified'] for transaction in transactions if transaction['type'] == 'status' and transaction['fields']['new'] in nonOpenTicketStatuses), None)

def ticketDaysInProject(ticket, projectPHID):
    ticketPHID = ticket['phid']
    transactions = fetchAddedOrRemovedTransactions(ticketPHID, projectPHID)
    dateEnteredProject = ticketFirstTimeAddedToProject(transactions, projectPHID)
    dateExitedProject = min(ticketLastTimeRemovedFromProject(transactions, projectPHID), ticketLastTimeStatusClosed(transactions)) if ticketLastTimeRemovedFromProject(transactions, projectPHID) != None and ticketLastTimeStatusClosed(transactions) != None else ticketLastTimeRemovedFromProject(transactions, projectPHID) if ticketLastTimeStatusClosed(transactions) == None else ticketLastTimeStatusClosed(transactions)

    if dateEnteredProject == None and not dateExitedProject == None:
        dateEnteredProject = ticket['dateCreated']

    if dateExitedProject == None or dateEnteredProject == None:
        print(f'\tNone type detected for ticket entry or exit project dates: {ticketPHID}. entry: {dateEnteredProject} exit: {dateExitedProject}')

    durationInProject = dateExitedProject - dateEnteredProject if dateExitedProject != None and dateEnteredProject != None else -1

    return round(durationInProject / (60 * 60 * 24), 1)

def sendToBrowser(string, extension):
    filePath = f'/tmp/browser.tmp.{extension}'
    f = open(filePath, 'wt', encoding='utf-8')
    f.write(string)
    # subprocess.run(f'open -a "Google Chrome" {filePath} --args --disable-web-security --user-data-dir=/tmp/chrome_dev_test', shell=True, check=True, text=True)
    subprocess.run(f'open -a "Safari" {filePath}', shell=True, check=True, text=True)

async def jsToShowBarGraphForProject(project):
    projectPHID = project['phid']
    tickets = fetchTicketsWithProject(projectPHID)
    ticketIDs = list(map(lambda ticket: f"T{ticket['id']}", tickets))

    ticketTitles = list(map(lambda ticket: ticket['name'], tickets))
    ticketDaysInProj = await asyncio.gather(*map(lambda ticket: asyncio.to_thread(lambda: ticketDaysInProject(ticket, projectPHID)), tickets))

    for i, ticket in enumerate(tickets):
        print(f'''\nT{ticketIDs[i]} - {ticket['phid']}\n"{ticketTitles[i]}"\n{ticketDaysInProj[i]} days on "{project['fields']['name']}"''')

    return f'''
        addGraph(
            {json.dumps(ticketIDs)},
            {json.dumps(ticketDaysInProj)},
            {json.dumps(ticketTitles)},
            'Project: {project['fields']['name']}',
            'Ticket',
            'Days on project',
            metric => `${{metric}} days`
        )
    '''

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
    projects = []
    projectPHIDs = request.args.get('projectPHIDs')
    projectNames = request.args.get('projectNames')

    if projectPHIDs != None:
        projectPHIDs = [phid.strip() for phid in projectPHIDs.split(',')]
        projects = list(getProjectsForProjectPHIDs(projectPHIDs))
    elif projectNames != None:
        projectNames = [name.strip() for name in projectNames.split(',')]
        projects = list(map(lambda projectName: getProjectForProjectTitle(projectName), projectNames))

    jsToShowBarGraphsForProjects = await asyncio.gather(*[jsToShowBarGraphForProject(project) for project in projects])
    return htmlToShowGraphsForProjects(''.join(jsToShowBarGraphsForProjects))

@app.route('/')
async def main():
    return await start()
