import os


class Mute():
    NULL_FDS = []
    BACKUP_FDS = []

    def __enter__(self):
        self.suppress_stdout()

    def __exit__(self, type, value, traceback):
        self.restore_stdout()

    def suppress_stdout(self):
        self.NULL_FDS = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        self.BACKUP_FDS = os.dup(1), os.dup(2)
        os.dup2(self.NULL_FDS[0], 1)
        os.dup2(self.NULL_FDS[1], 2)

    def restore_stdout(self):
        os.dup2(self.BACKUP_FDS[0], 1)
        os.dup2(self.BACKUP_FDS[1], 2)
        os.close(self.NULL_FDS[0])
        os.close(self.NULL_FDS[1])
