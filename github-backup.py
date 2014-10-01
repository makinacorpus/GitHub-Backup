#!/usr/bin/env python

"""
Authors: Anthony Gargiulo (anthony@agargiulo.com)
Steffen Vogel (post@steffenvogel.de)

Created: Fri Jun 15 2012
"""

from pygithub3 import Github
from argparse import ArgumentParser
import subprocess
import os

def main():
    """Main program"""

    parser = init_parser()
    args = parser.parse_args()

    git_options = args.git.split()

    # Process args
    if args.cron:
        git_options.append("--quiet")

    # Make the connection to Github here.
    config = {'user': args.username}

    if (args.password):
        config['password'] = args.password
        config['login'] = args.username

    # if both password and token are specified, the token will be
    # used, according to pygithub3 sources
    # however, the username isn't required when using a token
    if (args.token):
        config['token'] = args.token

    ghs = Github(**config)

    # Get all of the given user's repos
    if args.organization:
        user_repos = ghs.repos.list_by_org(args.organization).all()
    else:
        user_repos = ghs.repos.list().all()

    for repo in user_repos:
        repo.user = ghs.users.get(repo.owner.login)
        process_repo(repo, args, tuple(git_options))


def init_parser():
    """
    Set up the argument parser
    """

    parser = ArgumentParser(
        description="makes a backup of all of a github user's repositories")

    parser.add_argument("username", help="A Github username")
    parser.add_argument("backupdir",
                        help="The folder where you want your backups to go")
    parser.add_argument("-c", "--cron",
                        help="Use this when running from a cron job",
                        action="store_true")
    parser.add_argument("-m", "--mirror",
                        help="Create a bare mirror", action="store_true")
    parser.add_argument("-g", "--git",
                        default="", metavar="ARGS",
                        help="Pass extra arguments to git")
    parser.add_argument("-s", "--suffix",
                        default="",
                        help="Add suffix to repository directory names")
    parser.add_argument("-p", "--password",
                        help="Authenticate with Github API")
    parser.add_argument("-P", "--prefix",
                        default="",
                        help="Add prefix to repository directory names")
    parser.add_argument("-o", "--organization",
                        help="Backup Organizational repositories")
    parser.add_argument("-S", "--ssh",
                        action="store_true",
                        help="Use SSH protocol")
    parser.add_argument("-t", "--token",
                        default="",
                        help="Authenticate with Github API using OAuth token")
    return parser


def process_repo(repo, args, git_options):
    """Processes a repository. Which is to say, clones or updates an existing
    clone."""

    if not args.cron:
        print("Processing repo: %s" % (repo.full_name))

    backupdir = os.path.join(args.backupdir, 
                             args.prefix + repo.name + args.suffix)
    config = os.path.join(backupdir, 
                          "config" if args.mirror else ".git/config")

    if not os.access(config, os.F_OK):
        if not args.cron:
            print("Repo doesn't exists, lets clone it")
        clone_repo(repo, backupdir, args, git_options)
    else:
        if not args.cron:
            print("Repo already exists, let's try to update it instead")

    update_repo(repo, backupdir, args, git_options)


def clone_repo(repo, backupdir, args, git_options):
    """Clones a repository using the command line git tool."""
    if args.mirror:
        git_options = list(git_options)
        git_options.append("--mirror")

    # TODO: handle output. 
    output = subprocess.check_output(
        ['git', 'clone'] + list(git_options) + 
        [repo.ssh_url if args.ssh else repo.git_url, 
         backupdir])


def update_repo(repo, backupdir, args, git_options):
    """Update an existing cloned repository via the command line git tool"""

    saved_path = os.getcwd()
    os.chdir(backupdir)
    print(os.getcwd())
    # TODO: log the output? 
    if args.mirror:
        output = subprocess.check_output(['git', 'fetch', '--prune'] + 
                                         list(git_options))
    else:
        output = subprocess.check_output(['git', 'pull'] + list(git_options))
        
    # Fetch description and owner (useful for gitweb, cgit etc.)
    config_args = ['git', 'config', '--local'] 
     
    subprocess.check_call(config_args + ["gitweb.description", 
                                         repo.description])
    subprocess.check_call(config_args + ["gitweb.owner", "%s <%s>" %
                                         (repo.user.name,
                                          repo.user.email.encode("utf-8"))])
    subprocess.check_call(config_args + ["cgit.name", repo.name])
    subprocess.check_call(config_args + ["cgit.defbranch", 
                                         repo.default_branch])
    subprocess.check_call(config_args + ["cgit.clone-url", repo.clone_url])

    os.chdir(saved_path)


def shell_escape(dirty_str):
    """Escape a string for the shell. 

    Should be made obsolete by using subprocess."""
    return "'" + unicode(dirty_str.replace("'", "\\'")).encode("utf-8") + "'"


if __name__ == "__main__":
    main()
