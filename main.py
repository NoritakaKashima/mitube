import os
import flask
from flask import Flask, request, render_template, abort

app = Flask(__name__)
root = '.'


@app.route("/")
def hello():
    return get("")
    # return "<a href='Templates'>index!</a>"


def stat(path, base):
    p = os.path.join(path, base)
    o = {
        'path': p,
        'displayname': base,
        'isdir': os.path.isdir(p)
    }
    return o


def open(phy, _range):
    BUFFER_READ = 4096
    fspath = phy
    size = os.path.getsize(fspath)
    start = 0
    length = 0
    if _range:
        start = _range[0]
        if _range[1]:
            length = _range[1] - start + 1
        else:
            length = size - start
    else:
        length = size

    def generate():
        with open(fspath, 'rb') as f:
            f.seek(start)
            read = 0
            while not length or read < length:
                length_to_read = min(length - read, BUFFER_READ) if length else BUFFER_READ
                d = f.read(length_to_read)
                if d == 0:
                    break
                read += length_to_read
                yield d
    return generate


def get_file(phy):
    _range = None
    if 'Range' in request.headers:
        print(f'Range request: {request.headers["Range"]}')
        r0, r1 = request.headers['Range'].split("-")
        _range = (int(r0), int(r1) if r1 else None)
    stream = open(phy, _range)
    status = 206 if _range else 200
    return flask.Response(stream(), status, headers={}, direct_passthrough=True)


@app.route("/<path:path>")
def get(path):
    path = '/' + path
    phy = root + path
    if os.path.exists(phy):
        if os.path.isdir(phy):
            if not path.endswith('/'):
                return '', 301, {'Location': path + '/'}
            li = [stat(path, b) for b in os.listdir(phy)]
            li.insert(0, {'path': '..', 'displayname': '..', 'isdir': True})
            return render_template('list.html', path=path, phy=phy, li=li)
        else:
            return get_file(phy)
    else:
        return abort(404)


if __name__ == '__main__':
    app.run(debug=True)
