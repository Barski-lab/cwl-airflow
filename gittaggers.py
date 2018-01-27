import subprocess
import time
from setuptools.command.egg_info import egg_info


class EggInfoFromGit(egg_info):
    """Tag the build with git commit timestamp.

    If a build tag has already been set (e.g., "egg_info -b", building
    from source package), leave it alone.
    """

    def git_contain_commit_tag(self):
        return subprocess.check_output(['git', 'describe', '--contains']).strip()


    def git_timestamp_tag(self):
        gitinfo = subprocess.check_output(
            ['git', 'log', '--first-parent', '--max-count=1',
             '--format=format:%ct', '.']).strip()
        return time.strftime('.%Y%m%d%H%M%S', time.gmtime(int(gitinfo)))


    def tags(self):
        if self.tag_build is None:
            try:
                self.tag_build = self.git_contain_commit_tag()  # try to get version info from the closest tag
            except subprocess.CalledProcessError:
                try:
                    self.tag_build = self.git_timestamp_tag()  # try to get version info from commit date
                except subprocess.CalledProcessError:
                    pass
        return egg_info.tags(self)
