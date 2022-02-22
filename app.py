import re
import os
import requests
import unicodedata
from dotenv import load_dotenv
from indic_transliteration import detect
from indic_transliteration import sanscript
from flask import Flask, render_template, request
from indic_transliteration.sanscript import transliterate

load_dotenv()

app = Flask(__name__)

BEARER_TOKEN = os.environ.get("BEARER_TOKEN")

script_map = {
    'Bengali': ['bengali'],
    'Hindi': ['devanagari'],
    'Sanskrit': ['bevanagari'],
    'Gujarati': ['gujarati'],
    'Gurmukhi': ['gurmukhi'],
    'Kannada': ['kannada'],
    'Malayalam': ['malayalam'],
    'Oriya': ['oriya'],
    'Odia': ['oriya'],
    'Tamil': ['tamil'],
    'Telugu': ['telugu'],
    'English': ['ITRANS', 'HK', 'SLP1'],
}


def preprocess(txt):

    # removing web links
    txt = re.sub(r'http\S+', '', txt)
    # removing punctuations
    txt = re.sub(r'[^\w\s]', '', txt)
    # removing new line character
    txt = re.sub(r'\n', '', txt)

    return txt


def indicize(text, script='devanagari'):

    # transliterating from English script to Indic script
    return transliterate(text, sanscript.ITRANS, script)


def romanize(text, script):

    # transliterating from Indic script to English script
    return transliterate(text, script, sanscript.HK)


@app.route('/translate', methods=['POST'])
def twitter_anuvaad():

    form = request.form

    if form['twitter_url'] == '':
        return "No Twitter URL"

    if form['src_lang'] == form['tgt_lang']:
        return "Source language and Target language are same"

    twitter_url = form['twitter_url']

    url_id = twitter_url.split('/')[-1]

    # getting tweet from Twitter API
    response = requests.get(f"https://api.twitter.com/2/tweets/{url_id}",
                            headers={'Authorization': f"Bearer {BEARER_TOKEN}"})

    twitter = response.json()
    original_tweet = twitter['data']['text']

    # processing original tweet
    processed_tweet = preprocess(original_tweet)

    try:
        # detecting the script of the tweet using unicodedata
        tweet_script = set([unicodedata.name(c).split(' ')[0]
                           for c in processed_tweet])
    except Exception as e:
        return render_template('index.html', translation=f"Tweet parsing failed with Exception {e}")

    romanized = processed_tweet

    if form['src_lang'] == 'English':
        # if source language is English we need to translate to target Indic language.
        # We can also show the trnasliteration of the translated output
        trans_resp = requests.post(url='https://hf.space/gradioiframe/Harveenchadha/en_to_indic_translation/+/api/predict/',
                                   json={"data": [romanized, form['tgt_lang']]})
        translation = trans_resp.json()['data'][0]
        detected_script = detect.detect(translation)
        romanized = romanize(translation, detected_script.lower())

        return render_template('index.html', translation=translation, original=original_tweet, transliteration=romanized)
    else:
        # if the source language is not English we need to first transliterate the input if it is typed in English script.
        # We can then translate. We can also present transliteration if the target language is not English
        indicized = processed_tweet
        if 'LATIN' in tweet_script:
            print(
                f"English script found. Indicizing to {script_map[form['src_lang']][0]}")
            indicized = indicize(
                processed_tweet, script_map[form['src_lang']][0])

        trans_resp = requests.post(url='https://hf.space/gradioiframe/Harveenchadha/oiTrans/+/api/predict/',
                                   json={"data": [indicized, form['src_lang'], form['tgt_lang']]})
        translation = trans_resp.json()['data'][0]

        if form['tgt_lang'] != 'English':
            detected_script = detect.detect(translation)
            romanized = romanize(translation, detected_script.lower())
            return render_template('index.html', translation=translation, original=original_tweet, transliteration=romanized)

        return render_template('index.html', translation=translation, original=original_tweet)


@ app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':

    app.run(debug=True)
