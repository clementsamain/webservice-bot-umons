import os
from flask import Flask, request
from github import Github, GithubIntegration

app = Flask(__name__)

app_id = 311876

# Read the bot certificate
with open(
        os.path.normpath(os.path.expanduser('../softwareevolutionbot.pem')),
        'r'
) as cert_file:
    app_key = cert_file.read()
    
# Create an GitHub integration instance
git_integration = GithubIntegration(
    app_id,
    app_key,
)

def issue_opened_event(repo, payload):
    issue = repo.get_issue(number=payload['issue']['number'])
    author = issue.user.login

    issue.add_to_labels('needs triage')
    
    response = f"Thanks for opening this issue, @{author}! " \
                f"The repository maintainers will look into it ASAP! :speech_balloon:"
    issue.create_comment(f"{response}")

def pull_request_merged_event(repo, payload):
    pull_request = repo.get_pull(number=payload['pull_request']['number'])
    author = pull_request.user.login

    if pull_request.merged:
        pull_request.add_to_labels('merged')
        response = f"Thanks for your contribution, @{author}! " \
                    f"Your pull request has been merged! :tada:"
        pull_request.create_issue_comment(f"{response}")
        branch = pull_request.head.ref
        #repo.get_git_ref(f"heads/{branch}").delete()

def pull_request_edit_event(repo, payload):
    pull_request = repo.get_pull(payload['pull_request']['number'])
    branch = pull_request.head.ref
    author = pull_request.user.login

    if "wip" not in pull_request.title.lower() and "work in progress" not in pull_request.title.lower() and "do not merge" not in pull_request.title.lower():
        repo.get_commit(sha=pull_request.head.sha).create_status(state="success", description="Ready for review", context="review")
        response = f"Your pull request is ready for review @{author}!"
        pull_request.create_issue_comment(f"{response}")

    if "wip" in pull_request.title.lower() or "work in progress" in pull_request.title.lower() or "do not merge" in pull_request.title.lower():
        repo.get_commit(sha=pull_request.head.sha).create_status(state="pending", description="Work in progress", context="review")
        response = f"Your pull request is currently marked as a work in progress @{author}!"
        pull_request.create_issue_comment(f"{response}")

def pull_request_open_event(repo, payload):
    pull_request = repo.get_pull(payload['pull_request']['number'])
    branch = pull_request.head.ref
    author = pull_request.user.login

    if "wip" in pull_request.title.lower() or "work in progress" in pull_request.title.lower() or "do not merge" in pull_request.title.lower():
        repo.get_commit(sha=pull_request.head.sha).create_status(state="pending", description="Work in progress", context="review")
        response = f"Your pull request is currently marked as a work in progress @{author}!"
        pull_request.create_issue_comment(f"{response}")

@app.route("/", methods=['POST'])
def bot():
    payload = request.json

    if not 'repository' in payload.keys():
        return "", 204

    owner = payload['repository']['owner']['login']
    repo_name = payload['repository']['name']

    git_connection = Github(
        login_or_token=git_integration.get_access_token(
            git_integration.get_installation(owner, repo_name).id
        ).token
    )
    repo = git_connection.get_repo(f"{owner}/{repo_name}")

    # Check if the event is a GitHub issue creation event
    if all(k in payload.keys() for k in ['action', 'issue']) and payload['action'] == 'opened':
        issue_opened_event(repo, payload)
    # Check if the event is a GitHub pull request merge and after closing event
    elif all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'closed':
        pull_request_merged_event(repo, payload)

    # Check if the event is a GitHub pull request open event 
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'opened':
        pull_request_open_event(repo, payload)
    
    # Check if the event is a GitHub pull request edit event
    if all(k in payload.keys() for k in ['action', 'pull_request']) and payload['action'] == 'edited':
        pull_request_edit_event(repo, payload)

    return "", 204

if __name__ == "__main__":
    app.run(debug=True, port=5000)
