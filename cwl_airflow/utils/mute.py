import os


def suppress_stdout():
    global NULL_FDS
    global BACKUP_FDS
    try:
        NULL_FDS = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        BACKUP_FDS = os.dup(1), os.dup(2)
        os.dup2(NULL_FDS[0], 1)
        os.dup2(NULL_FDS[1], 2)
    except Exception:
        pass


def restore_stdout():
    try:
        os.dup2(BACKUP_FDS[0], 1)
        os.dup2(BACKUP_FDS[1], 2)
        os.close(NULL_FDS[0])
        os.close(NULL_FDS[1])
    except Exception:
        pass