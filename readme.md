# SimonsProject

Django web app (Part 1) + standalone CLI (Part 2) for fetching NCBI nucleotide records via EFetch, storing/displaying documents, and regex-searching sequences.

---

## Quick Start

### Prerequisites
- Python 3.12 or newer  
- PostgreSQL (running locally or via Docker)  
- Git

Clone the repository
```bash
git clone https://github.com/ndavis09/SimonsProject.git
cd SimonsProject
```

Create and activate a virtual environment
```bash
python -m venv venv
venv\Scripts\activate    # on Windows
# or 
source venv/bin/activate  # on macOS/Linux
```

Install dependencies
```bash
pip install -r requirements.txt
```

Apply database migrations
```bash
python manage.py migrate
```

Run the development server
```bash
python manage.py runserver
```

Then open http://127.0.0.1:8000 in your browser.  Note that you will need a Postgres database running for this.  A dockerfile is provided for this, but if you have a local instance you prefer to use, just make sure [the credentials in settings.py](https://github.com/ndavis09/SimonsProject/blob/81b8f90c7a90da917bbd7237e70708773fce4fc0/SimonsProject/settings.py#L78-L83) align with your DB.

With the repo on your machine, you can run the script for part like so:
```bash
python efetcher.py --id 30271926 --regex "(GAATAATGC)" --context 1
```

---

## Architecture

I tried to keep this as lean as possible while still making use of the spec suggestions.  To this end, the only big architectural requirements here are Django, Postgres, Psycopg, and Requests.

Part 1 is done entirely as a simple Django app.  On a fresh run, the user will input their efetch parameters, then will "Fetch and Save" the return document for easy later retrieval.  I make use of a Postgres DB model to store the returned document, which happens upon a successful fetch so that users can later pull up documents they've previously fetched (via the DB-backed "Recent Documents" subsection of the homepage) without hitting the NIH endpoint multiple times (though this is optional; if the underlying documents are expected to change, using the Fetch and Save button again will re-fetch the document fresh.)  Note that because the fetch operation is essentially upserting on db/id/rettype/retmode, this implementation lacks a way for tracking sequence history (if indeed the sequences were ever to change.)  Furthermore, as coded, only the 10 most recent documents fetched will be displayed here, although all documents fetched are stored in the DB, meaning we could change this in many ways if required, e.g. present a list of all documents ever stored, perhaps with search functionality.  However, for the purposes of this exercise (just two documents, one large one small) I felt it best to keep things simple, though this DB-backed retrieval method could be extremely important if the NIH server enforces a usage policy that throttles repeat requests for data.

When a document is pulled up, either by fetch or DB retrieval, the user is taken to a details page, and is presented with the ID and metadata of the document, as well as the nucleic acid sequence in its own dedicated div.  In the metadata, I give a hash for the response to more easily check if two server responses are 1-1; note that an upgrade could be worked out here if the endpoint could also offer up hashes for comparison.  In the upper-righthand corner of the screen will be a box for regex searching.  The nature of the sequence display (the code attempts to display the whole sequence in the div, regardless of how massive it is) and the regex search return (which re-renders the entire div for each 'marking' call) make this approach ill-suited to rendering the larger dataset in Part 2.  If I had more time, and we wanted to render arbitarily long sequences in this way, a relatively straightforward change would be to switch this to a paginated model, where we might display 'pages' of roughly 1MB in the div, with buttons around the div for navigation.  We could also modify the regex search to store pagination data, allowing us to quickly pull up regex results across pages.  Note, however, that even if we solve the display/pagination issue, we'll still be bound by the performance of the regex search, which will become slower as sequence length increases, particularly for searches with many matches, e.g. "A".

Part 2 takes the suggested Python script approach.  It takes the user's parameters then hits the NIH server similarly to the Django approach (simple requests library call) but stores the retrieved data in a temporary file for processing (optionally, the user can save the call's contents in a non-temporary file by passing through the use of the `keep-files` parameter.)  The sequence is then fed to a regex matching method which scans over the sequence and returns a list of results.  Here was another architectural choice: for the sake of simplicity, I opted to load the full sequence into memory, and perform the regex search so it returns a full list of matches.  This works performantly on my desktop machine even with the 200MB file, but for larger datasets or less powerful machines, a solution that streams the data in and performs regex matching on chunks might be useful.  Additionally, if the regex matching was known in advance to be very simple, (e.g. "GATTACA") an alternative solution where we just scan text as it streams in may be viable.  In any case, once we have our list of regex matches, we pass these on to another method which builds our 'contexts' for the matching strings.  A context is how many non-matching characters on either side of the match are displayed, along with potential ellipses to indicate that the match is in the beginning, middle, or end of the sequence.  Again, for the sake of simplicity, I chose to build these context strings using list slicing of the sequence text, but the performance tradeoff here in cases with many matches should be acknowledged.  A faster approach might be to try and extract all contexts in a single pass, reducing computational complexity to O(n).  Once the contexts have been created, the program prints them out along with their character indexes like:
`29622:"...TGAATAATGCT..."`
(search for `--regex "(GAATAATGC)"` with `--context 1`)




