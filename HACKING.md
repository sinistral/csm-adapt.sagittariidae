# Sagittariidae development

## Setup

It is good Python development practice to set up a virtual environment.  This
will allow you to manage Sagittariidae's dependencies independently of other
Python projcts and so avoid versioning conflicts.  We recommend [Conda], but
[virtualenv] is also a popular option.

Having set up and activated a virtual environment for Sagittariidae, install
the required packages:
```
pip install -r requirements.txt
```

## Development server

[Flask] (the micro-webservice upon which Sagittariidae is built) provides a
script to launch a development server and reload code as changes are made.
Some [simple configuration][devserver] is required:

```
$ export FLASK_APP=app/app.py
$ export FLASK_DEBUG=1
$ flask run
```

[Conda]: http://conda.pydata.org/docs/index.html#
[virtualenv]: http://docs.python-guide.org/en/latest/dev/virtualenvs/
[Flask]: http://flask.pocoo.org/docs/0.11/
[devserver]: http://flask.pocoo.org/docs/0.11/server/#server
