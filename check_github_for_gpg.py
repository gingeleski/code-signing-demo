"""
check_github_for_gpg.py

Iterates over GitHub orgs and checks whether users have set up GPG keys.

Put GitHub personal access token in $GITHUB_TOKEN or local .credentials file.

Requirements:
    pip3 install requests

Usage:
    python3 check_github_for_gpg.py --help
"""

import datetime
import json
import os
import re
import requests
import sys
import time


DEBUG_FLAG = False

ENV_GITHUB_TOKEN = 'GITHUB_TOKEN'

EXIT_ERROR = 1
EXIT_OK = 0

FILE_COMPLIANT_USERS = 'COMPLIANT_GITHUB_USERNAMES.txt'
try:
    os.remove(FILE_COMPLIANT_USERS)
except:
    pass
FILE_IGNORED_USERS = 'IGNORED_GITHUB_USERNAMES.txt'
try:
    os.remove(FILE_IGNORED_USERS)
except:
    pass
FILE_NONCOMPLIANT_USERS = 'COMPLIANT_GITHUB_USERNAMES.txt'
try:
    os.remove(FILE_NONCOMPLIANT_USERS)
except:
    pass

GITHUB_TOKEN = os.environ.get(ENV_GITHUB_TOKEN)
if GITHUB_TOKEN == None:
    try:
        with open('.credentials', 'r') as read_file:
            GITHUB_TOKEN = read_file.read().replace('\n','')
    except:
        print('[ERROR] Environment variable GITHUB_TOKEN not set to GitHub personal access token.')
        exit(EXIT_ERROR)

HEADERS = {
    'Accept' : 'application/vnd.github.v3+json',
    'Authorization' : 'token ' + str(GITHUB_TOKEN)
}


def get_all_repos_for_org(org):
    repos = []
    repos_url = 'https://api.gtihub.com/orgs/' + org + '/repos?per_page=100'
    log_debug('\t' + 'Getting all repos for GitHub org ' + org + ' ...')
    page = 1
    while page > 0:
        this_url = repos_url + '&page=' + str(page)
        res = requests.get(this_url, headers=HEADERS)
        if res.status_code != 200:
            page = -1
        if res.status_code == 404:
            log_error('404 response from GET ' + this_url)
            log_error('Does your GITHUB_TOKEN have sufficient permissions for this GitHub org ??')
            exit(EXIT_ERROR)
        elif res.status_code != 200:
            log_error('Unexpected response code ' + str(res.status_code) + ' from GET ' + this_url)
            exit(EXIT_ERROR)
        else:
            repo_list = res.json()
            if 0 != len(repo_list):
                for repo in repo_list:
                    repos.append(repo['html_url'])
            else:
                page = -1
        page += 1
    return repos


def log_debug(string):
    if True == DEBUG_FLAG:
        print('[DEBUG]', string)


def log_error(string):
    print('[ERROR]', string)


def log_info(string):
    print('[INFO]', string)


def log_warning(string):
    print('[WARNING]', string)


