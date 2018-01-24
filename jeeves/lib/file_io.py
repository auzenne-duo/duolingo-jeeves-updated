import gzip
import os

from jeeves import data_directory


def read_from_file(file_path, dir_path=None, compression=True):
    if dir_path is None:
        dir_path = data_directory
    path = os.path.join(dir_path, file_path)
    mode = 'rb' if compression else 'r'
    if compression:
        with gzip.open(path, mode) as f:
            return f.read().decode('utf-8')
    else:
        with open(path, mode) as f:
            return f.read()


def write_to_file(content, file_path, dir_path=None, compression=True):
    if dir_path is None:
        dir_path = data_directory
    path = os.path.join(dir_path, file_path)
    mode = 'wb' if compression else 'w'
    if compression:
        with gzip.open(path, mode) as f:
            f.write(content.encode('utf-8'))
    else:
        with open(path, mode) as f:
            f.write(content)
