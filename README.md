# Key Sentence Extractor
- EmbedRank
    - text extraction
    - POS tagging
    - doc2vec embedding
    - mmr
- frontend
    - flask templet
    - jinja engine
- backend
    - flask

# digit > 100, delete sentence
# digit > 20, check for validation
	- check if there is more than 10 digits continuously
	- digit that came in window of 4 char is consider as continuously
	- if not we dont count
	- if yes we delete that line from sentence and divide the sent

# TODO: try to remove the % after digit line
	- thoughts
		- if end_index = 10, check chars after end_index that is not alphabet, then move end_index to the
		  index of firs talphabet+1
