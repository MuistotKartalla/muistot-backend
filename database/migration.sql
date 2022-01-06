/*
    PREPARE ------------------------------------------------------------------------------------------------------------
*/

USE muistot_skeleton;

SET autocommit = FALSE;
START TRANSACTION;

SET @migrator_id = -11;
SET @migrator_name = 'memories-migrator';
INSERT IGNORE INTO muistot.users (id, username)
    VALUE (@migrator_id, @migrator_name);

/*
    ADD COLUMNS --------------------------------------------------------------------------------------------------------
*/

ALTER TABLE muistot.images
    ADD COLUMN IF NOT EXISTS migration_id INTEGER;
ALTER TABLE muistot.projects
    ADD COLUMN IF NOT EXISTS migration_id INTEGER;
ALTER TABLE muistot.sites
    ADD COLUMN IF NOT EXISTS migration_id INTEGER;
ALTER TABLE muistot.memories
    ADD COLUMN IF NOT EXISTS migration_id INTEGER;
ALTER TABLE muistot.comments
    ADD COLUMN IF NOT EXISTS migration_id INTEGER;
ALTER TABLE muistot.users
    ADD COLUMN IF NOT EXISTS migration_id INTEGER;

/*
    COPY IMAGES --------------------------------------------------------------------------------------------------------
*/
INSERT INTO muistot.images (migration_id, file_name, uploader_id)
SELECT KID, Tiedostonimi, @migrator_id
FROM Kuva;


/*
    COPY PROJECTS ------------------------------------------------------------------------------------------------------
*/
INSERT INTO muistot.projects (migration_id,
                              name,
                              anonymous_posting,
                              image_id,
                              starts,
                              ends,
                              published,
                              default_language_id,
                              modifier_id)
SELECT p.PID,
       CONCAT_WS('-', REPLACE(LOWER(IFNULL(p3.Nimi, p2.Nimi)), ' ', '-'), p.PID),
       visitorPosting,
       il.id,
       CONVERT(Alkaa, DATETIME),
       CONVERT(Loppuu, DATETIME),
       1,
       1,
       @migrator_id
FROM projektit p
         LEFT JOIN projektikuvaus p2 ON p.PID = p2.PID
    AND p2.Lang = 'fi'
         LEFT JOIN projektikuvaus p3 ON p.PID = p3.PID
    AND p3.Lang = 'en'
         JOIN muistot.images il ON p.LogoKID = il.migration_id;


INSERT INTO muistot.project_information (project_id, lang_id, name, abstract, description, modifier_id)
SELECT pl.id, l.id, p.Nimi, p.Johdanto, p.Kuvaus, @migrator_id
FROM projektikuvaus p
         JOIN muistot.projects pl ON pl.migration_id = p.PID
         JOIN muistot.languages l ON p.Lang = l.lang;

INSERT INTO muistot.project_contact (project_id, can_contact, has_research_permit, contact_email, modifier_id)
SELECT pl.id, pc.Yhteydenottolupa, pc.Tutkimuslupa, NULL, @migrator_id
FROM Projektilupa pc
         JOIN muistot.projects pl ON pl.migration_id = pc.PID;

/*
    COPY USERS TODO: SEE REAL DATA
*/

INSERT INTO muistot.users (migration_id, email, username, password_hash)
SELECT u.UID, u.email, u.Tunnus, IF(u.Logintype = 'email', u.Salasana, NULL)
FROM User u;


INSERT INTO muistot.project_admins (project_id, user_id)
SELECT pl.id, ul.id
FROM Moderators m
         JOIN muistot.projects pl ON pl.migration_id = m.PID
         JOIN muistot.users ul ON ul.migration_id = m.UID;

/*
    COPY SITES ---------------------------------------------------------------------------------------------------------
*/

INSERT INTO muistot.sites (migration_id, project_id, name, published, location, modifier_id, modified_at)
SELECT k.KohdeID,
       pl.id,
       CONCAT_WS('-', 'site', k.KohdeID),
       1,
       POINT(lng, lat),
       @migrator_id,
       latauspvm
FROM Kohde2 k
         JOIN muistot.projects pl ON pl.migration_id = k.PID
WHERE k.verified;

INSERT INTO muistot.site_information (site_id, lang_id, name, modifier_id, modified_at)
SELECT sl.id,
       pl.default_language_id,
       k.title,
       IFNULL(ul.id, @migrator_id),
       IF(ISNULL(ul.id), CURRENT_TIMESTAMP, k.latauspvm)
FROM Kohde2 k
         LEFT JOIN muistot.users ul ON ul.migration_id = k.UID
         JOIN muistot.sites sl ON sl.migration_id = k.KohdeID
         JOIN muistot.projects pl ON pl.migration_id = k.PID
WHERE k.verified;

/*
    UPDATE IMAGES ------------------------------------------------------------------------------------------------------
*/
UPDATE muistot.images i
    JOIN Kuva k ON k.KID = i.migration_id
    JOIN muistot.users u ON k.UID = u.migration_id
SET i.uploader_id = u.id
WHERE i.uploader_id = @migrator_id;

/*
    COPY MEMORIES ------------------------------------------------------------------------------------------------------
*/
INSERT INTO muistot.memories (migration_id, site_id, user_id, image_id, title, story, published, modified_at)
SELECT m.MuistoID,
       sl.id,
       ul.id,
       il.id,
       m.title,
       m.story,
       1,
       m.latauspvm
FROM Muisto m
         LEFT JOIN muistot.users ul ON ul.migration_id = m.UID
         LEFT JOIN muistot.images il ON il.migration_id = m.KID
         JOIN muistot.sites sl ON sl.migration_id = m.KohdeID
WHERE m.verified;

/*
    COPY COMMENTS ------------------------------------------------------------------------------------------------------
*/
INSERT INTO muistot.comments (migration_id, memory_id, user_id, comment, published, modified_at)
SELECT c.KommenttiID, ml.id, ul.id, CONCAT_WS('\n', c.title, c.story), 1, c.latauspvm
FROM Kommentti c
         LEFT JOIN muistot.users ul ON ul.migration_id = c.UID
         JOIN muistot.memories ml ON ml.migration_id = c.MuistoID;

/*
    RESTORE ------------------------------------------------------------------------------------------------------------
*/
/*
ALTER TABLE muistot.images
    DROP COLUMN IF EXISTS migration_id;
ALTER TABLE muistot.projects
    DROP COLUMN IF EXISTS migration_id;
ALTER TABLE muistot.sites
    DROP COLUMN IF EXISTS migration_id;
ALTER TABLE muistot.memories
    DROP COLUMN IF EXISTS migration_id;
ALTER TABLE muistot.comments
    DROP COLUMN IF EXISTS migration_id;
ALTER TABLE muistot.users
    DROP COLUMN IF EXISTS migration_id;
*/

ROLLBACK;

/*
    FINISH -------------------------------------------------------------------------------------------------------------
*/
