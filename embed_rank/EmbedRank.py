from tika import parser
import nltk
import unidecode
import re
import contractions
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from gensim.models.doc2vec import Doc2Vec
import logging
import os
logger = logging.Logger('catch_all')

# set-up enviornment for off line tika server
os.environ['TIKA_SERVER_JAR'] = os.getcwd() + "/embed_rank/tika_server/tika-server-1.24.1.jar"

stopwords = ['i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 
            'you', "you're", "you've", "you'll", "you'd", 'your', 'yours', 
            'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 
            "she's", 'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 
            'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 
            'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 
            'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 
            'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 
            'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 
            'through', 'during', 'before', 'after', 'above', 'below', 'to', 
            'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 
            'again', 'further', 'then', 'once', 'here', 'there', 'when', 
            'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 
            'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 
            'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 
            'can', 'will', 'just', 'don', "don't", 'should', "should've", 
            'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', 
            "aren't", 'couldn', "couldn't", 'didn', "didn't", 'doesn', 
            "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 'haven', "haven't", 
            'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 
            'needn', "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', 
            "wasn't", 'weren', "weren't", 'won', "won't", 'wouldn', "wouldn't"]

class EmbedRank:
    '''
    This class implements parts to run EmbedRank algorithm

    Attributes:
    ---------------
    sent_tokenizer: nltk sentence tokenizer
    
    punct_tokenizer: nltk punctuation remover
    
    stop_words: stop word list from nltk
    
    pos_tagger: nltk POS (Part Of Speech) tagger
    
    chucker: nltk regex parser used to chunk POS tagged words into specific phrase

    lemmatizer: nltk tool to lemmatize word tokens using POS tag

    parser: tika parser to extract text from files

    model_path: path to load the model
    '''
    def __init__(self, model_path=None):
        self.sent_tokenizer = nltk.tokenize.sent_tokenize
        self.punct_tokenizer = nltk.RegexpTokenizer(r"[^\W_]+|[^\W_\s]+")
        self.stop_words = stopwords
        self.pos_tagger = nltk.pos_tag
        self.chucker = nltk.RegexpParser("""NP:{<JJ>*<NN.*>{0,3}}  # Adjectives (0) plus Nouns (1-3)""")
        self.lemmatizer = nltk.stem.WordNetLemmatizer()
        self.parser = parser
        if model_path != None:
            self.model = Doc2Vec.load(model_path)

    def extract_information(self, pdf_path):
        '''
        This extracts raw text from the given path parameter

        Parameter:
        ---------------
        pdf_path: path of pdf to extract text from
        
        Parameter:
        ---------------
        Extracted raw text
        '''
        text = ''
        try:
            pdf_parser = self.parser.from_file(pdf_path)
            text = pdf_parser['content']

            # check if we got the text, if text is none, then the pdf is probably a scan
            if text == None:
                # TODO handle scanned pdf
                print("Activating OCR")
                #OCR_headers = {'X-Tika-PDFextractInlineImages': 'true'}
                #pdf_parser = parser.from_file(pdf_path, serverEndpoint="http://localhost:9998/rmeta/text",
                #                              headers=OCR_headers)
                #text = pdf_parser['content']
        except Exception as e:
            print("\n\nFailing to extract text from :", pdf_path, "\n")
            logger.error(e)
            print("\n")
        return text

    def tokenize(self, text):
        '''
        TODO: empty sentence removal

        This method dones the following
            - remove accents from accented chars
            - remove URLs
            - remove emails
            - remove digits
            - expand word contractions
            - splits text into sentence tokens then word tokens
            - normalize each sentence with lower case
            - remove punctuations

        Parameter:
        ---------------
        text: raw text to be tokenized

        Return:
        ---------------
        og_sent: list of sent token

        word_token: list of cleanned word tokens
        '''
        # remove accents
        text = unidecode.unidecode(text)
        og_sent = self.sent_tokenizer(text)
   
        # remove URLs (both http and www), emails, and digits
        # http\S+: regex for http links
        # www\S+: regex for www links
        # \S*@\S*\s?: regex for emails
        # [0-9]: regex for digits
        text = re.sub(r"http\S+|www\S+|\S*@\S*\s?|[0-9]", "", text)

        # expand contractions
        text = contractions.fix(text)

        # tokenize by sent and remove empty line
        sent_token = og_sent
        # sent_token = [sent for sent in sent_token if len(sent)]
        word_token = []

        # remove punctuations and lower case all
        for i in range(len(sent_token)):
            word_token.append(self.punct_tokenizer.tokenize(sent_token[i].lower()))
        
        return og_sent, word_token

    def pos_tag(self, lst_word_tokens):
        '''
        This method applies POS tag to each word

        Parameter:
        ---------------
        lst_word_tokens: 2d list where first dimension holds sentence level tokens
                         then each sentence token holds it's word tokens
        
        Return:
        ---------------
        lst_word_tokens: 2d list with first dimension representing the sentence of text corpus
        and second dimension the tuple of word token with its POS tag. (word, POS_tag)
        '''
        # apply POS tag to each word
        for i in range(len(lst_word_tokens)):
            lst_word_tokens[i] = self.pos_tagger(lst_word_tokens[i])

        # filter out unwanted tags
        wanted_tags = ['NN','NNS','NNP','NNPS','JJ','JJR','JJS']
        lst_word_tokens = [[word_token for word_token in sent_token if word_token[1] in wanted_tags]
                           for sent_token in lst_word_tokens]

        return lst_word_tokens

    def get_wordnet_pos(self, word_POS_tag):
        '''
        Helper method of preprocess, returns pos parameter of nltk lemmatizer

        Parameter:
        ---------------
        word_POS_tag: POS tag for the word token

        Return:
        ---------------
        str representation of nltk wordnet tag type
        '''
        return 'n' if word_POS_tag.startswith("N") else 'a'

    def preprocess(self, lst_word_tokens, remove_stopwords=True):
        '''
        TODO: remove empty sentence doc
        
        This method does the following:
            - remove stop words: if remove_stopwords is True
            - remove words with <= 2 chars or > 21 chars
            - apply lemmatization on each word token using POS tag
            - parses the tagged wordswith nltk regex parser to construct phrases 
              in "adjective(0+)" plus "noun(1-3)" pattern
            - remove duplicate phrases and phrase that is substring of another phrase
            - remove empty sentences

        Parameter:
        ---------------
        lst_word_tokens: 2d list where first dimension holds sentence level tokens
                         then each sentence token holds it's word tokens and POS_tag

        remove_stopwords: (True | False) flag to remove stopwords
        
        Return:
        ---------------
        new_lst_word_tokens: 2d list with first dimension representing the sentence of text corpus
                             and second dimension the candidate key phrases extracted from the sentence
                             [["kp1", "kp2", ...], [], ....., []]
        '''
        # remove stop words and words with <= 2 chars or > 21 chars
        stopwords_temp = self.stop_words if remove_stopwords else []
        lst_word_tokens = [[word_token for word_token in sent_token
                            if (word_token[0] not in stopwords_temp and 
                            (len(word_token[0])>2 and len(word_token[0])<=21))] 
                            for sent_token in lst_word_tokens]

        # filter out empty sentence
        #lst_word_tokens = [sent_token for sent_token in lst_word_tokens if len(sent_token)]
        
        # map all NN* tags to NN and all JJ* tags to JJ
        lst_word_tokens = [[(word_token[0], "NN") if "NN" in word_token[1] else (word_token[0], "JJ") 
                            for word_token in sent_token] for sent_token in lst_word_tokens]

        # lemmatization
        lst_word_tokens = [[(self.lemmatizer.lemmatize(word_token[0], 
                            pos=self.get_wordnet_pos(word_token[1])), word_token[1])
                            for word_token in sent_token] 
                            for sent_token in lst_word_tokens]

        # chunk the tagged sentence token using "adj(0+)" plus "noun(1-3)" pattern
        # outputing a tree structure
        lst_word_tokens = [self.chucker.parse(sent_token) for sent_token in lst_word_tokens]

        # reconstruct the tree to phrases
        lst_word_tokens = [[' '.join(leaf[0] for leaf in subtree.leaves())
                            for subtree in sent_token.subtrees()
                            if subtree.label() == "NP"]
                            for sent_token in lst_word_tokens]

        # filter out phrases that is substring of another phrase
        unique_phrase = list(set([phrase_token for sent_token in lst_word_tokens for phrase_token in sent_token]))
        picked_phrases = []
        new_lst_word_tokens = []
        for sent_index in range(len(lst_word_tokens)):
            sent_token = lst_word_tokens[sent_index]
            new_sent_token = []
            for phrase_token in sent_token:
                if phrase_token not in picked_phrases:
                    pass_flag = 1
                    for unique_token in unique_phrase:
                        if phrase_token != unique_token and phrase_token in unique_token:
                            pass_flag = 0
                            break
                    if pass_flag:
                        new_sent_token.append(phrase_token)
            #if len(new_sent_token):
            new_lst_word_tokens.append(new_sent_token)

        return new_lst_word_tokens

    def embed_doc_ckps(self, doc_tag, ckps_list, infer_epochs=50, mode='infer_mode'):
        '''
        This method embeds doc and ckps to vectors

        Parameter:
        ---------------
        doc_tag: document tag

        ckps_list: 2d list -> [[ckp1, ckp2, ...], [ckp1, ...]]

        infer_epochs: number of epochs to run model to infer the new document

        mode: [infer_mode | dict_mode]
              - infer_mode: to infer each ckps by treating them as documents
              - dict_mode: infer each ckps by taking average of word matrix vectors
        
        Return:
        ---------------
        doc_embed: a tup (doc_tag, doc_embed)

        ckps_embed: a dict with key=ckp string and value= [embeded ckp vector, sent_index]
        '''
        # convert ckps_list to list of word tokens in 1d
        # at the same time embed each ckp
        # TODO: will skipping some ckp_token cause bug?
        new_ckps_list = []
        ckps_embed = {}
        if mode == 'infer_mode':
            for sent_index in range(len(ckps_list)):
                sent_token = ckps_list[sent_index]
                for ckp_token in sent_token:
                    new_ckps_list += ckp_token.split()
                    ckps_embed[ckp_token] = [self.model.infer_vector(ckp_token.split(), epochs=infer_epochs), sent_index]
        elif mode == 'dict_mode':
            for sent_index in range(len(ckps_list)):
                sent_token = ckps_list[sent_index]
                for ckp_token in sent_token:
                    ckp_token_embed = []
                    for word_token in ckp_token.split(): 
                        new_ckps_list.append(word_token)
                        if word_token in self.model.wv: 
                            ckp_token_embed.append(self.model.wv[word_token])
                    if len(ckp_token_embed):
                        ckps_embed[ckp_token] = [np.mean(np.array(ckp_token_embed), axis=0), sent_index]

        # embed document
        doc_embed = (doc_tag, self.model.infer_vector(new_ckps_list, epochs=infer_epochs))
        
        return doc_embed, ckps_embed

    
    def mmr(self, doc_embed, ckps_embed, beta=0.55, top_n=10):
        '''
        This method applied mmr to pick the top_n ckp with controlled similarity between ckps

        Parameter:
        ---------------
        doc_embed: a tup (doc_tag, doc_embed)

        ckps_embed: a dict with key=ckp string and value= [embeded ckp vector, sent_index]
        
        Return:
        ---------------
        selected_ckp_strings: 1d np array containing ckp string of the selected ckps

        selected_sent_index: list that contains the index of sentence for selected ckps (in ranked order)
        '''
        # get the vector of doc and ckps
        doc_vec = doc_embed[1].reshape(1, -1)
        ckp_vecs = np.array([ckp_embed[0] for ckp_embed in ckps_embed.values()])

        # this list stores sent_index with current index as index of ckp
        ckpIndex2sentIndex = [ckp_embed[1] for ckp_embed in ckps_embed.values()]

        # 2d list, inner dimension contains only 1 value representing cos sim between doc and ckp
        doc_ckp_sims = cosine_similarity(ckp_vecs, doc_vec)
        # 2d list that calculates ckp's cos sim with all other ckps
        ckp2ckp_sims = cosine_similarity(ckp_vecs)
        np.fill_diagonal(ckp2ckp_sims, np.NaN)

        # normalize cos sims to [0, 1]
        doc_ckp_sims_norm = doc_ckp_sims / np.max(doc_ckp_sims)
        ckp2ckp_sims_norm = ckp2ckp_sims / np.nanmax(ckp2ckp_sims, axis=0)
        # standardize and shift by 0.5
        doc_ckp_sims_norm = 0.5 + (doc_ckp_sims_norm - np.mean(doc_ckp_sims_norm)) / np.std(doc_ckp_sims_norm)
        ckp2ckp_sims_norm = 0.5 + (ckp2ckp_sims_norm - np.nanmean(ckp2ckp_sims_norm, axis=0)) / np.nanstd(ckp2ckp_sims_norm, axis=0)

        # keep indices of selected and unselected ckp in list
        selected_ckp = []
        unselected_ckp = [i for i in range(len(ckp_vecs))]
        selected_sent_index = [] # stores sent_index of selected ckp for reconstruction back to full sentence

        # find the most similar keyword (using original cosine similarities)
        best_ckp_index = np.argmax(doc_ckp_sims)
        selected_ckp.append(best_ckp_index)
        selected_sent_index.append(ckpIndex2sentIndex[best_ckp_index])
        unselected_ckp.remove(best_ckp_index)

        # do top_n - 1 cycle to select top N keywords
        while len(selected_ckp) != top_n:
            dist_to_doc = doc_ckp_sims_norm[unselected_ckp, :] # dist from ckp to doc of the unselected ckps
            # this is a 2d list that contains cos sim between selected ckp to unselected ckp
            dist_between_ckp = ckp2ckp_sims_norm[unselected_ckp][:, selected_ckp]

            # if dimension of dist_between_ckp is 1 we add additional axis to the end
            if dist_between_ckp.ndim == 1: dist_between_ckp = dist_between_ckp[:, np.newaxis]

            # find new ckp with mmr applied
            best_ckp_index = np.argmax((beta * dist_to_doc) - ((1-beta) * np.max(dist_between_ckp, axis=1).reshape(-1, 1)))
            true_ckp_index = unselected_ckp[best_ckp_index]

            # add new ckp to list
            selected_ckp.append(true_ckp_index)
            unselected_ckp.remove(true_ckp_index)
            selected_sent_index.append(ckpIndex2sentIndex[true_ckp_index])
        
        # return the ckp string of selected ckps
        ckp_strings = np.array(list(ckps_embed.keys()))
        selected_ckp_strings = ckp_strings[selected_ckp]
        return selected_ckp_strings, selected_sent_index