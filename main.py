import os
import sys
import datetime
import traceback
import flask
from flask import Flask, request, render_template, abort

app = Flask(__name__, template_folder=os.path.dirname(__file__)+'/Templates')
root = '.'


def stat(path, entry):
    name = entry.name.decode('utf-8', 'surrogateescape')
    p = os.path.join(path, name)
    o = {
        'path': p + ('/' if entry.is_dir() else ''),
        'name': name,
        'type': str(type(name)),
        'isdir': entry.is_dir(),
        'size': entry.stat().st_size,
        'modified': datetime.datetime.fromtimestamp(entry.stat().st_mtime),
    }
    return o


def openfile(phy, _range):
    BUFFER_READ = 4096
    fspath = phy
    size = os.path.getsize(fspath)
    start = 0
    length = 0
    if _range:
        start = int(_range[0])
        if _range[1]:
            length = int(_range[1]) - start + 1
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
    stream = openfile(phy, _range)
    status = 206 if _range else 200
    return flask.Response(stream(), status, headers={}, direct_passthrough=True)


@app.route("/env")
def env():
    return {"defaultencoding": sys.getdefaultencoding(),
        "filesystemencoding": sys.getfilesystemencoding(),
        "getfilesystemencodeerrors": sys.getfilesystemencodeerrors(),
        "__file__": __file__, "cwd": os.getcwd()}
    
    
@app.route("/")
@app.route("/<path:path>")
def get(path=""):
    path = '/' + path
    phy = root + path
    if os.path.exists(phy):
        if os.path.isdir(phy):
            if not path.endswith('/'):
                return '', 301, {'Location': path + '/'}
            with os.scandir(phy.encode()) as sd:
                li = [stat(path, b) for b in sd]
            key = 'name'
            sort = request.args.get('sort')
            if sort:
                key = sort
            rev = False
            r = request.args.get('r')
            if r:
                rev = True
            li.sort(key=lambda x: x[key], reverse=rev)
            return render_template('list.html', path=path, phy=phy, li=li, sort=sort, rev=rev)
        else:
            return get_file(phy)
    else:
        return abort(404)


@app.errorhandler(Exception)
def handle(e):
#    return {
#        "code": e.code,
#        "name": e.name,
#        "description": e.description,
#        "stacktrace": traceback.format_exc(),
#    }
    return f"<pre>{traceback.format_exc()}</pre>"
    
    
if __name__ == '__main__':
    app.run()
