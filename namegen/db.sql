CREATE TABLE IF NOT EXISTS start
(
    id    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    value VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS end
(
    id    INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    value VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS generated
(
    value VARCHAR(255) PRIMARY KEY
);

INSERT INTO start (value)
VALUES ('nimetön'),
       ('nokkela'),
       ('tarkka'),
       ('nopea'),
       ('älykäs'),
       ('söpö'),
       ('leppoisa'),
       ('rauhallinen'),
       ('sisukas'),
       ('rohkea'),
       ('vikkelä'),
       ('utelias'),
       ('viekas'),
       ('veikeä'),
       ('mukava'),
       ('hassu'),
       ('terävä');

INSERT INTO end (value)
VALUES ('suunnistaja'),
       ('tutkija'),
       ('seikkailija'),
       ('orava'),
       ('kartturi'),
       ('kissa'),
       ('karhu'),
       ('peikko'),
       ('koira'),
       ('insinööri'),
       ('kettu'),
       ('lintu'),
       ('pöllö'),
       ('siili'),
       ('kala'),
       ('varis');
