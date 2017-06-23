import langid

def langClassify(text):
    return langid.classify(text)[0]
