import logging
import os

import pygit2
from django.contrib.auth.models import User
from django.conf import settings
from pygit2 import Repository

from requirements.utils import repository_path

_log = logging.getLogger(__name__)


def pygit2_version():
    return tuple([int(i) for i in pygit2.__version__.split(".")])


def remote_keypair():
    userhome = os.path.expanduser('~')
    return pygit2.Keypair('git', os.path.join(userhome, '.ssh', 'id_ed25519.pub'), os.path.join(userhome, '.ssh', 'id_ed25519'), '')


class MyRemoteCallbacks(pygit2.RemoteCallbacks):
    def push_update_reference(self, refname, message):
        print(refname, message)

    def sideband_progress(self, string):
        print(string)

    def transfer_progress(self, stats):
        print(stats)


def pygit2_init_repository(user):
    # type: (User) -> Repository
    return pygit2.init_repository(repository_path(user))


def pygit2_not_pulled(user):
    # type: (User) -> Repository
    return True


def pygit2_commit_and_push(user, repo, remote_name='origin', branch='master'):
    # type: (User, pygit2.Repository, str , str) -> None
    index = repo.index
    reference = 'refs/HEAD'
    message = '...some commit message...'
    tree = index.write_tree()
    author = pygit2.Signature(user.get_full_name(), user.get_email_field_name())
    commiter = pygit2.Signature(user.get_full_name(), user.get_email_field_name())
    oid = repo.create_commit(reference, author, commiter, message, tree, [repo.head.get_object().hex])
    for remote in repo.remotes:
        if remote.name == remote_name:
            remote.push(f'refs/heads/{branch}', callbacks=MyRemoteCallbacks(credentials=remote_keypair()))


def pygit2_pull(repo, remote_name='origin', branch='master'):
    #  type: (pygit2.Repository, str, str) -> None
    for remote in repo.remotes:
        if remote.name == remote_name:
            remote.fetch(callbacks=MyRemoteCallbacks(credentials=remote_keypair()))
            remote_master_id = repo.lookup_reference('refs/remotes/origin/%s' % branch).target
            merge_result, _ = repo.merge_analysis(remote_master_id)
            if merge_result & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
                return
            elif merge_result & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
                repo.checkout_tree(repo.get(remote_master_id))
                try:
                    master_ref = repo.lookup_reference('refs/heads/%s' % branch)
                    master_ref.set_target(remote_master_id)
                except KeyError:
                    repo.create_branch(branch, repo.get(remote_master_id))
                repo.head.set_target(remote_master_id)
            elif merge_result & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
                repo.merge(remote_master_id)
                if repo.index.conflicts is not None:
                    for conflict in repo.index.conflicts:
                        print('Conflicts found in:', conflict[0].path)
                    raise AssertionError('Conflicts, ahhhhh!!')

                user = repo.default_signature
                tree = repo.index.write_tree()
                commit = repo.create_commit('HEAD', user, user, 'Merge!', tree, [repo.head.target, remote_master_id])
                repo.state_cleanup()
            else:
                raise AssertionError('Unknown merge analysis result')