CREATE DATABASE memories_on_a_map CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE memories_on_a_map;

/*
    Language preferences
*/

CREATE TABLE languages
(
    id   INTEGER    NOT NULL AUTO_INCREMENT,
    lang VARCHAR(5) NOT NULL,

    PRIMARY KEY pk_languages (id),
    UNIQUE INDEX idx_lang (lang)
) COMMENT 'Stores localization languages';

CREATE TABLE oauth_provides
(
    id   INTEGER     NOT NULL AUTO_INCREMENT,
    name VARCHAR(15) NOT NULL,

    PRIMARY KEY pk_oap (id),
    UNIQUE INDEX idx_oap_name (name)
) COMMENT 'Stores OAuth providers';

INSERT INTO languages (lang)
VALUES ('fi'),
       ('en');

INSERT INTO oauth_provides (name)
VALUES ('google'),
       ('facebook'),
       ('twitter');

/*
    Create Data Tables
*/

CREATE TABLE users
(
    id            INTEGER      NOT NULL AUTO_INCREMENT,
    email         VARCHAR(255) NULL DEFAULT NULL,
    username      VARCHAR(255) NOT NULL,
    password_hash BINARY(60) COMMENT 'BCrypt',

    # Some data
    image_id      INTEGER      NULL COMMENT 'fk',
    lang_id       INTEGER      NULL COMMENT 'fk',

    PRIMARY KEY pk_users (id),
    UNIQUE INDEX idx_users_username (username),
    UNIQUE INDEX idx_users_email (email),

    CONSTRAINT FOREIGN KEY fk_users_language (lang_id) REFERENCES languages (id)
) COMMENT 'Stores user data';

CREATE TABLE oauth_users
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

CREATE TABLE images
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
    ADD CONSTRAINT FOREIGN KEY fk_users_image (image_id) REFERENCES images (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL;

/*
    Create Project Data Tables
*/

CREATE TABLE projects
(
    id                INTEGER      NOT NULL AUTO_INCREMENT,
    name              VARCHAR(255) NOT NULL,
    image_id          INTEGER      NULL     DEFAULT NULL COMMENT 'fk',
    starts            DATE         NOT NULL DEFAULT CURRENT_DATE,
    ends              DATE         NOT NULL DEFAULT DATE('9999-12-31'),
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

CREATE TABLE project_information
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

CREATE TABLE project_legals
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

CREATE TABLE project_admins
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

CREATE TABLE sites
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

CREATE TABLE site_information
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

CREATE TABLE comment
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

    CONSTRAINT FOREIGN KEY fk_comments_user (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fk_comments_site (site_id) REFERENCES sites (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fk_comments_image (image_id) REFERENCES images (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL
) COMMENT 'Comments on sites. Only modify own comments.';
