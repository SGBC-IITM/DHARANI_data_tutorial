import re
import csv
from collections import namedtuple

# a utility function
def _make_cleaned_headings(headings):
    cleaned_headings = []
    for i, header in enumerate(headings):
        cleaned_i = re.sub(r'[^0-9a-zA-Z_]','_', header.strip())
        if cleaned_i and cleaned_i[0].isdigit():
            cleaned_i = '_'+cleaned_i
        if not cleaned_i:
            cleaned_i = f'column_{i}'
        cleaned_headings.append(cleaned_i)
    return cleaned_headings


def load_csv(listingfilename):
    listing={}
    with open(listingfilename) as listingfile:
        reader = csv.reader(listingfile)
        headings = next(reader)
        RowType = namedtuple('RowType', _make_cleaned_headings(headings))
        for row in reader:
            rec = RowType(*row)
            listing[int(rec.section_number)]=rec

    return listing
