CREATE DATABASE IF NOT EXISTS memories_on_a_map CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE memories_on_a_map;

/*
    Language preferences
*/

CREATE TABLE IF NOT EXISTS languages
(
    id   INTEGER    NOT NULL AUTO_INCREMENT,
    lang VARCHAR(5) NOT NULL,

    PRIMARY KEY pk_languages (id),
    UNIQUE INDEX idx_lang (lang)
) COMMENT 'Stores localization languages';

CREATE TABLE IF NOT EXISTS oauth_provides
(
    id   INTEGER     NOT NULL AUTO_INCREMENT,
    name VARCHAR(15) NOT NULL,

    PRIMARY KEY pk_oap (id),
    UNIQUE INDEX idx_oap_name (name)
) COMMENT 'Stores OAuth providers';

INSERT IGNORE INTO languages (lang)
VALUES ('fi'),
       ('en');

INSERT IGNORE INTO oauth_provides (name)
VALUES ('google'),
       ('facebook'),
       ('twitter');

/*
    Create Data Tables
*/

CREATE TABLE IF NOT EXISTS users
(
    id            INTEGER      NOT NULL AUTO_INCREMENT,
    email         VARCHAR(255) NULL DEFAULT NULL,
    username      VARCHAR(255) NOT NULL,
    password_hash BINARY(60) COMMENT 'BCrypt',

    # important
    verified      BOOLEAN           DEFAULT FALSE,
    created_at    DATETIME          DEFAULT CURRENT_TIMESTAMP,

    # basic data
    image_id      INTEGER      NULL COMMENT 'fk',
    lang_id       INTEGER      NULL COMMENT 'fk',

    PRIMARY KEY pk_users (id),
    UNIQUE INDEX idx_users_username (username),
    UNIQUE INDEX idx_users_email (email),

    CONSTRAINT FOREIGN KEY fk_users_language (lang_id) REFERENCES languages (id)
) COMMENT 'Stores user data';

