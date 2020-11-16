from embed_rank.EmbedRank import EmbedRank
from flask import Flask, request, render_template
import base64

MODEL_PATH = "d500_w4_mc8_n9_e50.model"
app = Flask(__name__)
er = EmbedRank(model_path=MODEL_PATH)


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

def embed_rank_pipline(pdf_filename):
    text = er.extract_information(pdf_filename)

    sent_token, word_token = er.tokenize(text)
    assert len(sent_token) == len(word_token)

    word_token = er.pos_tag(word_token)
    assert len(sent_token) == len(word_token)

    word_token = er.preprocess(word_token)
    assert len(sent_token) == len(word_token)

    doc_embed, ckps_embed = er.embed_doc_ckps(pdf_filename, word_token)
    selected_ckp_strings, selected_sent_index = er.mmr(doc_embed, ckps_embed)

@app.route("/get_key_phrases", methods=["GET", "POST"])
def get_key_phrases():
    '''
    f = request.files["doc"]
    f.save("test.pdf")
    text = er.extract_information("test.pdf")
    return text
    '''
    #pdf = open(request.files["doc"], "rb")
    #text = er.extract_information(pdf)
    names = ["hi", "no"]
    return render_template("content.html", pdf_filename="test_doc4.pdf", names=names)



if __name__ == "__main__":
    app.run(debug=True, port=5000)
