from embed_rank.EmbedRank import EmbedRank
from flask import Flask, request, render_template

MODEL_PATH = "d500_w4_mc8_n9_e50.model"
app = Flask(__name__)
er = EmbedRank(model_path=MODEL_PATH)
FILE_NAME = "static/temp.pdf"
res_dict = {}
cur_sort_mode = "rank"

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/get_key_phrases", methods=["GET", "POST"])
def get_key_phrases():
    global res_dict
    res_dict = embed_rank_pipline(FILE_NAME)
    return render_template("content.html", pdf_filename=FILE_NAME.split("/")[-1], data=res_dict)

@app.route("/get_key_phrases/sort", methods=["GET", "POST"])
def sort():
    global cur_sort_mode
    global res_dict
    if cur_sort_mode == "rank":
        res_dict["zip_display"] = sorted(res_dict["zip_display"], key = lambda x: x[1][-1])
        cur_sort_mode = "original"
    else:
        res_dict["zip_display"] = sorted(res_dict["zip_display"], key = lambda x: x[1][0])
        cur_sort_mode = "rank"

    return render_template("content.html", pdf_filename=FILE_NAME.split("/")[-1], data=res_dict)

@app.route("/upload_file", methods=["POST"])
def upload_file():
    f = request.files['file']
    f.save(FILE_NAME)
    return "Success"

def reconstructor(sent_token, selected_ckp_strings, selected_sent_index):
    '''
    og_sents = [ (sent index, sent), ...]
    selected_ckp_strings = [string1, string2, ...]
    selected_full_sents = [(rank, og_sent, sent_index)]
    zip_display = [(ckp1, (rank1, og_sent_for_ckp1, sent_index)), ...]
    '''

    res_dict = {
        "og_sents" : [],
        "selected_ckp_strings" : selected_ckp_strings,
        "selected_full_sents" : [],
        "zip_display" : []
    }
    
    for sent_index in range(len(sent_token)):
        res_dict["og_sents"].append((sent_index, sent_token[sent_index]))

    rank = 1
    for sent_index in selected_sent_index:
        res_dict["selected_full_sents"].append((rank, sent_token[sent_index], sent_index))
        rank += 1

    res_dict["zip_display"] = list(zip(res_dict["selected_ckp_strings"], res_dict["selected_full_sents"]))

    return res_dict

def embed_rank_pipline(pdf_filename):
    text = er.extract_information(pdf_filename)

    sent_token, word_token = er.tokenize(text)
    assert len(sent_token) == len(word_token)

    word_token = er.pos_tag(word_token)
    assert len(sent_token) == len(word_token)

    word_token = er.preprocess(word_token)
    assert len(sent_token) == len(word_token)

    doc_embed, ckps_embed = er.embed_doc_ckps(pdf_filename, word_token, mode="infer_mode")
    selected_ckp_strings, selected_sent_index = er.mmr(doc_embed, ckps_embed)

    return reconstructor(sent_token, selected_ckp_strings, selected_sent_index)




if __name__ == "__main__":
    app.run(debug=True, port=5000)
