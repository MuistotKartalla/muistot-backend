import random
import sqlite3
import string

from fastapi import FastAPI, Depends, Response
from pydantic import BaseModel

app = FastAPI()


class Name(BaseModel):
    value: str


def connection_provider():
    conn = sqlite3.connect('usernames.db')
    yield conn
    conn.close()


@app.on_event('startup')
def startup():
    app.state.disabled = False
    app.state.locked_name = None


@app.get(
    '/',
    name='name',
    response_model=Name,
    responses={
        200: {
            'description': 'Success',
            'value': {
                'example': {
                    'application/json': {
                        'value': 'NimetönSuunnistaja#3713'
                    }
                }
            }
        }
    }
)
def get_name(connection: sqlite3.Connection = Depends(connection_provider)):
    if app.state.disabled:
        return Response(status_code=500)
    elif app.state.locked_name:
        return Name.construct(value=app.state.locked_name)
    else:
        generated: str
        while True:
            c = connection.cursor()
            c.execute('SELECT value FROM start ORDER BY random()')
            start, = c.fetchone()
            c.execute('SELECT value FROM end ORDER BY random()')
            end, = c.fetchone()
            serial = ''.join(map(lambda _: random.choice(string.digits), range(0, 4)))
            generated = start[0].upper() + start[1:] + end[0].upper() + end[1:] + '#' + serial
            c.execute('SELECT NOT EXISTS(SELECT 1 FROM generated WHERE value = ?)', [generated])
            free, = c.fetchone()
            if free:
                break
        return Name.construct(value=generated)


@app.post('/lock')
def lock(username: str = None):
    app.state.locked_name = username


@app.post('/disable')
def disable():
    app.state.disabled = not app.state.disabled
