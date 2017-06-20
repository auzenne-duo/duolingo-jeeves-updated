# duolingo-jeeves
Technology-driven user support.

## Owner
- Lawrence Wolf-Sonkin, lawrence@duolingo.com
- Hideki Shima, hideki@duolingo.com

## Set up
- `git clone git@github.com:duolingo/duolingo-jeeves.git`
- `cd duolingo-jeeves`
- `virtualenv env`
- `export PYTHONPATH=$(pwd)`
- `source env/bin/activate`
- `pip install -r requirements.txt`
- `uwsgi uwsgi_dev.ini`
- open `http://localhost:5000/about` and `http://localhost:5000/api/1/hello`

## Links
- [Jeeves Spec](https://docs.google.com/document/d/1QaIR3qbbQh0cT0uwlHrLWeRywRnmXP4NKyK21PUCXnU/edit#)
