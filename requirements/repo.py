import logging
import os
from typing import Optional, List

import pygit2
from django.contrib.auth.models import User
from pygit2 import Repository, GIT_STATUS_IGNORED, GIT_STATUS_WT_MODIFIED, GIT_STATUS_INDEX_MODIFIED, GIT_STATUS_WT_NEW
from pygit2._pygit2 import TreeBuilder

from requirements.utils import repository_path

_log = logging.getLogger(__name__)


class GitFileStatusRecord(object):
    def __init__(self, name, status):
        self.selected = False
        self.name = name
        self.status = status

    @property
    def base_name(self):
        pos = self.name.rfind('/')
        return self.name if pos == -1 else self.name[pos+1:-4]

    def status_text(self):
        if self.status == GIT_STATUS_WT_MODIFIED:
            return 'Modified'
        elif self.status == GIT_STATUS_INDEX_MODIFIED:
            return 'Index changed'
        elif self.status == GIT_STATUS_WT_NEW:
            return 'Index new'
        else:
            return self.status


class MyPyGit2(object):

    class MyRemoteCallbacks(pygit2.RemoteCallbacks):
        def push_update_reference(self, refname, message):
            print(refname, message)

        def sideband_progress(self, string):
            print(string)

        def transfer_progress(self, stats):
            print(stats)

    def __init__(self, user):
        #  type: (User) -> None
        self._user = user  # type: User
        self._repo = pygit2.init_repository(repository_path(user))  # type: Repository

    @staticmethod
    def version():
        return tuple([int(i) for i in pygit2.__version__.split(".")])

    @staticmethod
    def remote_keypair():
        userhome = os.path.expanduser('~')
        return pygit2.Keypair('git', os.path.join(userhome, '.ssh', 'id_ed25519.pub'), os.path.join(userhome, '.ssh', 'id_ed25519'), '')

    @staticmethod
    def is_not_pulled():
        # type: () -> bool
        return True

    def diff_patch(self, ref='HEAD', filter_file=None):
        #  type: (str, Optional[str]) -> str
        patch_text = ''
        for patch in self._repo.diff(ref):
            if filter_file is None:
                patch_text += patch.text
            else:
                line = patch.text.partition('\n')[0]
                if filter_file in line:
                    patch_text += patch.text
        return patch_text

    def modified_files(self):
        #  type: () -> List[GitFileStatusRecord]
        modified = []
        repostatus = self._repo.status()
        for obj in repostatus:
            if repostatus[obj] != GIT_STATUS_IGNORED:
                modified.append(GitFileStatusRecord(obj, repostatus[obj]))
        return modified

    def commit_and_push(self, remote_name='origin', branch='master'):
        # type: (str , str) -> None
        index = self._repo.index
        reference = 'refs/HEAD'
        message = '...some commit message...'
        tree = index.write_tree()
        author = pygit2.Signature(self._user.get_full_name(), self._user.get_email_field_name())
        commiter = pygit2.Signature(self._user.get_full_name(), self._user.get_email_field_name())
        _oid = self._repo.create_commit(reference, author, commiter, message, tree, [self._repo.head.get_object().hex])
        for remote in self._repo.remotes:
            if remote.name == remote_name:
                remote.push(f'refs/heads/{branch}', callbacks=MyPyGit2.MyRemoteCallbacks(credentials=MyPyGit2.remote_keypair()))

    def pull(self, remote_name='origin', branch='master'):
        #  type: (str, str) -> None
        for remote in self._repo.remotes:
            if remote.name == remote_name:
                remote.fetch(callbacks=MyPyGit2.MyRemoteCallbacks(credentials=MyPyGit2.remote_keypair()))
                remote_master_id = self._repo.lookup_reference('refs/remotes/origin/%s' % branch).target
                merge_result, _ = self._repo.merge_analysis(remote_master_id)
                if merge_result & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
                    return
                elif merge_result & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
                    self._repo.checkout_tree(self._repo.get(remote_master_id))
                    try:
                        master_ref = self._repo.lookup_reference('refs/heads/%s' % branch)
                        master_ref.set_target(remote_master_id)
                    except KeyError:
                        self._repo.create_branch(branch, self._repo.get(remote_master_id))
                    self._repo.head.set_target(remote_master_id)
                elif merge_result & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
                    self._repo.merge(remote_master_id)
                    if self._repo.index.conflicts is not None:
                        for conflict in self._repo.index.conflicts:
                            print('Conflicts found in:', conflict[0].path)
                        raise AssertionError('Conflicts, ahhhhh!!')

                    user = self._repo.default_signature
                    tree = self._repo.index.write_tree()
                    _commit = self._repo.create_commit('HEAD', user, user, 'Merge!', tree, [self._repo.head.target, remote_master_id])
                    self._repo.state_cleanup()
                else:
                    raise AssertionError('Unknown merge analysis result')

    def test(self):
        tb = self._repo.TreeBuilder()  # type: TreeBuilder
        index = self._repo.index
        index.read()
        for f in index:
            print(f)
