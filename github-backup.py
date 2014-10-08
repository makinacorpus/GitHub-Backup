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
import logging
import logging.config


def main():
    """Main program"""

    parser = init_parser()
    args = parser.parse_args()
    init_logging(args)

    git_options = args.git.split()

    # Process args
    if args.log_level not in ('info', 'debug'):
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

    logging.debug("Contacting github with: %s", config)
    ghs = Github(**config)

    # Get all of the given user's repos
    if args.organization:
        user_repos = ghs.repos.list_by_org(args.organization).all()
    else:
        user_repos = ghs.repos.list().all()

    # Fetch users while the backend has an HTTPS connection open.
    for repo in user_repos:
        logging.debug("Getting user for %s", repo.full_name)
        repo.user = ghs.users.get(repo.owner.login)
        logging.debug("User is %s", repo.user)
 
    for repo in user_repos:
       process_repo(repo, args, tuple(git_options))


def init_logging(args):
    """Set up logging based on command line perferences"""

    logging_conf = {
        'version': 1,
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                },
            },
        'root': {
            'level': args.log_level.upper(),
            'handlers': ['console'],
            },
        }
    logging.config.dictConfig(logging_conf)

def init_parser():
    """
    Set up the argument parser
    """

    parser = ArgumentParser(
        description="makes a backup of all of a github user's repositories")

    parser.add_argument("username", help="A Github username")
    parser.add_argument("backupdir",
                        help="The folder where you want your backups to go")
    parser.add_argument("--log-level",
                        choices=["debug", "info", "warn",
                                 "error", "critical"],
                        default="info",
                        help="Level of logging detail.")
    parser.add_argument("-c", "--cron",
                        dest="log_level",
                        action="store_const",
                        const="warn",
                        help="Synonym for --logging=warning")
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

    
    logging.info("Processing repo: %s", repo.full_name)

    backupdir = os.path.join(args.backupdir, 
                             args.prefix + repo.name + args.suffix)
    config = os.path.join(backupdir, 
                          "config" if args.mirror else ".git/config")

    if not os.access(config, os.F_OK):
        logging.info("Repo doesn't exists, lets clone it")
        try:
            clone_repo(repo, backupdir, args, git_options)
        except subprocess.CalledProcessError:
            # Don't try to update if clone failed.
            return None

    update_repo(repo, backupdir, args, git_options)
    return None

def clone_repo(repo, backupdir, args, git_options):
    """Clones a repository using the command line git tool."""

    logging.debug("In clone_repo:")
    if args.mirror:
        git_options = list(git_options)
        git_options.append("--mirror")

    try:
        git_args = ['git', 'clone'] + list(git_options) +\
            [repo.ssh_url if args.ssh else repo.git_url, 
             backupdir]
        logging.debug("Running command: %s", git_args)
        output = subprocess.check_output(git_args, stderr=subprocess.STDOUT)
        logging.info(output.rstrip())
    except subprocess.CalledProcessError as err:
        logging.error("Clone of %s failed with error code: %s", 
                      repo.full_name, err.returncode)
        logging.error("  Command:: %s", err.cmd)
        logging.error("  Output: %s", err.output.rstrip())
        # reraise so the process function can avoid updating.
        raise

    return None

def update_repo(repo, backupdir, args, git_options):
    """Update an existing cloned repository via the command line git tool"""

    logging.debug("In update_repo:")
    saved_path = os.getcwd()
    os.chdir(backupdir)
    logging.debug("Changed to %s", backupdir)

    try:
        if args.mirror:
            git_args = ['git', 'fetch', '--prune'] + list(git_options)
        else:
            git_args = ['git', 'pull'] + list(git_options)
        logging.debug("Running command: %s", git_args)
        output = subprocess.check_output(git_args, stderr=subprocess.STDOUT)
        logging.info(output.rstrip())
    except subprocess.CalledProcessError as err:
        logging.error("Update of %s failed with error code: %s",
                      repo.full_name, err.returncode)
        logging.error("  Command:: %s", err.cmd)
        logging.error("  Output: %s", err.output.rstrip())
        os.chdir(saved_path)
        logging.debug("Changed to %s", saved_path)
        return None

    # Fetch description and owner (useful for gitweb, cgit etc.)
    config_args = ['git', 'config', '--local'] 
     
    try:
        subprocess.check_call(config_args + ["gitweb.description", 
                                             repo.description])
        subprocess.check_call(config_args + ["gitweb.owner", "%s <%s>" %
                                             (repo.user.name,
                                              repo.user.email.encode("utf-8"))])
        subprocess.check_call(config_args + ["cgit.name", repo.name])
        subprocess.check_call(config_args + ["cgit.defbranch", 
                                             repo.default_branch])
        subprocess.check_call(config_args + ["cgit.clone-url", repo.clone_url])
    except subprocess.CalledProcessError as err:
        logging.error("Description update failed with error code: %s",
                      err.returncode)
        logging.error("  Command:: %s", err.cmd)
        logging.error("  Output: %s", err.output.rstrip())

    os.chdir(saved_path)
    logging.debug("Changed to %s", saved_path)
    return None


if __name__ == "__main__":
    main()
