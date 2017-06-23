# duolingo-jeeves
Technology-driven user support.

## Owner
- Lawrence Wolf-Sonkin, lawrence@duolingo.com
- Hideki Shima, hideki@duolingo.com

## Set up
- `brew install python3`
- `git clone git@github.com:duolingo/duolingo-jeeves.git`
- `cd duolingo-jeeves`
- `virtualenv -p python3 env`
- `export PYTHONPATH=$(pwd)`
- `source env/bin/activate`
- `pip3 install -r requirements.txt`
- `pip3 install -r dev-requirements.txt`
- `pre-commit install`
- `uwsgi uwsgi_dev.ini`
- Open `http://localhost:5000/`

## Links
- [Jeeves Spec](https://docs.google.com/document/d/1QaIR3qbbQh0cT0uwlHrLWeRywRnmXP4NKyK21PUCXnU/edit#)
