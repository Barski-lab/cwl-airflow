import os


def get_folder(abs_path, permissions=0o0775, exist_ok=True):
    try:
        os.makedirs(abs_path, mode=permissions)
    except os.error as ex:
        if not exist_ok:
            raise
    return abs_path