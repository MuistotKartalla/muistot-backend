USE muistot_skeleton;

SET autocommit = FALSE;
START TRANSACTION;

SET @migrator_id = -11;
SET @migrator_name = 'memories-migrator';
INSERT INTO memories_on_a_map.users (id, username)
    VALUE (@migrator_id, @migrator_name);
/*
    Copy images
*/
DROP TEMPORARY TABLE IF EXISTS memories_on_a_map.images_lookup;
CREATE TEMPORARY TABLE memories_on_a_map.images_lookup
(
    old_id INTEGER,
    new_id INTEGER,
    INDEX (old_id, new_id)
);

INSERT INTO memories_on_a_map.images (file_name, uploader_id)
SELECT Tiedostonimi, @migrator_id
FROM Kuva;

INSERT INTO memories_on_a_map.images_lookup (old_id, new_id)
SELECT o.KID, n.id
FROM Kuva o
         JOIN memories_on_a_map.images n ON o.Tiedostonimi = n.file_name;

/*
    Copy projects
*/
DROP TEMPORARY TABLE IF EXISTS memories_on_a_map.projects_lookup;
CREATE TEMPORARY TABLE memories_on_a_map.projects_lookup
(
    old_id INTEGER,
    new_id INTEGER,
    INDEX (old_id, new_id)
);

INSERT INTO memories_on_a_map.projects (name, anonymous_posting, image_id, starts, ends, published)
SELECT CONCAT_WS('-', 'migrated', 'project', PID),
       visitorPosting,
       il.new_id,
       CONVERT(Alkaa, DATETIME),
       CONVERT(Loppuu, DATETIME),
       1
FROM projektit p
         JOIN memories_on_a_map.images_lookup il ON p.LogoKID = il.old_id;

INSERT INTO memories_on_a_map.projects_lookup (old_id, new_id)
SELECT o.PID, n.id
FROM projektit o
         CROSS JOIN memories_on_a_map.projects n
WHERE n.name = CONCAT_WS('-', 'migrated', 'project', o.PID);

/*
    Copy project info TODO: Copy legals
*/
INSERT INTO memories_on_a_map.project_information (project_id, lang_id, name, abstract, description, modifier_id)
SELECT pl.old_id, l.id, p.Nimi, p.Johdanto, p.Kuvaus, @migrator_id
FROM projektikuvaus p
         JOIN memories_on_a_map.projects_lookup pl ON pl.old_id = p.PID
         JOIN memories_on_a_map.languages l ON p.Lang = l.lang;

/*
    Copy users TODO: SEE REAL DATA
*/
DROP TEMPORARY TABLE IF EXISTS memories_on_a_map.users_lookup;
CREATE TEMPORARY TABLE memories_on_a_map.users_lookup
(
    old_id INTEGER,
    new_id INTEGER,
    INDEX (old_id, new_id)
);

INSERT INTO memories_on_a_map.users (email, username, password_hash)
SELECT u.email, u.Tunnus, IF(u.Logintype = 'email', u.Salasana, NULL)
FROM User u;

INSERT INTO memories_on_a_map.users_lookup (old_id, new_id)
SELECT ou.UID, nu.id
FROM memories_on_a_map.users nu
         JOIN User ou ON ou.Tunnus = nu.username;

/*
    Copy admins TODO
*/

/*
    Copy sites TODO: Also copy opening time
*/
INSERT INTO memories_on_a_map.sites (project_id, name, published, location, modifier_id)
SELECT pl.new_id,
       k.title,
       EXISTS(SELECT 1 FROM KohteenAvaus WHERE KohdeID = k.KohdeID),
       POINT(lng, lat),
       @migrator_id
FROM Kohde2 k
    JOIN memories_on_a_map.projects_lookup pl ON pl.old_id = k.PID;

/*
    Copy comments TODO
*/


ROLLBACK;
