"""Tools for .csv data files.

Author: Guangyu Peng
"""

import csv

def read_csv(filepath, ignore_title=False, delimiter=','):
    csv_data = []
    with open(filepath) as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=delimiter)
        if ignore_title:
            next(csv_reader)
        for row in csv_reader:
            csv_data.append(row)
    return csv_data

def write_csv(filepath, title, rows_list,
              ignore_title=False, delimiter=','):
    with open(filepath, 'w') as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=delimiter)
        if not ignore_title:
            csv_writer.writerow(title)
        for row in rows_list:
            csv_writer.writerow(row)