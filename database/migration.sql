USE muistot_skeleton;

SET autocommit = FALSE;
START TRANSACTION;

SET @migrator_id = -11;
SET @migrator_name = 'memories-migrator';
INSERT INTO muistot.users (id, username)
    VALUE (@migrator_id, @migrator_name);
/*
    Copy images
*/
DROP TEMPORARY TABLE IF EXISTS muistot.images_lookup;
CREATE TEMPORARY TABLE muistot.images_lookup
(
    old_id INTEGER,
    new_id INTEGER,
    INDEX (old_id, new_id)
);

INSERT INTO muistot.images (file_name, uploader_id)
SELECT Tiedostonimi, @migrator_id
FROM Kuva;

INSERT INTO muistot.images_lookup (old_id, new_id)
SELECT o.KID, n.id
FROM Kuva o
         JOIN muistot.images n ON o.Tiedostonimi = n.file_name;

/*
    Copy projects
*/
DROP TEMPORARY TABLE IF EXISTS muistot.projects_lookup;
CREATE TEMPORARY TABLE muistot.projects_lookup
(
    old_id INTEGER,
    new_id INTEGER,
    INDEX (old_id, new_id)
);

INSERT INTO muistot.projects (name, anonymous_posting, image_id, starts, ends, published)
SELECT CONCAT_WS('-', 'migrated', 'project', PID),
       visitorPosting,
       il.new_id,
       CONVERT(Alkaa, DATETIME),
       CONVERT(Loppuu, DATETIME),
       1
FROM projektit p
         JOIN muistot.images_lookup il ON p.LogoKID = il.old_id;

INSERT INTO muistot.projects_lookup (old_id, new_id)
SELECT o.PID, n.id
FROM projektit o
         CROSS JOIN muistot.projects n
WHERE n.name = CONCAT_WS('-', 'migrated', 'project', o.PID);

/*
    Copy project info TODO: Copy legals
*/
INSERT INTO muistot.project_information (project_id, lang_id, name, abstract, description, modifier_id)
SELECT pl.old_id, l.id, p.Nimi, p.Johdanto, p.Kuvaus, @migrator_id
FROM projektikuvaus p
         JOIN muistot.projects_lookup pl ON pl.old_id = p.PID
         JOIN muistot.languages l ON p.Lang = l.lang;

/*
    Copy users TODO: SEE REAL DATA
*/
DROP TEMPORARY TABLE IF EXISTS muistot.users_lookup;
CREATE TEMPORARY TABLE muistot.users_lookup
(
    old_id INTEGER,
    new_id INTEGER,
    INDEX (old_id, new_id)
);

INSERT INTO muistot.users (email, username, password_hash)
SELECT u.email, u.Tunnus, IF(u.Logintype = 'email', u.Salasana, NULL)
FROM User u;

INSERT INTO muistot.users_lookup (old_id, new_id)
SELECT ou.UID, nu.id
FROM muistot.users nu
         JOIN User ou ON ou.Tunnus = nu.username;

/*
    Copy admins TODO
*/

/*
    Copy sites TODO: Also copy opening time
*/
INSERT INTO muistot.sites (project_id, name, published, location, modifier_id)
SELECT pl.new_id,
       k.title,
       EXISTS(SELECT 1 FROM KohteenAvaus WHERE KohdeID = k.KohdeID),
       POINT(lng, lat),
       @migrator_id
FROM Kohde2 k
    JOIN muistot.projects_lookup pl ON pl.old_id = k.PID;

/*
    Copy comments TODO
*/


ROLLBACK;
