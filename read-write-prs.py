import datetime
import json
import os
import requests
import time

import duckdb

START = '2023-04-01'
END   = '2023-05-01'
RWS   = [
         ('0xRob','0xRobin'),
         ('Huang Geyang','Hosuke'),
        ]

DATA_FOLDER = os.environ.get('SPELLBOOK_JSON_STATS_LOC')
GITHUB_TOKEN = os.environ.get('MM_GITHUB_API')

GITHUB_AUTH_HEADER = { 'authorization': "token {0}".format(GITHUB_TOKEN) }
ISSUES_ENDPOINT = "https://api.github.com/repos/duneanalytics/spellbook/issues"

def write_response(file_name, content):
    f = open(DATA_FOLDER + file_name, "w")
    f.write(content)
    f.close()

def get_issue_timeline(issue_no):
    with requests.Session() as session:
        try:
            # Get and store timeline response
            req = f"https://api.github.com/repos/duneanalytics/spellbook/issues/{issue_no}/timeline?per_page=100"
            resp = session.get(req, headers=GITHUB_AUTH_HEADER)

            resp_object = resp.json()
            for r in resp_object:
                r['issue_no'] = issue_no

            write_response(f"issues-timeline-{issue_no}.json", json.dumps(resp_object))
            print(f"Wrote timeline response for {issue_no} to disk")
        except:
            print(f"Error writing timeline for {issue_no}")
            print(resp_object)

# Get current open issues
# https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#list-repository-issues
def get_issues(last_updated_at, sort='created', page=1):
    with requests.Session() as session:
            time.sleep(3)
            req = f"{ISSUES_ENDPOINT}?per_page=100&sort={sort}&page={page}&state=all&since={last_updated_at}&direction=ASC"
            print(req)
            resp = session.get(req, headers=GITHUB_AUTH_HEADER)

            resp_object = resp.json()
            no_of_results = len(resp_object)
            for issue in resp_object:
                issue_no = issue['number']

                # rename field `user` as this is a reserved field in duckdb
                try:
                    issue['issue_creator'] = issue['user']['login']
                except:
                    print(f"Error getting `user.login` for {issue_no}")
                    issue['issue_creator'] = None

                # distinguish PRs and issues
                # "Issues" endpoints may return both issues and pull requests in the response.
                if issue.get('pull_request'):
                    issue['issue_type'] = 'pull_request'
                else:
                    issue['issue_type'] = 'issue'

                write_response(f"issues-issue-{issue_no}.json", json.dumps(issue))
                print(f"Wrote {issue_no} to disk")

                time.sleep(3)
                get_issue_timeline(issue_no)

            return no_of_results

def show_work(start, end):
    for res_wiz in RWS:
        print(f'Work for {res_wiz[1]}')
        # all issues for time interval between start and end
        sql_all= duckdb.sql(f"""
        SELECT number, created_at, issue_creator, issue_type, title 
        FROM '{DATA_FOLDER}issues-issue-*.json' 
        WHERE created_at >= '{start}' AND created_at < '{end}'
        """)

        # filter for issues created by RW
        sql_creator = duckdb.sql(f"SELECT * FROM sql_all WHERE issue_creator = '{res_wiz[1]}'")
        duckdb.sql("SELECT * FROM sql_creator ORDER BY number DESC;").show()


        now = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        duckdb.sql("SELECT * FROM sql_creator ORDER BY number DESC;").write_csv(f"./output/created_by_{res_wiz[1]}_{now}")

        # list issues created by others that RW added commits, comments to
        # or had other interactions with (such as approvals)
        sql_get_work = duckdb.sql(f"""
        SELECT  issue_no, s.created_at, issue_creator, issue_type, title, 
        sum(case when event = 'committed' then 1 else 0 end) no_of_commits,
        sum(case when event = 'commented' then 1 else 0 end) no_of_comments
        FROM '{DATA_FOLDER}issues-timeline-*.json' t
        INNER JOIN (SELECT * FROM sql_all) s ON number = issue_no
        WHERE (author.name = '{res_wiz[0]}' OR actor.login = '{res_wiz[1]}')
        AND number NOT IN (SELECT number FROM sql_creator)
        GROUP BY issue_no, s.created_at, issue_creator, issue_type, title
        ORDER BY no_of_commits DESC, no_of_comments DESC
        """)
        sql_get_work.show()
        sql_get_work.write_csv(f"./output/review_work_by_{res_wiz[1]}_{now}")

def get_last_issue():
    try:
        sql_last_updated = duckdb.sql(f"""
        SELECT max(updated_at)
        FROM '{DATA_FOLDER}issues-issue-*.json' 
        """)
        a = sql_last_updated.fetchall()
        max_time = a[0][0]
        return max_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    # fallback if there is no data yet
    except:
        return '2022-07-01T00:00:00Z'

if __name__ == '__main__':
    # update local JSON data 
    last_updated_at = get_last_issue()
    print(last_updated_at)
    i = 1
    while True:
        no_of_results = get_issues(sort='updated', page=i, last_updated_at=last_updated_at)
        print(no_of_results)
        if no_of_results < 100:
            break
        i += 1
    # compile results for RWs, print and export them as CSV
    show_work(START, END)
