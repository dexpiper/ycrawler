# Ycombinator news crawler

Asyncro crawler for news site news.ycombinator.com

## Installation

1) Clone repo:

`$ git clone <repo address>`

and cd into directory

2) <i>optionally</i> - initialize and start virtual environment with:

`$ python3 -m venv env`
`$ source env/bin/activate`

3) Install dependencies:

`$ pip install -r requirements.txt`

## Usage

`$ python3 -m crawler [-d, --debug] [-l, --log]`

#### Arguments:

* -d, --debug:  set logging to debug (default logging level - info)
* -l, --log:    write logs into file. Usage: <i>-l mylogs.log</i>. If not set, logs would go to stdout

### Cycle

Script will take 30 news from root <i>news.ycombinator.com</i>, download link to each news piece and all the links mentioned in comments to that news piece. Downloaded items will be stored in folder "downloads" in project dir (by default). Every newspiece would have a separate folder with its unique <i>id</i>. Urls would be stored in <i>links.txt</i> file, downloaded pages related to newspiece - in <i>#hash#.html</i>.