CREATE TABLE IF NOT EXISTS oauth_users
(
    user_id    INTEGER NOT NULL COMMENT 'fk',
    service_id INTEGER NOT NULL COMMENT 'fk',

    PRIMARY KEY pk_oau (user_id, service_id),

    CONSTRAINT FOREIGN KEY fk_oau_user (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fk_oau_service (service_id) REFERENCES oauth_provides (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) COMMENT 'Links users to OAuth providers';

CREATE TABLE IF NOT EXISTS images
(
    id          INTEGER     NOT NULL AUTO_INCREMENT,
    created_at  DATETIME    NOT NULL                                                     DEFAULT CURRENT_TIMESTAMP,
    uploader_id INTEGER     NULL COMMENT 'fk',
    file_name   VARCHAR(36) NOT NULL COMMENT 'Never From Input' COLLATE ascii_general_ci DEFAULT UUID(),

    PRIMARY KEY pk_images (id),
    INDEX idx_images_uploader (uploader_id),
    CONSTRAINT FOREIGN KEY fk_images_uploader (uploader_id) REFERENCES users (id)
) COMMENT 'Unified storage for image files';

ALTER TABLE users
    ADD CONSTRAINT FOREIGN KEY IF NOT EXISTS fk_users_image (image_id) REFERENCES images (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL;

/*
    Create Project Data Tables
*/

CREATE TABLE IF NOT EXISTS projects
(
    id                INTEGER      NOT NULL AUTO_INCREMENT,
    name              VARCHAR(255) NOT NULL,
    image_id          INTEGER      NULL     DEFAULT NULL COMMENT 'fk',
    starts            DATETIME     NULL     DEFAULT NULL,
    ends              DATETIME     NULL     DEFAULT NULL,
    anonymous_posting BOOLEAN      NOT NULL DEFAULT FALSE,

    published         BOOLEAN      NOT NULL DEFAULT FALSE,
    modifier_id       INTEGER      NULL COMMENT 'fk',
    modified_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY pk_projects (id),
    UNIQUE INDEX idx_project_name (name),
    INDEX idx_projects_status (published, ends, starts),

    CONSTRAINT FOREIGN KEY fk_projects_logo (image_id) REFERENCES images (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL,
    CONSTRAINT FOREIGN KEY fk_projects_modifier (modifier_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL
) COMMENT 'Project base information';

CREATE TABLE IF NOT EXISTS project_information
(
    project_id  INTEGER      NOT NULL COMMENT 'fk',
    lang_id     INTEGER      NOT NULL COMMENT 'fk',
    name        VARCHAR(255) NULL,
    abstract    TEXT,
    description LONGTEXT,

    modifier_id INTEGER      NULL COMMENT 'fk',
    modified_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY pk_pi (project_id, lang_id),

    CONSTRAINT FOREIGN KEY fg_pi_id (project_id) REFERENCES projects (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fg_pi_lang (lang_id) REFERENCES languages (id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT FOREIGN KEY fg_pi_modifier (modifier_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL
) COMMENT 'Stores localized project information';

CREATE TABLE IF NOT EXISTS project_contact
(
    project_id          INTEGER      NOT NULL COMMENT 'fk',
    can_contact         BOOLEAN      NOT NULL DEFAULT FALSE,
    has_research_permit BOOLEAN      NOT NULL DEFAULT FALSE,
    contact_email       VARCHAR(255) NULL,

    modifier_id         INTEGER      NULL COMMENT 'fk',
    modified_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY pk_pl (project_id),

    CONSTRAINT FOREIGN KEY fk_pl_project (project_id) REFERENCES projects (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fk_pl_modifier (modifier_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL
) COMMENT 'Stores any additional project information';

CREATE TABLE IF NOT EXISTS project_admins
(
    project_id INTEGER NOT NULL COMMENT 'fk',
    user_id    INTEGER NOT NULL COMMENT 'fk',

    PRIMARY KEY pk_pa (project_id, user_id),

    CONSTRAINT FOREIGN KEY fk_pa_project (project_id) REFERENCES projects (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fk_pa_user (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) COMMENT 'Admins for projects';

CREATE TABLE IF NOT EXISTS sites
(
    id          INTEGER      NOT NULL AUTO_INCREMENT,
    project_id  INTEGER      NOT NULL COMMENT 'fk',
    name        VARCHAR(255) NOT NULL,
    image_id    INTEGER      NULL COMMENT 'fk',

    published   BOOLEAN      NOT NULL DEFAULT FALSE,
    modifier_id INTEGER      NULL COMMENT 'fk',
    modified_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    location    POINT        NOT NULL COMMENT 'Coordinates',

    PRIMARY KEY pk_sites (id),
    UNIQUE INDEX idx_sites_name (name),
    INDEX idx_sites_published (published, project_id),

    SPATIAL INDEX idx_sites_coordinate (location) COMMENT 'Index for coordinates',

    CONSTRAINT FOREIGN KEY fk_sites_project (project_id) REFERENCES projects (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fk_sites_image (image_id) REFERENCES images (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL,
    CONSTRAINT FOREIGN KEY fk_sites_modifier (modifier_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL
) COMMENT 'Stores project site locations';

CREATE TABLE IF NOT EXISTS site_information
(
    site_id     INTEGER      NOT NULL COMMENT 'fk',
    lang_id     INTEGER      NOT NULL COMMENT 'fk',
    name        VARCHAR(255) NULL,
    abstract    TEXT,
    description LONGTEXT,

    modifier_id INTEGER      NULL COMMENT 'fk',
    modified_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY pk_si (site_id, lang_id),

    CONSTRAINT FOREIGN KEY fg_si_id (site_id) REFERENCES sites (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fg_si_lang (lang_id) REFERENCES languages (id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT,
    CONSTRAINT FOREIGN KEY fg_si_modifier (modifier_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL
) COMMENT 'Stores localized project information';

CREATE TABLE IF NOT EXISTS memories
(
    id          INTEGER  NOT NULL AUTO_INCREMENT,
    site_id     INTEGER  NOT NULL COMMENT 'fk',
    user_id     INTEGER  NOT NULL COMMENT 'fk',
    image_id    INTEGER  NULL COMMENT 'fk',
    title       VARCHAR(255),
    story       TEXT,

    published   BOOLEAN  NOT NULL DEFAULT FALSE,
    modified_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY pk_comments (id),
    INDEX idx_comments_per_user (published, user_id),
    INDEX idx_comments_published (published, site_id) COMMENT 'Hopefully shares first part with the other index',

    CONSTRAINT FOREIGN KEY fk_memories_user (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fk_memories_site (site_id) REFERENCES sites (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fk_memories_image (image_id) REFERENCES images (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL
) COMMENT 'Only modify own memories.';

CREATE TABLE IF NOT EXISTS comments
(
    id          INTEGER  NOT NULL AUTO_INCREMENT,
    memory_id   INTEGER  NOT NULL COMMENT 'fk',
    user_id     INTEGER  NOT NULL COMMENT 'fk',
    comment     TEXT,

    published   BOOLEAN  NOT NULL DEFAULT FALSE,
    modified_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY pk_comments (id),
    INDEX idx_comments_per_user (published, user_id),
    INDEX idx_comments_published (published, memory_id) COMMENT 'Hopefully shares first part with the other index',

    CONSTRAINT FOREIGN KEY fk_comments_user (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fk_comments_memory (memory_id) REFERENCES memories (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) COMMENT 'Comments on memories. Only modify own comments.';

/**
More
*/

CREATE TABLE IF NOT EXISTS user_email_verifiers
(
    user_id    INTEGER      NOT NULL,
    verifier   VARCHAR(255) NOT NULL,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY pk_uev (user_id),
    INDEX idx_uev_date (created_at),

    CONSTRAINT FOREIGN KEY fk_uc_user_id (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) COMMENT 'Stores user confirm data';

CREATE TABLE IF NOT EXISTS user_personal_data
(
    user_id     INTEGER      NOT NULL,
    first_name  VARCHAR(255) NULL,
    last_name   VARCHAR(255) NULL,
    birth_date  DATETIME     NULL DEFAULT NULL,
    country     VARCHAR(5)   NULL,
    city        VARCHAR(255) NULL,

    modified_at DATETIME          DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY pk_upd (user_id),
    INDEX idx_upd_name (last_name, first_name),
    INDEX idx_upd_location (country, city),
    INDEX idx_upd_birthdate (birth_date),

    CONSTRAINT FOREIGN KEY fk_upd_user_id (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE
) COMMENT 'User personal data';

SET GLOBAL event_scheduler = TRUE;

DELIMITER $$

DROP PROCEDURE IF EXISTS clean_verifiers $$
CREATE PROCEDURE clean_verifiers()
BEGIN
    DELETE u
    FROM users u
             JOIN user_email_verifiers uev on u.id = uev.user_id
    WHERE uev.created_at < ADDDATE(CURRENT_TIMESTAMP, INTERVAL -24 HOUR)
      AND u.verified = 0;
    DELETE uev
    FROM users u
             JOIN user_email_verifiers uev ON u.id = uev.user_id
    WHERE u.verified;
END $$

DROP EVENT IF EXISTS delete_verifiers;
CREATE EVENT delete_verifiers
    ON SCHEDULE EVERY 24 HOUR
        STARTS '2021-01-01 02:00:00'
    DO CALL clean_verifiers() $$

DROP TRIGGER IF EXISTS trg_verifier_update $$
CREATE TRIGGER trg_verifier_update
    AFTER UPDATE
    ON users
    FOR EACH ROW
BEGIN
    IF NEW.verified THEN
        DELETE FROM user_email_verifiers WHERE user_id = OLD.id;
    END IF;
END $$

DROP PROCEDURE IF EXISTS analyze_all_tables $$
CREATE PROCEDURE analyze_all_tables()
BEGIN
    SET @table_list = NULL;
    SHOW TABLES WHERE (@table_list := concat_ws(',', @table_list, `Tables_in_memories_on_a_map`));
    SET @table_list := concat('ANALYZE TABLE ', @table_list);
    PREPARE tasks FROM @table_list;
    EXECUTE tasks;
    DEALLOCATE PREPARE tasks;
    SET @table_list = NULL;
END $$

DROP EVENT IF EXISTS check_tables;
CREATE EVENT check_tables
    ON SCHEDULE EVERY 1 WEEK
        STARTS '2021-01-01 02:10:00'
    DO CALL analyze_all_tables() $$

DELIMITER ;

CREATE TABLE IF NOT EXISTS audit_comments
(
    comment_id INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,

    PRIMARY KEY pk_ac (comment_id, user_id),

    CONSTRAINT FOREIGN KEY fg_ac_comment (comment_id) REFERENCES comments (id),
    CONSTRAINT FOREIGN KEY fg_ac_user (user_id) REFERENCES users (id)
);

DELIMITER $$

DROP PROCEDURE IF EXISTS comments_audit_log;
CREATE PROCEDURE comments_audit_log()
BEGIN
    SELECT COUNT(*)                    AS report_count,
           c.id                        AS comment_id,
           c.comment                   AS comment_story,
           cu.username                 AS comment_user,
           CONCAT_WS(',', ru.username) AS reporting_users
    FROM audit_comments ac
             JOIN comments c ON ac.comment_id = c.id
             JOIN users cu ON c.user_id = cu.id
             JOIN users ru ON ac.user_id = ru.id
    GROUP BY ac.comment_id
    ORDER BY report_count DESC;
END $$

DROP PROCEDURE IF EXISTS hide_reported_things;
CREATE PROCEDURE hide_reported_things()
BEGIN
    UPDATE comments c
        JOIN (
            SELECT ac.comment_id,
                   COUNT(*) AS report_count
            FROM audit_comments ac
            GROUP BY ac.comment_id
        ) ac ON ac.comment_id = c.id
    SET c.published = 0
    WHERE ac.report_count > 10;
END $$

CREATE EVENT report_watchdog
    ON SCHEDULE EVERY 12 HOUR
        STARTS '2021-01-01 00:00:00'
    DO CALL hide_reported_things() $$

DELIMITER ;

CALL analyze_all_tables();