def print_help():
    print('CHECK GITHUB FOR GPG')
    print('    Iterates over GitHub orgs and checks whether users have set up GPG keys.')
    print('USAGE :')
    print('    python3 check_github_for_gpg.py -h')
    print('        Just prints this help.')
    print('    python3 check_github_for_gpg.py --help')
    print('        Just prints this help.')
    print('    python3 check_github_for_gpg.py --config <RELATIVE_JSON_FILE_PATH>')
    print('        Executes actual checker program with a prebuilt JSON configuration file.')
    print('    python3 check_github_for_gpg.py --org <ORG_NAME_1> --org <ORG_NAME_N>')
    print('        Executes actual checker program over the specified GitHub org(s).')
    print('ADDITIONAL FLAGS :')
    print('    -d, --debug')
    print('        Prints even more information while running, for debugging purposes and/or curiosity\'s sake.')
    print('EXAMPLES :')
    print('    python3 check_github_for_gpg.py --config config.json')
    print('    python3 check_github_for_gpg.py --org HBOCodeLabs --org turnercode')
    print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print_help()
        exit(EXIT_ERROR)
    if ('-h' in sys.argv) or ('--help' in sys.argv):
        print_help()
        exit(EXIT_OK)
    # Attempt early debug flag processing
    if ('-d' in sys.argv) or ('--debug' in sys.argv):
        DEBUG_FLAG = True
    check_config_files = []
    check_ignores = []
    check_orgs = []
    check_mode = None
    check_span = None
    log_debug(str(datetime.datetime.now()))
    log_debug('[START] Command line argument processing and validation')
    i = 1
    while i < len(sys.argv):
        command_line_argument = str(sys.argv[i]).lower()
        if command_line_argument == '--config' or command_line_argument == '--from-file':
            if i == len(sys.argv) - 1:
                log_error('--config or --from-file was given without a filename afterward')
                exit(EXIT_ERROR)
            if 0 < len(check_config_files):
                log_error('Multiple config files were specified, which is unsupported...')
                exit(EXIT_ERROR)
            input_config_file = str(sys.argv[i+1])
            try:
                with open(input_config_file, 'r') as tempfile:
                    # If we can read the file okay then we can infer it exists, do nothing else right now
                    pass
            except IOError:
                # IOError occurs if file path is invalid
                log_error('--config or --from-file was given with an invalid file path afterward')
                exit(EXIT_ERROR)
            check_config_files.append(input_config_file)
            i += 1
        elif command_line_argument == '--org':
            if i == len(sys.argv) - 1:
                log_error('--org was given without a GitHub org named afterward')
                exit(EXIT_ERROR)
            input_org = str(sys.argv[i+1])
            # Input validation for GitHub org name
            github_org_name_validation = re.compile("/^[a-z\d](?:[a-z\d]|-(?=[a-z\d])){0,50}$/i")
            if False == github_org_name_validation.match(input_org):
                log_error('--org was given with an invalid GitHub org named afterward')
                exit(EXIT_ERROR)
            check_orgs.append(input_org)
            i += 1
        elif command_line_argument == '--span':
            if i == len(sys.argv) - 1:
                log_error('--span was given without an integer day count afterward i.e. "30d"')
                exit(EXIT_ERROR)
            input_span = str(sys.argv[i+1]).lower().strip()
            if False == input_span.replace('d','').isdigit():
                log_error('--span was given without a valid integer day count afterward i.e. "30d"')
                exit(EXIT_ERROR)
            check_span = int(input_span.replace('d',''))
            i += 1
        elif command_line_argument == '--mode':
            if i == len(sys.argv) - 1:
                log_error('--mode was given without "all-users" or "active-users-only" afterward')
                exit(EXIT_ERROR)
            input_mode = str(sys.argv[i+1]).lower().strip()
            if input_mode != "all-users" and input_mode != "active-users-only":
                log_error('--mode was given without "all-users" or "active-users-only" afterward')
                exit(EXIT_ERROR)
            check_mode = input_mode                
            i += 1
        elif command_line_argument == '-d' or command_line_argument == '--debug':
            DEBUG_FLAG = True
        else:
            log_error('Invalid command line argument given : ' + command_line_argument)
            exit(EXIT_ERROR)
        i += 1
    log_debug('\t' + 'check_config_files = ' + str(check_config_files))
    log_debug('\t' + 'check_ignores = ' + str(check_ignores))
    log_debug('\t' + 'check_orgs = ' + str(check_orgs))
    log_debug('\t' + 'check_span = ' + str(check_span))
    log_debug('\t' + 'check_mode = ' + str(check_mode))
    log_debug('[END] Command line argument processing and validation')
    if GITHUB_TOKEN == None:
        print('[ERROR] Environment variable GITHUB_TOKEN not set to GitHub personal access token.')
        exit(EXIT_ERROR)
    log_debug('[START] Configuration file read-in')
    if 0 < len(check_config_files):
        log_debug('Parsing given configuration JSON files ...')
        # FIXME there is little to no input validation on config file read-in
        for check_config_file in check_config_files:
            try:
                log_debug('\t' + 'Reading in file ' + check_config_file)
                f = open(check_config_file)
                parsed_config = json.load(f)
                # If there are 'orgs' given in the config file
                if 'orgs' in parsed_config and parsed_config['orgs'] != None:
                    # Add the orgs along with whatever we might have already from command line args
                    for new_org in parsed_config['orgs']:
                        log_debug('\t\t' + 'Adding "' + new_org + '" to orgs list, from configuration file')
                        check_orgs.append(new_org)
                # If there are 'ignores' given in the config file
                if 'ignores' in parsed_config and parsed_config['ignores'] != None:
                    # Add the ignore list entries along with whatever we might have already from command line args
                    for ignore in parsed_config['ignores']:
                        if 'username' in ignore:
                            log_debug('\t\t' + 'Adding "' + ignore['username'] + '" to ignore list, from configuration file ')
                            check_ignores.append(ignore['username'])
                # If 'mode' was specified in the config file
                if 'mode' in parsed_config and parsed_config['mode'] != None:
                    # Only read in if it wasn't given on the command line
                    if check_mode == None:
                        log_debug('\t\t' + 'Setting check_mode from configuration file')
                        check_span = int(str(parsed_config['mode']).lower())                        
                # If 'span' was specified in the config file
                if 'span' in parsed_config and parsed_config['span'] != None:
                    # Only read in if it wasn't given on the command line
                    if check_span == None:
                        log_debug('\t\t' + 'Setting check_span from configuration file')
                        check_span = int(str(parsed_config['span']).lower().replace('d',''))
                f.close()
            except:
                log_error('Invalid config file specified : ' + check_config_file)
                exit(EXIT_ERROR)
            # Right now we only support reading in a single config file, so break the loop
            break
    log_debug('[END] Configuration file read-in')
    # Default the check mode to "active-users-only" if span was given, or "all-users" otherwise
    if check_mode == None or check_span == None:
        if check_span != None:
            log_info('Defaulting mode to "active-users-only" since a span argument was given')
            check_mode = "active-users-only"
        elif check_mode == None or check_mode == "active-users-only":
            log_info('Defaulting mode to "all-users" since no span argument was given.')
            check_mode = "all-users"
    # If a span of time to check for was given, and the "mode" supports it, convert from days to time
    if check_span != None and check_mode == "active-users-only":
        # The following two lines convert check_span from an integer representation of days to GitHub API-friendly time string
        check_span = str((datetime.datetime.now() - datetime.timedelta(days=int(check_span))).isoformat())
        check_span = check_span.replace('.' + check_span.split('.')[-1], '')
        log_debug('Activity time within which to check users for has been adapted to ' + check_span)
    log_debug('[START] Determine unique members of specified GitHub org(s)')
    unique_users = {}
    for check_org in check_orgs:
        page = 1
        while page > 0:
            this_url = 'https://api.github.com/orgs/' + check_org + '/members?page=' + str(page)
            res = requests.get(this_url, headers=HEADERS)
            if res.status_code != 200:
                log_error('None-200 response from ' + this_url)
                exit(EXIT_ERROR)
            else:
                user_list = res.json()
                if 0 != len(user_list):
                    for user in user_list:
                        if 'login' not in user:
                            log_error('Could not find "login" field for username, response may be corrupted!')
                            exit(EXIT_ERROR)
                        unique_users[user['login']] = True
                else:
                    page = -1
            page += 1
    log_debug('[END] Determine unique members of specified GitHub org(s)')
    if len(unique_users) == 0:
        log_error('No unique GitHub users found for the search parameters given.')
        exit(EXIT_ERROR)
    filtered_unique_users = {}
    if check_mode == "active-users-only":
        check_repos = []
        log_info('Will check activity within ' + str(len(check_orgs)) + ' GitHub orgs')
        for check_org in check_orgs:
            org_repos = get_all_repos_for_org(check_org)
            log_info('Found ' + str(len(org_repos)) + ' repos to check from within the GitHub org ' + check_org + ' ...')
            for org_repo in org_repos:
                check_repos.append(org_repo)
        log_info('Will check activity within ' + str(len(check_repos)) + ' repos from ' + str(len(check_orgs)) + ' GitHub orgs')
        for check_repo_link in check_repos:
            log_info('Checking repository @ ' + check_repo_link + ' ...')
            log_debug('[START] Commit checks')
            branch_url = check_repo_link.replace('https://github.com/', 'https://api.github.com/repos/') + '/branches?per_page=100'
            commits_url = branch_url.replace('/branches', '/commits')
            filtered_commits_url = commits_url + '&since=' + check_span
            page = 1
            while page > 0:
                this_url = filtered_commits_url + '&page=' + str(page)
                res = requests.get(this_url, headers=HEADERS)
                if res.status_code == 404:
                    log_error('404 response from GET ' + this_url)
                    log_error('Does your GITHUB_TOKEN has sufficient permissions for this GitHub org ??')
                    exit(EXIT_ERROR)
                elif res.status_code == 409:
                    log_warning('409 response from GET ' + this_url)
                    page = -1
                elif res.status_code != 200:
                    #page = -1
                    log_error('Unexpected response code ' + str(res.status_code) + ' from GET ' + this_url)
                    exit(EXIT_ERROR)
                else:
                    commits_list = res.json()
                    if 0 == len(commits_list):
                        log_debug('\t\t' + 'No matching Git commits for search parameters in this repo')
                        break
                    log_debug('\t\t' + 'Found ' + str(len(commits_list)) + ' Git commits generally matching search parameters in this repo')
                    for commit in commits_list:
                        if commit != None and 'author' in commit and commit['author'] != None and 'login' in commit['author'] and commit['author']['login'] != None:
                            if commit['author']['login'] not in filtered_unique_users:
                                if commit['author']['login'] in unique_users:
                                    log_debug('\t\t' + 'Labeling GitHub user "' + '" as active after seeing a Git commit from them.')
                                    filtered_unique_users[commit['author']['login']] = True
                page += 1
            log_debug('[END] Commit checks')
    else:
        # There is no filtering so all unique_users go into filtered_unique_users
        filtered_unique_users = unique_users
    ignored_users = []
    non_compliant_users = []
    compliant_users = []
    for user in filtered_unique_users:
        if user in check_ignores:
            ignored_users.append(user)
            continue 
        this_url = 'https://api.github.com/users/' + user + '/gpg_keys'
        res = requests.get(this_url, headers=HEADERS)
        if res.status_code != 200:
            log_error('Non-200 response from GET ' + this_url)
            exit(EXIT_ERROR)
        gpg_keys = res.json()
        if 0 == len(gpg_keys):
            non_compliant_users.append(user)
        else:
            compliant_users.append(user)
    unique_users = len(ignored_users) + len(compliant_users) + len(non_compliant_users)
    log_info('Total unique users across GitHub orgs : ' + str(unique_users) + ' (100.0%)')
    log_info('\t\t' + 'Ignored users, per exception list for GPG key setup : ' + str(len(ignored_users)) + ' (' + str(round((len(ignored_users) / unique_users) * 100.0,3)) + '%)')
    write_file = open(FILE_IGNORED_USERS, 'w')
    ignored_users = sorted(ignored_users, key=str.casefold)
    for user in ignored_users:
        write_file.write(user + '\n')
        log_info('\t\t\t' + user)
    write_file.close()
    log_info('\t\t' + 'Users with GPG keys : ' + str(len(compliant_users)) + ' (' + str(round((len(compliant_users) / unique_users) * 100.0,3)) + '%)')
    write_file = open(FILE_COMPLIANT_USERS, 'w')
    compliant_users = sorted(compliant_users, key=str.casefold)
    for user in compliant_users:
        write_file.write(user + '\n')
        log_info('\t\t\t' + user)
    write_file.close()
    log_info('\t\t' + 'Users without GPG keys : ' + str(len(non_compliant_users)) + ' (' + str(round((len(non_compliant_users) / unique_users) * 100.0,3)) + '%)')
    write_file = open(FILE_NONCOMPLIANT_USERS, 'w')
    non_compliant_users = sorted(non_compliant_users, key=str.casefold)
    for user in non_compliant_users:
        write_file.write(user + '\n')
        log_info('\t\t\t' + user)
    write_file.close()
    log_debug(str(datetime.datetime.now()))
