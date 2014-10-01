#!/usr/bin/env python

"""
Authors: Anthony Gargiulo (anthony@agargiulo.com)
Steffen Vogel (post@steffenvogel.de)

Created: Fri Jun 15 2012
"""

from pygithub3 import Github
from argparse import ArgumentParser
import os


def main():
    """Main program"""

    parser = init_parser()
    args = parser.parse_args()

    # Process args
    if args.cron:
        args.git += "--quiet"

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
        process_repo(repo, args)


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


def process_repo(repo, args):
    """Processes a repository. Which is to say, clones or updates an existing
    clone."""

    if not args.cron:
        print("Processing repo: %s" % (repo.full_name))

    backupdir = "%s/%s" % (args.backupdir, args.prefix +
                           repo.name + args.suffix)
    config = "%s/%s" % (backupdir, "config" if args.mirror else ".git/config")

    if not os.access(config, os.F_OK):
        if not args.cron:
            print("Repo doesn't exists, lets clone it")
        clone_repo(repo, backupdir, args)
    else:
        if not args.cron:
            print("Repo already exists, let's try to update it instead")

    update_repo(repo, backupdir, args)


def clone_repo(repo, backupdir, args):
    """Clones a repository using the command line git tool."""
    if args.mirror:
        options = args.git + " --mirror"
    else:
        options = args.git

    # TODO: replace with subprocess.
    os.system('git clone %s %s %s' % (
            options, repo.ssh_url if args.ssh else repo.git_url, backupdir))


def update_repo(repo, backupdir, args):
    """Update an existing cloned repository via the command line git tool"""

    saved_path = os.getcwd()
    os.chdir(backupdir)

    # GitHub => Local
    # TODO: use subprocess package and fork git into
    # background (major performance boost expected)
    if args.mirror:
        os.system("git fetch %s" % (args.git + " --prune",))
    else:
        os.system("git pull %s" % (args.git,))

    # Fetch description and owner (useful for gitweb, cgit etc.)
    # TODO: can we combine that in a single call to 'git config'
    os.system("git config --local gitweb.description %s" %
              (shell_escape(repo.description),))
    os.system("git config --local gitweb.owner %s" %
              (shell_escape("%s <%s>" %
                            (repo.user.name,
                             repo.user.email.encode("utf-8"))),))

    os.system("git config --local cgit.name %s" % (shell_escape(repo.name),))
    os.system("git config --local cgit.defbranch %s" %
              (shell_escape(repo.default_branch),))
    os.system("git config --local cgit.clone-url %s" %
              (shell_escape(repo.clone_url),))

    os.chdir(saved_path)


def shell_escape(dirty_str):
    """Escape a string for the shell. 

    Should be made obsolete by using subprocess."""
    return "'" + unicode(dirty_str.replace("'", "\\'")).encode("utf-8") + "'"


if __name__ == "__main__":
    main()
