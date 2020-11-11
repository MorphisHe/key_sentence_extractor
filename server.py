from embed_rank.EmbedRank import EmbedRank
from flask import Flask, request
from io import BytesIO

MODEL_PATH = "d500_w4_mc8_n9_e50.model"
app = Flask(__name__)
er = EmbedRank(model_path=MODEL_PATH)



@app.route("/get_key_phrases", methods=["GET", "POST"])
def get_key_phrases():
    '''
    f = request.files["doc"]
    f.save("test.pdf")
    text = er.extract_information("test.pdf")
    return text
    '''
    pdf = open(request.files["doc"], "rb")
    text = er.extract_information(pdf)
    return text



if __name__ == "__main__":
    app.run(debug=True, port=5000)
