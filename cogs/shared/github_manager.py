import os
from dotenv import load_dotenv
import github

load_dotenv(dotenv_path=".venv/.env")
git_token = os.getenv("GITHUB_TOKEN")

auth = github.Auth.Token(git_token)
github_access = github.Github(auth=auth)
git_repo = github_access.get_repo("knexwiz/fdlteamlogos")

def upload_to_git(*, folder:str="", file_name:str, extension:str, new_file:bytes) -> str:
    test_contents = git_repo.get_contents(folder, ref="main")
    taken_paths = []

    # noinspection PyTypeChecker
    for git_file in test_contents:
        taken_paths.append(git_file.path)

    def find_new_path(c):
        new_path = f"{folder}{file_name}{'' if c == 1 else c}.{extension}"
        # noinspection PyTypeChecker
        if new_path in taken_paths:
            return find_new_path(c+1)
        return new_path

    path = find_new_path(1)
    git_repo.create_file(
        path=path,
        message="initial commit",
        content=new_file,
        branch="main")

    return (f"https://raw.githubusercontent.com/knexwiz/fdlteamlogos/refs/heads/main/"
            f"{path.replace(' ','%20')}")