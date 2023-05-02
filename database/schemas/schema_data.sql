/*
    Create Project Data Tables
*/
USE muistot;

CREATE TABLE IF NOT EXISTS projects
(
    id                  INTEGER      NOT NULL AUTO_INCREMENT,
    name                VARCHAR(255) NOT NULL,
    image_id            INTEGER      NULL     DEFAULT NULL COMMENT 'fk',
    starts              DATETIME     NULL     DEFAULT NULL,
    ends                DATETIME     NULL     DEFAULT NULL,
    admin_posting       BOOLEAN      NOT NULL DEFAULT FALSE,

    default_language_id INTEGER      NOT NULL,
    auto_publish        BOOLEAN      NOT NULL DEFAULT FALSE,

    published           BOOLEAN      NOT NULL DEFAULT FALSE,
    modifier_id         INTEGER      NULL COMMENT 'fk',
    modified_at         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY pk_projects (id),
    UNIQUE INDEX idx_project_name (name),
    INDEX idx_projects_status (published, ends, starts),

    CONSTRAINT FOREIGN KEY fk_projects_logo (image_id) REFERENCES images (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL,
    CONSTRAINT FOREIGN KEY fk_projects_modifier (modifier_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL,
    CONSTRAINT FOREIGN KEY fk_project_default_language (default_language_id) REFERENCES languages (id)
        ON UPDATE RESTRICT
        ON DELETE RESTRICT
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
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

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
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

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
    project_id INTEGER  NOT NULL COMMENT 'fk',
    user_id    INTEGER  NOT NULL COMMENT 'fk',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

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
    creator_id  INTEGER      NULL COMMENT 'fk',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    location    GEOMETRY     NOT NULL COMMENT 'Coordinates',

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
        ON DELETE SET NULL,
    CONSTRAINT FOREIGN KEY fg_sites_creator (creator_id) REFERENCES users (id)
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
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,

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
    user_id     INTEGER  NULL COMMENT 'fk',
    image_id    INTEGER  NULL COMMENT 'fk',
    title       VARCHAR(255),
    story       TEXT,

    deleted     BOOLEAN  NOT NULL DEFAULT FALSE,
    published   BOOLEAN  NOT NULL DEFAULT FALSE,
    modified_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY pk_comments (id),
    INDEX idx_comments_per_user (published, user_id),
    INDEX idx_comments_published (published, site_id) COMMENT 'Hopefully shares first part with the other index',

    CONSTRAINT FOREIGN KEY fk_memories_user (user_id) REFERENCES users (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL,
    CONSTRAINT FOREIGN KEY fk_memories_site (site_id) REFERENCES sites (id)
        ON UPDATE RESTRICT
        ON DELETE CASCADE,
    CONSTRAINT FOREIGN KEY fk_memories_image (image_id) REFERENCES images (id)
        ON UPDATE RESTRICT
        ON DELETE SET NULL
) COMMENT 'Only modify own memories.';
