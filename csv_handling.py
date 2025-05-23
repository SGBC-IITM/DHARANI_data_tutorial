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


def load_csv(listingfilename, keycol='section_number'):
    """
    Loads a CSV file into a dictionary of namedtuples.

    Args:
        listingfilename: Path to the CSV file.
        keycol: The name of the column to use as the dictionary key.
                If None, returns a list of dictionaries. Defaults to 'section_number'.

    Returns:
        A dictionary where keys are values from `keycol` and values are namedtuples
        representing rows, or a list of dictionaries if `keycol` is None.
        
    """
    if keycol is None:
        listing = []
    else:
        listing={}
    with open(listingfilename) as listingfile:
        reader = csv.reader(listingfile)
        headings = next(reader)
        RowType = namedtuple('RowType', _make_cleaned_headings(headings))
        for row in reader:
            rec = RowType(*row)
            if keycol is not None:
                keyval = getattr(rec,keycol)
                if keyval.isdigit():
                    listing[int(keyval)]=rec
                else:
                    listing[keyval]=rec
            else:
                listing.append(rec._asdict()) # suitable for constructing pandas DataFrame
    return listing
    