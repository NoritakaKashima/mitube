import os
import sys
import math
import datetime
import traceback
import re
import flask
from flask import Flask, request, render_template, abort, make_response

app = Flask(__name__, template_folder=os.path.dirname(__file__)+'/Templates')
root = '/volume1'

mimetypes = {
    ".txt": "text/plain",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".mp4": "video/mp4",
    ".pdf": "application/pdf",
    }
    
    
def getmimetypes(ext):
    if ext in mimetypes:
        return mimetypes[ext]
    return 'plain/text'
    

@app.template_filter('convert_size')
def convert_size(size):
    units = ("bytes", "KB", "MB", "GB")
    if size < 1024:
        return f"{size}"
    else:
        i = math.floor(math.log(size, 1024)) if size > 0 else 0
        size = round(size / 1024 ** i, 2)
        return f"{size} {units[i]}"
    

def stat(path, entry):
    name = entry.name.decode('utf-8', 'surrogateescape')
    p = os.path.join(path, name)
    isdir = entry.is_dir()
    ext = 'dir'
    if not isdir:
        root, ext = os.path.splitext(p)
        if ext == '.mp4':
            p += '.html'
    o = {
        'path': p + ('/' if entry.is_dir() else ''),
        'name': name,
        'type': str(type(name)),
        'isdir': isdir,
        'size': entry.stat().st_size,
        'modified': datetime.datetime.fromtimestamp(entry.stat().st_mtime),
        'ext': ext,
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

    status = 206 if _range else 200
    return flask.Response(generate(), status, headers={'Content-Length': length, 'Accept-Ranges': 'bytes'}, direct_passthrough=True)


def get_file(phy, ext):
    _range = None
    if 'Range' in request.headers:
        m = re.search('(\d+)-(\d*)', request.headers['Range'])
        if m:
            g = m.groups()
            _range = (int(g[0]), int(g[1]) if g[1] else None)
        _range = (0, None)

    res = openfile(phy, _range)
    mt = getmimetypes(ext)
    res.headers.set('Content-Type', mt)
    return res


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
    rt, ext = os.path.splitext(path)
    phy = (root + path).encode()
    if os.path.exists(phy):
        if os.path.isdir(phy):
            if not path.endswith('/'):
                return '', 301, {'Location': path + '/'}
            with os.scandir(phy) as sd:
                li = [stat(path, b) for b in sd]
            key = request.args.get('sort', 'name')
            rev = False
            r = request.args.get('r')
            if r:
                rev = True
            li.sort(key=lambda x: x[key], reverse=rev)
            res = make_response(render_template('list.html', path=path, phy=phy, li=li, sort=key, rev=rev))
            res.headers.set('Accept-Ranges', 'bytes')
            return res
        else:
            return get_file(phy, ext)
    else:
        rt2, ext2 = os.path.splitext(rt)
        if ext == '.html' and ext2 == '.mp4':
            return make_response(render_template('movie.html', path=rt))
        return abort(404)


@app.errorhandler(Exception)
def handle(e):
    return f"<pre>{traceback.format_exc()}</pre>"
    
    
if __name__ == '__main__':
    app.run()
