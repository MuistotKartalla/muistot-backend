import sqlite3

from fastapi import FastAPI, Depends
from pydantic import BaseModel

app = FastAPI()


class Name(BaseModel):
    value: str


def connection_provider():
    conn = sqlite3.connect('usernames.db')
    yield conn
    conn.close()


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
    import random, string
    generated: str
    while True:
        c = connection.cursor()
        c.execute('SELECT value FROM start ORDER BY RANDOM()')
        start, = c.fetchone()
        c.execute('SELECT value FROM end ORDER BY RANDOM()')
        end, = c.fetchone()
        serial = ''.join(map(lambda _: random.choice(string.digits), range(0, 4)))
        generated = start[0].upper() + start[1:] + end[0].upper() + end[1:] + '#' + serial
        c.execute('SELECT NOT EXISTS(SELECT 1 FROM generated WHERE value = ?)', [generated])
        free, = c.fetchone()
        if free:
            break
    return Name.construct(value=generated)
